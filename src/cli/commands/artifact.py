"""Artifact registry commands."""

import asyncio
from pathlib import Path
from uuid import UUID

import typer
from rich.console import Console
from rich.table import Table

from benchmark_core.db.models import Artifact as DBArtifact
from benchmark_core.db.session import get_db_session
from benchmark_core.repositories.artifact_repository import SQLArtifactRepository

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

    # Parse UUIDs if provided
    session_uuid: UUID | None = None
    experiment_uuid: UUID | None = None

    if session_id:
        try:
            session_uuid = UUID(session_id)
        except ValueError as err:
            raise typer.BadParameter(f"Invalid session ID: {session_id}") from err

    if experiment_id:
        try:
            experiment_uuid = UUID(experiment_id)
        except ValueError as err:
            raise typer.BadParameter(f"Invalid experiment ID: {experiment_id}") from err

    # Auto-detect size if not provided
    detected_size = size_bytes
    if detected_size is None and storage_path.exists():
        detected_size = storage_path.stat().st_size

    console.print("[bold blue]Registering artifact...[/bold blue]")
    console.print(f"  Name: {name}")
    console.print(f"  Type: {artifact_type}")
    console.print(f"  Path: {storage_path}")
    if detected_size:
        console.print(f"  Size: {detected_size} bytes")
    if session_uuid:
        console.print(f"  Session: {session_uuid}")
    if experiment_uuid:
        console.print(f"  Experiment: {experiment_uuid}")

    with get_db_session() as db:
        try:
            repository = SQLArtifactRepository(db)

            # Create artifact entity
            artifact = DBArtifact(
                artifact_type=artifact_type,
                name=name,
                content_type=content_type,
                storage_path=str(storage_path),
                size_bytes=detected_size,
                session_id=session_uuid,
                experiment_id=experiment_uuid,
            )

            created = asyncio.run(repository.create(artifact))
            console.print(f"[green]Artifact registered successfully: {created.id}[/green]")

        except Exception as e:
            console.print(f"[red]Error registering artifact: {e}[/red]")
            raise typer.Exit(1) from e


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

    # Parse UUIDs if provided
    session_uuid: UUID | None = None
    experiment_uuid: UUID | None = None

    if session_id:
        try:
            session_uuid = UUID(session_id)
        except ValueError as err:
            raise typer.BadParameter(f"Invalid session ID: {session_id}") from err

    if experiment_id:
        try:
            experiment_uuid = UUID(experiment_id)
        except ValueError as err:
            raise typer.BadParameter(f"Invalid experiment ID: {experiment_id}") from err

    with get_db_session() as db:
        try:
            repository = SQLArtifactRepository(db)

            if session_uuid:
                artifacts = asyncio.run(repository.list_by_session(session_uuid))
            elif experiment_uuid:
                artifacts = asyncio.run(repository.list_by_experiment(experiment_uuid))
            else:
                artifacts = asyncio.run(repository.list_all(limit=100))

            if not artifacts:
                console.print("[yellow]No artifacts found[/yellow]")
                return

            # Create table
            table = Table(title=f"Artifacts ({len(artifacts)})")
            table.add_column("ID", style="dim", no_wrap=True)
            table.add_column("Name", style="cyan")
            table.add_column("Type", style="blue")
            table.add_column("Size", style="green", justify="right")
            table.add_column("Scope", style="yellow")

            for art in artifacts:
                # Determine scope
                if art.session_id:
                    scope = f"session:{str(art.session_id)[:8]}"
                elif art.experiment_id:
                    scope = f"experiment:{str(art.experiment_id)[:8]}"
                else:
                    scope = "none"

                size_str = f"{art.size_bytes:,}" if art.size_bytes else "-"
                table.add_row(
                    str(art.id)[:8],
                    art.name,
                    art.artifact_type,
                    size_str,
                    scope,
                )

            console.print(table)

        except Exception as e:
            console.print(f"[red]Error listing artifacts: {e}[/red]")
            raise typer.Exit(1) from e


@app.command()
def show(
    artifact_id: str,
) -> None:
    """Show artifact details."""
    try:
        art_uuid = UUID(artifact_id)
    except ValueError as err:
        raise typer.BadParameter(f"Invalid artifact ID: {artifact_id}") from err

    with get_db_session() as db:
        try:
            repository = SQLArtifactRepository(db)
            art = asyncio.run(repository.get_by_id(art_uuid))

            if art is None:
                console.print(f"[red]Artifact not found: {artifact_id}[/red]")
                raise typer.Exit(1)

            console.print(f"[bold blue]Artifact: {art.id}[/bold blue]")
            console.print(f"  Name: {art.name}")
            console.print(f"  Type: {art.artifact_type}")
            console.print(f"  Content Type: {art.content_type}")
            console.print(f"  Storage Path: {art.storage_path}")
            if art.size_bytes:
                console.print(f"  Size: {art.size_bytes:,} bytes")
            if art.session_id:
                console.print(f"  Session ID: {art.session_id}")
            if art.experiment_id:
                console.print(f"  Experiment ID: {art.experiment_id}")
            console.print(f"  Created: {art.created_at}")

        except Exception as e:
            console.print(f"[red]Error showing artifact: {e}[/red]")
            raise typer.Exit(1) from e


@app.command()
def remove(
    artifact_id: str,
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """Remove an artifact from the registry."""
    try:
        art_uuid = UUID(artifact_id)
    except ValueError as err:
        raise typer.BadParameter(f"Invalid artifact ID: {artifact_id}") from err

    with get_db_session() as db:
        try:
            repository = SQLArtifactRepository(db)

            # Check if artifact exists first
            art = asyncio.run(repository.get_by_id(art_uuid))
            if art is None:
                console.print(f"[red]Artifact not found: {artifact_id}[/red]")
                raise typer.Exit(1)

            # Confirm deletion
            if not force:
                confirm = console.input(
                    f"Remove artifact '{art.name}' ({artifact_id[:8]})? [y/N]: "
                )
                if confirm.lower() != "y":
                    console.print("[yellow]Cancelled[/yellow]")
                    raise typer.Exit(0)

            console.print(f"[bold blue]Removing artifact {artifact_id}...[/bold blue]")
            deleted = asyncio.run(repository.delete(art_uuid))

            if deleted:
                console.print("[green]Artifact removed successfully[/green]")
            else:
                console.print(f"[red]Failed to remove artifact: {artifact_id}[/red]")
                raise typer.Exit(1)

        except Exception as e:
            console.print(f"[red]Error removing artifact: {e}[/red]")
            raise typer.Exit(1) from e
