"""Session CLI commands."""

import asyncio
from pathlib import Path
from typing import Any
from uuid import UUID

import click
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from benchmark_core.config import Settings
from benchmark_core.models import (
    OutcomeState,
    SessionCreate,
    SessionFinalize,
    SessionNote,
    SessionStatus,
)
from benchmark_core.repositories import InMemorySessionRepository
from benchmark_core.services import (
    HarnessRenderer,
    SessionManager,
    capture_git_metadata,
)

console = Console()

# Get the session group from main
from cli.main import session


@session.command("create")
@click.option("--experiment", "-e", "experiment_name", help="Experiment name")
@click.option("--variant", "-v", "variant_name", help="Variant name")
@click.option("--task-card", "-t", "task_card_name", help="Task card name")
@click.option("--harness", "-h", "harness_profile_name", help="Harness profile name")
@click.option("--operator", "-o", "operator_label", help="Operator label")
@click.option("--repo-path", type=click.Path(exists=True), help="Repository path for git metadata")
@click.option("--output-dir", type=click.Path(), default=".stackperf", help="Output directory for rendered files")
@click.option("--format", "-f", "render_format", type=click.Choice(["shell", "dotenv", "json"]), default="shell", help="Output format")
@click.option("--no-git", is_flag=True, help="Skip git metadata capture")
def create_session(
    experiment_name: str | None,
    variant_name: str | None,
    task_card_name: str | None,
    harness_profile_name: str | None,
    operator_label: str | None,
    repo_path: str | None,
    output_dir: str,
    render_format: str,
    no_git: bool,
) -> None:
    """Create a new benchmark session.

    Creates a session record, issues a session-scoped credential,
    and renders the harness environment snippet.

    The session must be created BEFORE launching the harness.
    """
    # Create async context
    async def _create() -> None:
        settings = Settings()
        repository = InMemorySessionRepository()
        manager = SessionManager(settings=settings, session_repository=repository)

        # Build session creation input
        create_input = SessionCreate(
            experiment_name=experiment_name,
            variant_name=variant_name,
            task_card_name=task_card_name,
            harness_profile_name=harness_profile_name,
            operator_label=operator_label,
            capture_git=not no_git,
        )

        repo = Path(repo_path) if repo_path else None

        # Create session
        session_obj = await manager.create_session(create_input, repo_path=repo)

        # Get the raw API key (only shown once!)
        api_key = manager.credential_issuer.generate_api_key_value(session_obj.proxy_credential)

        # Display session info
        console.print(Panel.fit(
            f"[bold green]Session Created[/bold green]\n\n"
            f"[dim]Session ID:[/dim] {session_obj.session_id}\n"
            f"[dim]Status:[/dim] {session_obj.status.value}\n"
            f"[dim]Key Alias:[/dim] {session_obj.proxy_credential.key_alias}\n",
            title="StackPerf Session",
        ))

        # Show git metadata if captured
        if session_obj.git_metadata:
            console.print("\n[bold]Git Metadata:[/bold]")
            console.print(f"  Repo: {session_obj.git_metadata.repo_root}")
            console.print(f"  Branch: {session_obj.git_metadata.branch}")
            console.print(f"  Commit: {session_obj.git_metadata.commit_sha[:8]}")
            console.print(f"  Dirty: {'Yes' if session_obj.git_metadata.dirty else 'No'}")

        # Show credential (only shown once!)
        console.print("\n[bold red]⚠️  Session API Key (save this!):[/bold red]")
        console.print(f"  [yellow]{api_key}[/yellow]\n")
        console.print("[dim]This key is NOT stored - copy it now or use the rendered output.[/dim]\n")

        # Render environment snippet
        env_content = _render_minimal_env(session_obj, api_key, settings, render_format)

        # Save to output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Add to .gitignore if not already there
        gitignore_path = Path(".gitignore")
        if gitignore_path.exists():
            gitignore_content = gitignore_path.read_text()
            if output_dir not in gitignore_content:
                with open(gitignore_path, "a") as f:
                    f.write(f"\n# StackPerf session outputs\n{output_dir}/\n.env.local\n")

        env_file = output_path / f"session-env.{render_format}"
        env_file.write_text(env_content)

        console.print(f"[bold]Rendered environment:[/bold] {env_file}")
        console.print("\n[dim]Source this file before launching your harness:[/dim]")
        console.print(f"  [cyan]source {env_file}[/cyan]\n")

        # Show environment content
        console.print(Panel(
            Syntax(env_content, render_format if render_format != "dotenv" else "bash"),
            title="Environment Snippet",
        ))

    asyncio.run(_create())


def _render_minimal_env(
    session_obj: Any,
    api_key: str,
    settings: Settings,
    format: str,
) -> str:
    """Render minimal environment snippet for session."""
    lines: list[str] = []
    lines.append("# StackPerf Session Environment")
    lines.append("# WARNING: This file contains secrets - do not commit!")
    lines.append(f"# Session ID: {session_obj.session_id}")
    lines.append("")
    
    proxy_url = settings.litellm_base_url
    
    if format == "shell":
        lines.append(f"export STACKPERF_SESSION_ID=\"{session_obj.session_id}\"")
        lines.append(f"export STACKPERF_PROXY_BASE_URL=\"{proxy_url}\"")
        lines.append(f"export STACKPERF_SESSION_API_KEY=\"{api_key}\"")
        lines.append("")
        lines.append("# Anthropic-surface harness")
        lines.append("export ANTHROPIC_BASE_URL=\"${STACKPERF_PROXY_BASE_URL}/v1\"")
        lines.append("export ANTHROPIC_API_KEY=\"${STACKPERF_SESSION_API_KEY}\"")
        lines.append("")
        lines.append("# OpenAI-surface harness")
        lines.append("export OPENAI_BASE_URL=\"${STACKPERF_PROXY_BASE_URL}/v1\"")
        lines.append("export OPENAI_API_KEY=\"${STACKPERF_SESSION_API_KEY}\"")
    elif format == "dotenv":
        lines.append(f"STACKPERF_SESSION_ID=\"{session_obj.session_id}\"")
        lines.append(f"STACKPERF_PROXY_BASE_URL=\"{proxy_url}\"")
        lines.append(f"STACKPERF_SESSION_API_KEY=\"{api_key}\"")
        lines.append("")
        lines.append("# Anthropic-surface harness")
        lines.append(f"ANTHROPIC_BASE_URL=\"{proxy_url}/v1\"")
        lines.append(f"ANTHROPIC_API_KEY=\"{api_key}\"")
        lines.append("")
        lines.append("# OpenAI-surface harness")
        lines.append(f"OPENAI_BASE_URL=\"{proxy_url}/v1\"")
        lines.append(f"OPENAI_API_KEY=\"{api_key}\"")
    elif format == "json":
        import json
        data = {
            "STACKPERF_SESSION_ID": str(session_obj.session_id),
            "STACKPERF_PROXY_BASE_URL": proxy_url,
            "STACKPERF_SESSION_API_KEY": api_key,
            "ANTHROPIC_BASE_URL": f"{proxy_url}/v1",
            "ANTHROPIC_API_KEY": api_key,
            "OPENAI_BASE_URL": f"{proxy_url}/v1",
            "OPENAI_API_KEY": api_key,
        }
        return json.dumps(data, indent=2)
    
    return "\n".join(lines)


@session.command("finalize")
@click.argument("session_id")
@click.option("--outcome", "-o", "outcome_state", 
              type=click.Choice(["success", "partial", "failed", "error", "excluded"]),
              help="Session outcome")
@click.option("--note", "-n", "note_text", help="Final note to add")
def finalize_session(
    session_id: str,
    outcome_state: str | None,
    note_text: str | None,
) -> None:
    """Finalize a session with outcome."""
    async def _finalize() -> None:
        settings = Settings()
        repository = InMemorySessionRepository()
        manager = SessionManager(settings=settings, session_repository=repository)

        outcome = OutcomeState(outcome_state) if outcome_state else None

        try:
            session_obj = await manager.finalize_session(
                UUID(session_id),
                outcome=outcome,
            )

            if note_text:
                note_input = SessionNote(
                    session_id=UUID(session_id),
                    note=note_text,
                )
                session_obj = await manager.add_note(note_input)

            console.print(Panel.fit(
                f"[bold green]Session Finalized[/bold green]\n\n"
                f"[dim]Session ID:[/dim] {session_obj.session_id}\n"
                f"[dim]Status:[/dim] {session_obj.status.value}\n"
                f"[dim]Outcome:[/dim] {session_obj.outcome.value if session_obj.outcome else 'None'}\n"
                f"[dim]Duration:[/dim] {_format_duration(session_obj)}\n",
                title="StackPerf Session",
            ))

            if session_obj.notes:
                console.print("\n[bold]Session Notes:[/bold]")
                for i, note in enumerate(session_obj.notes, 1):
                    console.print(f"  {i}. {note}")

            if session_obj.is_comparison_eligible():
                console.print("\n[green]✓ Session eligible for comparisons[/green]")
            else:
                console.print(f"\n[yellow]⚠ Session excluded from comparisons (outcome: {session_obj.outcome})[/yellow]")

        except Exception as e:
            console.print(f"[red]Error finalizing session: {e}[/red]")
            raise click.Abort()

    asyncio.run(_finalize())


def _format_duration(session_obj: Any) -> str:
    """Format session duration."""
    if session_obj.ended_at and session_obj.started_at:
        delta = session_obj.ended_at - session_obj.started_at
        total_seconds = int(delta.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"
    return "N/A"


@session.command("note")
@click.argument("session_id")
@click.argument("note")
def add_note(session_id: str, note: str) -> None:
    """Add a note to a session."""
    async def _note() -> None:
        settings = Settings()
        repository = InMemorySessionRepository()
        manager = SessionManager(settings=settings, session_repository=repository)

        note_input = SessionNote(
            session_id=UUID(session_id),
            note=note,
        )

        try:
            session_obj = await manager.add_note(note_input)
            console.print(f"[green]Added note to session {session_id}[/green]")
            console.print(f"  Note: {note}")
        except Exception as e:
            console.print(f"[red]Error adding note: {e}[/red]")
            raise click.Abort()

    asyncio.run(_note())


@session.command("show")
@click.argument("session_id")
def show_session(session_id: str) -> None:
    """Show session details."""
    async def _show() -> None:
        settings = Settings()
        repository = InMemorySessionRepository()
        manager = SessionManager(settings=settings, session_repository=repository)

        try:
            session_obj = await manager.get_session(UUID(session_id))

            console.print(Panel.fit(
                f"[bold]Session Details[/bold]\n\n"
                f"[dim]Session ID:[/dim] {session_obj.session_id}\n"
                f"[dim]Status:[/dim] {session_obj.status.value}\n"
                f"[dim]Outcome:[/dim] {session_obj.outcome.value if session_obj.outcome else 'None'}\n"
                f"[dim]Operator:[/dim] {session_obj.operator_label or 'None'}\n"
                f"[dim]Started:[/dim] {session_obj.started_at}\n"
                f"[dim]Ended:[/dim] {session_obj.ended_at or 'Active'}\n",
                title="StackPerf Session",
            ))

            if session_obj.git_metadata:
                console.print("\n[bold]Git Metadata:[/bold]")
                table = Table(show_header=False)
                table.add_row("Repo", session_obj.git_metadata.repo_root)
                table.add_row("Branch", session_obj.git_metadata.branch)
                table.add_row("Commit", session_obj.git_metadata.commit_sha[:12])
                table.add_row("Dirty", "Yes" if session_obj.git_metadata.dirty else "No")
                table.add_row("Message", session_obj.git_metadata.commit_message or "")
                console.print(table)

            if session_obj.proxy_credential:
                console.print("\n[bold]Proxy Credential:[/bold]")
                console.print(f"  Alias: {session_obj.proxy_credential.key_alias}")
                console.print(f"  Virtual Key ID: {session_obj.proxy_credential.virtual_key_id or 'N/A'}")
                console.print(f"  Expires: {session_obj.proxy_credential.expires_at or 'N/A'}")

            if session_obj.notes:
                console.print("\n[bold]Notes:[/bold]")
                for i, note in enumerate(session_obj.notes, 1):
                    console.print(f"  {i}. {note}")

        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            raise click.Abort()

    asyncio.run(_show())


@session.command("list")
@click.option("--status", "-s", help="Filter by status")
def list_sessions(status: str | None) -> None:
    """List sessions."""
    async def _list() -> None:
        repository = InMemorySessionRepository()

        if status:
            sessions = await repository.list_by_status(status)
        else:
            sessions = await repository.list_all()

        if not sessions:
            console.print("[dim]No sessions found[/dim]")
            return

        table = Table(title="Sessions")
        table.add_column("Session ID", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Outcome", style="yellow")
        table.add_column("Started", style="dim")
        table.add_column("Operator")

        for s in sessions:
            table.add_row(
                str(s.session_id)[:8],
                s.status.value,
                s.outcome.value if s.outcome else "-",
                s.started_at.strftime("%Y-%m-%d %H:%M") if s.started_at else "-",
                s.operator_label or "-",
            )

        console.print(table)

    asyncio.run(_list())
