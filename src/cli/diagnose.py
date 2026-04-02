"""Diagnostic commands for stack health and environment verification.

This module provides commands for operators to verify stack health,
detect misconfigurations, and troubleshoot issues before launching
benchmark sessions.
"""

import asyncio
import sys
from dataclasses import dataclass
from enum import Enum
from typing import Any

import click
from rich.console import Console
from rich.table import Table

console = Console()


class HealthStatus(str, Enum):
    """Health check status."""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"
    NOT_CONFIGURED = "not_configured"


@dataclass
class HealthCheckResult:
    """Result of a single health check."""

    component: str
    status: HealthStatus
    message: str
    details: dict[str, Any] | None = None
    action: str | None = None  # Suggested action to fix issues


async def check_litellm_health(base_url: str = "http://localhost:4000") -> HealthCheckResult:
    """Check LiteLLM proxy health.

    Args:
        base_url: LiteLLM proxy base URL.

    Returns:
        Health check result.
    """
    import httpx

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{base_url}/health")

            if response.status_code == 200:
                return HealthCheckResult(
                    component="LiteLLM Proxy",
                    status=HealthStatus.HEALTHY,
                    message="Proxy is responding",
                    details={"base_url": base_url, "status_code": response.status_code},
                )
            else:
                return HealthCheckResult(
                    component="LiteLLM Proxy",
                    status=HealthStatus.UNHEALTHY,
                    message=f"Proxy returned status {response.status_code}",
                    details={"base_url": base_url, "status_code": response.status_code},
                    action="Check LiteLLM logs for errors",
                )
    except httpx.ConnectError:
        return HealthCheckResult(
            component="LiteLLM Proxy",
            status=HealthStatus.UNHEALTHY,
            message="Cannot connect to proxy",
            details={"base_url": base_url},
            action="Ensure LiteLLM is running: docker-compose up -d litellm",
        )
    except Exception as e:
        return HealthCheckResult(
            component="LiteLLM Proxy",
            status=HealthStatus.UNKNOWN,
            message=f"Unexpected error: {e}",
            details={"base_url": base_url, "error": str(e)},
            action="Check network configuration and proxy URL",
        )


async def check_postgres_health(
    database_url: str | None = None,
) -> HealthCheckResult:
    """Check PostgreSQL health.

    Args:
        database_url: Database connection URL (currently unused,
            connection params are read from environment with local defaults).

    Returns:
        Health check result.
    """
    import os

    try:
        import asyncpg

        # Read connection params from environment with local dev defaults
        host = os.environ.get("POSTGRES_HOST", "localhost")
        port = int(os.environ.get("POSTGRES_PORT", "5432"))
        user = os.environ.get("POSTGRES_USER", "postgres")
        password = os.environ.get("POSTGRES_PASSWORD", "postgres")
        database = os.environ.get("POSTGRES_DB", "stackperf")

        # Simple check - try to connect
        conn = await asyncpg.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            timeout=5.0,
        )
        await conn.close()

        return HealthCheckResult(
            component="PostgreSQL",
            status=HealthStatus.HEALTHY,
            message="Database connection successful",
            details={"host": host, "port": port, "database": database},
        )
    except Exception as e:
        return HealthCheckResult(
            component="PostgreSQL",
            status=HealthStatus.UNHEALTHY,
            message=f"Cannot connect to database: {e}",
            details={"error": str(e)},
            action="Ensure PostgreSQL is running: docker-compose up -d postgres",
        )


async def check_prometheus_health(base_url: str = "http://localhost:9090") -> HealthCheckResult:
    """Check Prometheus health.

    Args:
        base_url: Prometheus base URL.

    Returns:
        Health check result.
    """
    import httpx

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{base_url}/-/healthy")

            if response.status_code == 200:
                return HealthCheckResult(
                    component="Prometheus",
                    status=HealthStatus.HEALTHY,
                    message="Prometheus is healthy",
                    details={"base_url": base_url},
                )
            else:
                return HealthCheckResult(
                    component="Prometheus",
                    status=HealthStatus.UNHEALTHY,
                    message=f"Prometheus returned status {response.status_code}",
                    details={"base_url": base_url},
                    action="Check Prometheus configuration",
                )
    except httpx.ConnectError:
        return HealthCheckResult(
            component="Prometheus",
            status=HealthStatus.UNHEALTHY,
            message="Cannot connect to Prometheus",
            details={"base_url": base_url},
            action="Ensure Prometheus is running: docker-compose up -d prometheus",
        )
    except Exception as e:
        return HealthCheckResult(
            component="Prometheus",
            status=HealthStatus.UNKNOWN,
            message=f"Unexpected error: {e}",
            details={"base_url": base_url, "error": str(e)},
        )


async def check_grafana_health(base_url: str = "http://localhost:3000") -> HealthCheckResult:
    """Check Grafana health.

    Args:
        base_url: Grafana base URL.

    Returns:
        Health check result.
    """
    import httpx

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{base_url}/api/health")

            if response.status_code == 200:
                return HealthCheckResult(
                    component="Grafana",
                    status=HealthStatus.HEALTHY,
                    message="Grafana is healthy",
                    details={"base_url": base_url},
                )
            else:
                return HealthCheckResult(
                    component="Grafana",
                    status=HealthStatus.UNHEALTHY,
                    message=f"Grafana returned status {response.status_code}",
                    details={"base_url": base_url},
                    action="Check Grafana configuration",
                )
    except httpx.ConnectError:
        return HealthCheckResult(
            component="Grafana",
            status=HealthStatus.UNHEALTHY,
            message="Cannot connect to Grafana",
            details={"base_url": base_url},
            action="Ensure Grafana is running: docker-compose up -d grafana",
        )
    except Exception as e:
        return HealthCheckResult(
            component="Grafana",
            status=HealthStatus.UNKNOWN,
            message=f"Unexpected error: {e}",
            details={"base_url": base_url, "error": str(e)},
        )


def display_health_results(results: list[HealthCheckResult]) -> int:
    """Display health check results in a table.

    Args:
        results: List of health check results.

    Returns:
        Exit code (0 if all healthy, 1 otherwise).
    """
    table = Table(title="Stack Health Check")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Message")
    table.add_column("Action", style="yellow")

    all_healthy = True

    for result in results:
        status_style = {
            HealthStatus.HEALTHY: "green",
            HealthStatus.UNHEALTHY: "red",
            HealthStatus.UNKNOWN: "yellow",
            HealthStatus.NOT_CONFIGURED: "dim",
        }[result.status]

        if result.status != HealthStatus.HEALTHY:
            all_healthy = False

        table.add_row(
            result.component,
            f"[{status_style}]{result.status.value}[/{status_style}]",
            result.message,
            result.action or "",
        )

    console.print(table)

    if not all_healthy:
        console.print("\n[red]Some components are unhealthy. Review actions above.[/red]")
        return 1
    else:
        console.print("\n[green]All components are healthy.[/green]")
        return 0


@click.group()
def diagnose() -> None:
    """Diagnostic commands for stack health and troubleshooting."""
    pass


@diagnose.command()
@click.option("--litellm-url", default="http://localhost:4000", help="LiteLLM proxy URL")
@click.option("--prometheus-url", default="http://localhost:9090", help="Prometheus URL")
@click.option("--grafana-url", default="http://localhost:3000", help="Grafana URL")
def health(
    litellm_url: str,
    prometheus_url: str,
    grafana_url: str,
) -> None:
    """Check health of all stack components.

    This command verifies that all required services are running and healthy
    before launching a benchmark session.
    """
    console.print("[bold]Checking stack health...[/bold]\n")

    async def run_checks() -> list[HealthCheckResult]:
        results = await asyncio.gather(
            check_litellm_health(litellm_url),
            check_postgres_health(),
            check_prometheus_health(prometheus_url),
            check_grafana_health(grafana_url),
        )
        return list(results)

    results = asyncio.run(run_checks())
    exit_code = display_health_results(results)
    sys.exit(exit_code)


@diagnose.command()
@click.option("--session-id", help="Session ID to validate")
@click.option("--base-url", help="Expected proxy base URL")
@click.option("--model-alias", help="Expected model alias")
def session(
    session_id: str | None,
    base_url: str | None,
    model_alias: str | None,
) -> None:
    """Validate session configuration before launching a benchmark.

    Checks for common misconfigurations and provides actionable warnings.
    """
    issues: list[str] = []

    # Check for session ID
    if not session_id:
        issues.append("No session ID provided. Create a session first: stackperf session create")
    else:
        console.print(f"[green]✓[/green] Session ID: {session_id}")

    # Check base URL
    if base_url:
        if not base_url.startswith(("http://localhost", "http://127.0.0.1")):
            issues.append(
                f"Base URL '{base_url}' does not point to localhost. "
                "Ensure the proxy is accessible at this URL."
            )
        else:
            console.print(f"[green]✓[/green] Base URL: {base_url}")
    else:
        issues.append("No base URL configured")

    # Check model alias
    if model_alias:
        console.print(f"[green]✓[/green] Model alias: {model_alias}")
    else:
        issues.append("No model alias configured")

    # Display results
    if issues:
        console.print("\n[yellow]Configuration issues detected:[/yellow]")
        for issue in issues:
            console.print(f"  [yellow]•[/yellow] {issue}")
        console.print("\n[red]Resolve these issues before launching the session.[/red]")
        sys.exit(1)
    else:
        console.print("\n[green]Session configuration is valid. Ready to launch.[/green]")


@diagnose.command()
def env() -> None:
    """Diagnose environment configuration.

    Checks for required environment variables and common configuration issues.
    """
    import os

    console.print("[bold]Environment Diagnostics[/bold]\n")

    # Required environment variables
    env_vars = {
        "LITELLM_MASTER_KEY": "LiteLLM master key for authentication",
        "DATABASE_URL": "PostgreSQL connection string",
        "PROVIDER_API_KEYS": "Upstream provider API keys (optional)",
    }

    table = Table()
    table.add_column("Variable")
    table.add_column("Status")
    table.add_column("Description")

    for var, description in env_vars.items():
        value = os.environ.get(var)
        if value:
            # Check for potential secrets exposure
            if "key" in var.lower() or "secret" in var.lower():
                status = "[green]Set (value hidden)[/green]"
            else:
                status = "[green]Set[/green]"
        else:
            status = "[yellow]Not set[/yellow]"

        table.add_row(var, status, description)

    console.print(table)

    # Check for common issues
    console.print("\n[bold]Common Configuration Checks:[/bold]")

    # Check if .env file exists
    env_file = ".env"
    if os.path.exists(env_file):
        console.print("[green]✓[/green] .env file exists")
    else:
        console.print("[yellow]![/yellow] No .env file found. Copy .env.example to .env")

    # Check git state
    import subprocess

    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.stdout.strip():
            console.print("[yellow]![/yellow] Git working directory has uncommitted changes")
        else:
            console.print("[green]✓[/green] Git working directory is clean")
    except (subprocess.SubprocessError, FileNotFoundError):
        console.print("[yellow]![/yellow] Cannot check git state")


def main() -> None:
    """Entry point for diagnostic commands."""
    diagnose()
