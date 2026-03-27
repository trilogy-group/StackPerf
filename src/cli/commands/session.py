"""Session lifecycle commands."""

import typer
from rich.console import Console

from benchmark_core.models import SessionOutcomeState

app = typer.Typer(help="Manage benchmark sessions")
console = Console()

# CLI choice values for outcome states
OUTCOME_CHOICES = [state.value for state in SessionOutcomeState]


@app.command()
def create(
    experiment: str = typer.Option(..., "--experiment", "-e", help="Experiment ID"),
    variant: str = typer.Option(..., "--variant", "-v", help="Variant ID"),
    task_card: str = typer.Option(..., "--task-card", "-t", help="Task card ID"),
    harness_profile: str = typer.Option(
        ...,
        "--harness",
        "-H",
        help="Harness profile name",
    ),
    label: str | None = typer.Option(None, "--label", "-l", help="Operator label"),
    notes: str | None = typer.Option(None, "--notes", "-n", help="Initial session notes"),
) -> None:
    """Create a new benchmark session."""
    console.print("[bold blue]Creating session...[/bold blue]")
    console.print(f"  Experiment: {experiment}")
    console.print(f"  Variant: {variant}")
    console.print(f"  Task Card: {task_card}")
    console.print(f"  Harness: {harness_profile}")
    if label:
        console.print(f"  Label: {label}")
    if notes:
        console.print(f"  Notes: {notes[:50]}...")
    # Placeholder: actual implementation will create session and render env
    console.print("[green]Session created successfully[/green]")


@app.command("list")
def list_sessions(
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
def finalize(
    session_id: str,
    outcome: str = typer.Option(
        "valid",
        "--outcome",
        "-o",
        help="Outcome state",
        case_sensitive=False,
    ),
) -> None:
    """Finalize a benchmark session with outcome state.

    Outcome states:
    - valid: Session completed successfully (default)
    - invalid: Session completed but data should be excluded from comparisons
    - aborted: Session was terminated before completion
    """
    # Validate outcome state
    if outcome not in OUTCOME_CHOICES:
        console.print(f"[red]Invalid outcome state: {outcome}[/red]")
        console.print(f"Valid options: {', '.join(OUTCOME_CHOICES)}")
        raise typer.Exit(1)

    console.print(f"[bold blue]Finalizing session {session_id}...[/bold blue]")
    console.print(f"  Outcome: {outcome}")
    # Placeholder: actual implementation will finalize session
    console.print("[green]Session finalized[/green]")


@app.command()
def env(session_id: str) -> None:
    """Render harness environment snippet for a session."""
    console.print(f"[bold blue]Environment for session {session_id}:[/bold blue]")
    # Placeholder: actual implementation will render env snippet
    console.print("export OPENAI_API_BASE=http://localhost:4000")
    console.print("export OPENAI_API_KEY=sk-benchmark-...")


@app.command()
def add_notes(
    session_id: str,
    notes: str = typer.Option(..., "--notes", "-n", help="Notes to add to session"),
    append: bool = typer.Option(
        False,
        "--append",
        "-a",
        help="Append to existing notes instead of replacing",
    ),
) -> None:
    """Add or update notes for a benchmark session."""
    console.print(f"[bold blue]Updating notes for session {session_id}...[/bold blue]")
    if append:
        console.print("[dim]Appending to existing notes[/dim]")
    console.print(f"Notes: {notes[:80]}...")
    # Placeholder: actual implementation will update session notes
    console.print("[green]Session notes updated[/green]")
