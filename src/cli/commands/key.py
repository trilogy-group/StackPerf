"""Sessionless proxy key commands for the CLI.

Provides `benchmark key create`, `benchmark key list`,
`benchmark key info`, and `benchmark key revoke` commands.
"""

import asyncio
from typing import Any
from uuid import UUID

import typer
from rich.console import Console
from rich.table import Table
from sqlalchemy.orm import Session as SQLAlchemySession

from benchmark_core.db.session import get_db_session
from benchmark_core.models import ProxyKeyStatus
from benchmark_core.repositories.proxy_key_repository import SQLProxyKeyRepository
from benchmark_core.services.proxy_key_service import (
    LiteLLMAPIError,
    ProxyKeyService,
    ProxyKeyServiceError,
)

app = typer.Typer(help="Manage sessionless proxy keys")
console = Console()


def _get_service(db: SQLAlchemySession) -> ProxyKeyService:
    """Build a ProxyKeyService from environment/config and a DB session."""
    import os

    litellm_url = os.environ.get("LITELLM_BASE_URL", "http://localhost:4000")
    master_key = os.environ.get("LITELLM_MASTER_KEY")

    repository = SQLProxyKeyRepository(db)
    return ProxyKeyService(
        repository=repository,
        litellm_base_url=litellm_url,
        master_key=master_key,
        enforce_https=False,
    )


@app.command()
def create(
    alias: str | None = typer.Option(None, "--alias", "-a", help="Key alias"),
    owner: str | None = typer.Option(None, "--owner", "-o", help="Key owner"),
    team: str | None = typer.Option(None, "--team", "-t", help="Team label"),
    customer: str | None = typer.Option(None, "--customer", "-c", help="Customer label"),
    purpose: str | None = typer.Option(None, "--purpose", "-p", help="Key purpose/description"),
    models: list[str] | None = typer.Option(
        None, "--model", "-m", help="Allowed model alias (repeatable)"
    ),
    budget_amount: float | None = typer.Option(
        None, "--budget-amount", "-b", help="Budget limit (currency units)"
    ),
    budget_duration: str | None = typer.Option(
        None, "--budget-duration", "-d", help="Budget interval (e.g. '1d', '30d')"
    ),
    metadata_pairs: list[str] | None = typer.Option(
        None, "--meta", help="Metadata tag as 'key=value' (repeatable)"
    ),
    ttl_hours: int = typer.Option(168, "--ttl-hours", help="Key TTL in hours (default 7 days)"),
    show_env: bool = typer.Option(
        False, "--show-env", "-e", help="Print environment snippet after creation"
    ),
    format_type: str = typer.Option(
        "shell",
        "--format",
        "-f",
        help="Environment format: shell or dotenv",
    ),
) -> None:
    """Create a new sessionless proxy key.

    The key secret is displayed ONCE and never persisted.
    Only non-secret metadata (alias, owner, team, etc.) is stored locally.
    """
    console.print("[bold blue]Creating sessionless proxy key...[/bold blue]")

    # Parse metadata pairs
    metadata: dict[str, str] | None = None
    if metadata_pairs:
        metadata = {}
        for pair in metadata_pairs:
            if "=" not in pair:
                console.print(f"[red]Invalid metadata format: {pair} (expected key=value)[/red]")
                raise typer.Exit(1)
            key, value = pair.split("=", 1)
            metadata[key] = value

    with get_db_session() as db:
        service = _get_service(db)

        try:
            proxy_key, secret = _run(
                service.create_key(
                    key_alias=alias,
                    owner=owner,
                    team=team,
                    customer=customer,
                    purpose=purpose,
                    allowed_models=models or None,
                    budget_amount=budget_amount,
                    budget_duration=budget_duration,
                    metadata=metadata,
                    ttl_hours=ttl_hours,
                )
            )
        except ProxyKeyServiceError as e:
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(1) from e
        except LiteLLMAPIError as e:
            console.print(f"[red]LiteLLM API error: {e}[/red]")
            raise typer.Exit(1) from e

    # Display success
    console.print("[green]Proxy key created successfully[/green]")
    console.print(f"  Alias: [bold]{proxy_key.key_alias}[/bold]")
    console.print(f"  ID: {proxy_key.proxy_key_id}")
    if proxy_key.owner:
        console.print(f"  Owner: {proxy_key.owner}")
    if proxy_key.team:
        console.print(f"  Team: {proxy_key.team}")
    if proxy_key.customer:
        console.print(f"  Customer: {proxy_key.customer}")
    if proxy_key.allowed_models:
        console.print(f"  Allowed Models: {', '.join(proxy_key.allowed_models)}")
    console.print(f"  Status: {proxy_key.status.value}")
    console.print(f"  Expires: {proxy_key.expires_at}")

    # Display the secret ONCE
    console.print(
        "\n[bold yellow]API Key Secret (copy now - will not be shown again):[/bold yellow]"
    )
    console.print(f"  {secret.get_secret_value()}")

    # Optionally render environment snippet
    if show_env:
        env_vars = service.render_env_snippet(secret)
        console.print("\n[bold blue]Environment Variables:[/bold blue]")
        if format_type == "shell":
            console.print(service.render_env_shell(env_vars))
        elif format_type == "dotenv":
            console.print(service.render_env_dotenv(env_vars))
        else:
            console.print(f"[yellow]Unknown format '{format_type}', using shell[/yellow]")
            console.print(service.render_env_shell(env_vars))

    # Warning
    console.print("\n[dim]Note: The secret is not stored locally. Keep it safe.[/dim]")


@app.command("list")
def list_keys(
    owner: str | None = typer.Option(None, "--owner", "-o", help="Filter by owner"),
    team: str | None = typer.Option(None, "--team", "-t", help="Filter by team"),
    customer: str | None = typer.Option(None, "--customer", "-c", help="Filter by customer"),
    status: str | None = typer.Option(None, "--status", "-s", help="Filter by status"),
    limit: int = typer.Option(50, "--limit", "-n", help="Maximum results"),
) -> None:
    """List sessionless proxy keys."""
    status_enum = None
    if status:
        try:
            status_enum = ProxyKeyStatus(status)
        except ValueError as exc:
            console.print(f"[red]Invalid status: {status}[/red]")
            raise typer.Exit(1) from exc

    with get_db_session() as db:
        service = _get_service(db)
        try:
            keys = _run(
                service.list_keys(
                    owner=owner,
                    team=team,
                    customer=customer,
                    status=status_enum,
                    limit=limit,
                )
            )
        except ProxyKeyServiceError as e:
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(1) from e

    if not keys:
        console.print("[yellow]No proxy keys found[/yellow]")
        return

    table = Table(title="Proxy Keys")
    table.add_column("Alias", style="cyan")
    table.add_column("Owner")
    table.add_column("Team")
    table.add_column("Customer")
    table.add_column("Status", style="bold")
    table.add_column("Allowed Models")
    table.add_column("Created")
    table.add_column("Expires")
    table.add_column("Revoked")

    for key in keys:
        status_style = {
            ProxyKeyStatus.ACTIVE: "green",
            ProxyKeyStatus.REVOKED: "red",
            ProxyKeyStatus.EXPIRED: "yellow",
        }.get(key.status, "white")

        revoked_str = key.revoked_at.isoformat() if key.revoked_at else "-"

        table.add_row(
            key.key_alias,
            key.owner or "-",
            key.team or "-",
            key.customer or "-",
            f"[{status_style}]{key.status.value}[/{status_style}]",
            ", ".join(key.allowed_models) if key.allowed_models else "-",
            key.created_at.strftime("%Y-%m-%d %H:%M") if key.created_at else "-",
            key.expires_at.strftime("%Y-%m-%d %H:%M") if key.expires_at else "-",
            revoked_str[:16] if revoked_str != "-" else "-",
        )

    console.print(table)
    console.print(f"\n[dim]Showing {len(keys)} key(s)[/dim]")


@app.command()
def info(
    key_id: str = typer.Argument(..., help="Proxy key ID (UUID) or alias"),
) -> None:
    """Show detailed info for a proxy key."""
    with get_db_session() as db:
        service = _get_service(db)

        # Try as UUID first, then as alias
        try:
            pk_uuid = UUID(key_id)
            proxy_key = _run(service.get_key_info(pk_uuid))
        except ValueError:
            proxy_key = _run(service.get_key_by_alias(key_id))

    if proxy_key is None:
        console.print(f"[red]Proxy key not found: {key_id}[/red]")
        raise typer.Exit(1)

    status_style = {
        ProxyKeyStatus.ACTIVE: "green",
        ProxyKeyStatus.REVOKED: "red",
        ProxyKeyStatus.EXPIRED: "yellow",
    }.get(proxy_key.status, "white")

    console.print(f"[bold]Proxy Key:[/bold] {proxy_key.key_alias}")
    console.print(f"  ID: {proxy_key.proxy_key_id}")
    console.print(f"  LiteLLM Key ID: {proxy_key.litellm_key_id or '-'}")
    console.print(f"  Status: [{status_style}]{proxy_key.status.value}[/{status_style}]")
    if proxy_key.owner:
        console.print(f"  Owner: {proxy_key.owner}")
    if proxy_key.team:
        console.print(f"  Team: {proxy_key.team}")
    if proxy_key.customer:
        console.print(f"  Customer: {proxy_key.customer}")
    if proxy_key.purpose:
        console.print(f"  Purpose: {proxy_key.purpose}")
    if proxy_key.allowed_models:
        console.print(f"  Allowed Models: {', '.join(proxy_key.allowed_models)}")
    if proxy_key.budget_amount is not None:
        console.print(f"  Budget: {proxy_key.budget_amount} {proxy_key.budget_currency}")
    if proxy_key.budget_duration:
        console.print(f"  Budget Duration: {proxy_key.budget_duration}")
    console.print(f"  Created: {proxy_key.created_at}")
    if proxy_key.expires_at:
        console.print(f"  Expires: {proxy_key.expires_at}")
    if proxy_key.revoked_at:
        console.print(f"  Revoked: {proxy_key.revoked_at}")
    if proxy_key.key_metadata:
        console.print(f"  Metadata: {proxy_key.key_metadata}")


@app.command()
def revoke(
    key_id: str = typer.Argument(..., help="Proxy key ID (UUID) or alias"),
) -> None:
    """Revoke a sessionless proxy key.

    Marks the local metadata as inactive and attempts LiteLLM deletion.
    The key secret cannot be recovered after revocation.
    """
    with get_db_session() as db:
        service = _get_service(db)

        # Try as UUID first, then as alias
        try:
            pk_uuid = UUID(key_id)
            try:
                proxy_key = _run(service.revoke_key(pk_uuid))
            except ProxyKeyServiceError as e:
                console.print(f"[red]Error: {e}[/red]")
                raise typer.Exit(1) from e
        except ValueError:
            try:
                proxy_key = _run(service.get_key_by_alias(key_id))
            except ProxyKeyServiceError as e:
                console.print(f"[red]Error: {e}[/red]")
                raise typer.Exit(1) from e
            if proxy_key is not None:
                try:
                    proxy_key = _run(service.revoke_key(proxy_key.proxy_key_id))
                except ProxyKeyServiceError as e:
                    console.print(f"[red]Error: {e}[/red]")
                    raise typer.Exit(1) from e

    if proxy_key is None:
        console.print(f"[red]Proxy key not found: {key_id}[/red]")
        raise typer.Exit(1)

    console.print("[green]Proxy key revoked successfully[/green]")
    console.print(f"  Alias: {proxy_key.key_alias}")
    console.print(f"  Status: {proxy_key.status.value}")
    if proxy_key.revoked_at:
        console.print(f"  Revoked at: {proxy_key.revoked_at}")


def _run(coro: Any) -> Any:
    """Run an async coroutine synchronously."""
    return asyncio.run(coro)
