"""Session lifecycle commands."""

import typer
from rich.console import Console

app = typer.Typer(help="Manage benchmark sessions")
console = Console()


@app.command()
def create(
    experiment: str = typer.Option(..., "--experiment", "-e", help="Experiment ID"),
    variant: str = typer.Option(..., "--variant", "-v", help="Variant ID"),
    task_card: str = typer.Option(..., "--task-card", "-t", help="Task card ID"),
    harness_profile: str = typer.Option(
        ...,
        "--harness",
        "-h",
        help="Harness profile name",
    ),
    label: str | None = typer.Option(None, "--label", "-l", help="Operator label"),
) -> None:
    """Create a new benchmark session."""
    console.print("[bold blue]Creating session...[/bold blue]")
    console.print(f"  Experiment: {experiment}")
    console.print(f"  Variant: {variant}")
    console.print(f"  Task Card: {task_card}")
    console.print(f"  Harness: {harness_profile}")
    # Placeholder: actual implementation will create session and render env
    console.print("[green]Session created successfully[/green]")


@app.command()
def list(
    experiment: str | None = typer.Option(None, "--experiment", "-e", help="Filter by experiment"),
) -> None:
    """List benchmark sessions."""
    console.print("[bold blue]Active Sessions:[/bold blue]")
    # Placeholder: actual implementation will list sessions


@app.command()
def show(session_id: str) -> None:
    """Show session details."""
    console.print(f"[bold]Session:[/bold] {session_id}")
    # Placeholder: actual implementation will show session details


@app.command()
def finalize(session_id: str) -> None:
    """Finalize a benchmark session."""
    console.print(f"[bold blue]Finalizing session {session_id}...[/bold blue]")
    # Placeholder: actual implementation will finalize session
    console.print("[green]Session finalized[/green]")


@app.command()
def env(session_id: str) -> None:
    """Render harness environment snippet for a session."""
    console.print(f"[bold blue]Environment for session {session_id}:[/bold blue]")
    # Placeholder: actual implementation will render env snippet
    console.print("export OPENAI_API_BASE=http://localhost:4000")
    console.print("export OPENAI_API_KEY=sk-benchmark-...")
