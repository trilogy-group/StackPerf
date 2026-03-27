"""Artifact registry commands."""

from pathlib import Path

import typer
from rich.console import Console

app = typer.Typer(help="Manage benchmark artifacts")
console = Console()


@app.command()
def register(
    name: str = typer.Option(..., "--name", "-n", help="Artifact name"),
    artifact_type: str = typer.Option(
        ..., "--type", "-t", help="Artifact type (export, report, bundle)"
    ),
    storage_path: Path = typer.Option(..., "--path", "-p", help="Path to artifact file"),
    content_type: str = typer.Option(
        "application/octet-stream", "--content-type", "-c", help="MIME content type"
    ),
    session_id: str | None = typer.Option(None, "--session", "-s", help="Associated session ID"),
    experiment_id: str | None = typer.Option(
        None, "--experiment", "-e", help="Associated experiment ID"
    ),
    size_bytes: int | None = typer.Option(
        None, "--size", help="Size in bytes (auto-detected if not provided)"
    ),
) -> None:
    """Register a new artifact in the registry.

    Either --session or --experiment must be provided to scope the artifact.
    """
    if session_id is None and experiment_id is None:
        console.print("[red]Error: Either --session or --experiment must be specified[/red]")
        raise typer.Exit(1)

    console.print("[bold blue]Registering artifact...[/bold blue]")
    console.print(f"  Name: {name}")
    console.print(f"  Type: {artifact_type}")
    console.print(f"  Path: {storage_path}")
    if session_id:
        console.print(f"  Session: {session_id}")
    if experiment_id:
        console.print(f"  Experiment: {experiment_id}")

    # Auto-detect size if not provided
    detected_size = size_bytes
    if detected_size is None and storage_path.exists():
        detected_size = storage_path.stat().st_size
        console.print(f"  Size: {detected_size} bytes")

    # Placeholder: actual implementation will register via ArtifactRegistryService
    console.print("[green]Artifact registered successfully[/green]")


@app.command("list")
def list_artifacts(
    session_id: str | None = typer.Option(None, "--session", "-s", help="Filter by session ID"),
    experiment_id: str | None = typer.Option(
        None, "--experiment", "-e", help="Filter by experiment ID"
    ),
) -> None:
    """List registered artifacts."""
    if session_id is None and experiment_id is None:
        console.print(
            "[yellow]Warning: No filter specified. Showing all artifacts may be slow.[/yellow]"
        )

    console.print("[bold blue]Registered Artifacts:[/bold blue]")

    if session_id:
        console.print(f"[dim]Session: {session_id}[/dim]")
    if experiment_id:
        console.print(f"[dim]Experiment: {experiment_id}[/dim]")

    # Placeholder: actual implementation will list from ArtifactRegistryService
    console.print("[dim]No artifacts found (placeholder)[/dim]")


@app.command()
def show(
    artifact_id: str,
) -> None:
    """Show artifact details."""
    console.print(f"[bold blue]Artifact: {artifact_id}[/bold blue]")
    # Placeholder: actual implementation will show from ArtifactRegistryService
    console.print("[dim]Artifact details (placeholder)[/dim]")


@app.command()
def remove(
    artifact_id: str,
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """Remove an artifact from the registry."""
    if not force:
        confirm = console.input(f"Remove artifact {artifact_id}? [y/N]: ")
        if confirm.lower() != "y":
            console.print("[yellow]Cancelled[/yellow]")
            raise typer.Exit(0)

    console.print(f"[bold blue]Removing artifact {artifact_id}...[/bold blue]")
    # Placeholder: actual implementation will remove via ArtifactRegistryService
    console.print("[green]Artifact removed[/green]")
