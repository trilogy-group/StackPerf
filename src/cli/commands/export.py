"""Export commands for reports and comparisons."""

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import typer
from rich.console import Console

from benchmark_core.db.models import Artifact
from benchmark_core.db.session import get_db_session
from benchmark_core.repositories.artifact_repository import SQLArtifactRepository
from reporting.export_service import ExportSerializer, ExportService

app = typer.Typer(help="Export benchmark results and reports")
console = Console()


@app.command()
def session(
    session_id: str,
    output: Path = typer.Option(
        Path("./output"),
        "--output",
        "-o",
        help="Output directory",
    ),
    output_format: str = typer.Option(
        "json", "--format", "-f", help="Export format (json, csv, parquet)"
    ),
    include_requests: bool = typer.Option(
        True, "--requests/--no-requests", help="Include request-level data"
    ),
    redact_secrets: bool = typer.Option(
        True, "--redact/--no-redact", help="Redact sensitive fields"
    ),
    register_artifact: bool = typer.Option(
        True, "--register/--no-register", help="Register export as artifact"
    ),
) -> None:
    """Export a single session with all canonical fields.

    Exports session metadata, timing, git information, and optional request data.
    Supports JSON, CSV, and Parquet formats. Automatically registers the export
    as an artifact in the benchmark database.
    """
    # Parse session ID
    try:
        session_uuid = UUID(session_id)
    except ValueError as err:
        raise typer.BadParameter(f"Invalid session ID: {session_id}") from err

    console.print(f"[bold blue]Exporting session {session_id}...[/bold blue]")

    with get_db_session() as db:
        try:
            # Create export service
            export_service = ExportService(db)

            # Export session data
            export_data = export_service.export_session(
                session_id=session_uuid,
                include_requests=include_requests,
                redact_secrets=redact_secrets,
            )

            # Generate output filename
            timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
            extension = {"json": "json", "csv": "csv", "parquet": "parquet"}[output_format]
            filename = f"session_{session_id[:8]}_{timestamp}.{extension}"
            output_file = output / filename

            # Serialize to chosen format
            if output_format == "json":
                ExportSerializer.to_json(export_data, output_file)
            elif output_format == "csv":
                ExportSerializer.to_csv(export_data, output_file, record_type="requests")
            elif output_format == "parquet":
                ExportSerializer.to_parquet(export_data, output_file, record_type="requests")

            console.print(f"[green]Exported to {output_file}[/green]")

            # Register as artifact if requested
            if register_artifact:
                artifact_repo = SQLArtifactRepository(db)

                artifact = Artifact(
                    artifact_type="export",
                    name=filename,
                    content_type=_get_content_type(output_format),
                    storage_path=str(output_file.absolute()),
                    size_bytes=output_file.stat().st_size if output_file.exists() else None,
                    session_id=session_uuid,
                    artifact_metadata={
                        "format": output_format,
                        "include_requests": include_requests,
                        "redact_secrets": redact_secrets,
                        "exported_at": datetime.now(UTC).isoformat(),
                    },
                )

                created = asyncio.run(artifact_repo.create(artifact))
                console.print(f"[green]Artifact registered: {created.id}[/green]")

        except ValueError as e:
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(1) from e
        except Exception as e:
            console.print(f"[red]Error exporting session: {e}[/red]")
            raise typer.Exit(1) from e


@app.command()
def experiment(
    experiment_id: str,
    output: Path = typer.Option(
        Path("./output"),
        "--output",
        "-o",
        help="Output directory",
    ),
    output_format: str = typer.Option(
        "json", "--format", "-f", help="Export format (json, csv, parquet)"
    ),
    include_sessions: bool = typer.Option(
        True, "--sessions/--no-sessions", help="Include session-level data"
    ),
    include_requests: bool = typer.Option(
        False, "--requests/--no-requests", help="Include request-level data"
    ),
    redact_secrets: bool = typer.Option(
        True, "--redact/--no-redact", help="Redact sensitive fields"
    ),
    register_artifact: bool = typer.Option(
        True, "--register/--no-register", help="Register export as artifact"
    ),
) -> None:
    """Export experiment with all sessions and optional request data.

    Exports experiment metadata, all sessions, and optionally all requests.
    Supports JSON, CSV, and Parquet formats. Automatically registers the export
    as an artifact in the benchmark database.
    """
    # Parse experiment ID
    try:
        experiment_uuid = UUID(experiment_id)
    except ValueError as err:
        raise typer.BadParameter(f"Invalid experiment ID: {experiment_id}") from err

    console.print(f"[bold blue]Exporting experiment {experiment_id}...[/bold blue]")

    with get_db_session() as db:
        try:
            # Create export service
            export_service = ExportService(db)

            # Export experiment data
            export_data = export_service.export_experiment(
                experiment_id=experiment_uuid,
                include_sessions=include_sessions,
                include_requests=include_requests,
                redact_secrets=redact_secrets,
            )

            # Generate output filename
            timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
            extension = {"json": "json", "csv": "csv", "parquet": "parquet"}[output_format]
            filename = f"experiment_{experiment_id[:8]}_{timestamp}.{extension}"
            output_file = output / filename

            # Serialize to chosen format
            if output_format == "json":
                ExportSerializer.to_json(export_data, output_file)
            elif output_format == "csv":
                ExportSerializer.to_csv(export_data, output_file, record_type="sessions")
            elif output_format == "parquet":
                ExportSerializer.to_parquet(export_data, output_file, record_type="sessions")

            console.print(f"[green]Exported to {output_file}[/green]")

            # Register as artifact if requested
            if register_artifact:
                artifact_repo = SQLArtifactRepository(db)

                artifact = Artifact(
                    artifact_type="export",
                    name=filename,
                    content_type=_get_content_type(output_format),
                    storage_path=str(output_file.absolute()),
                    size_bytes=output_file.stat().st_size if output_file.exists() else None,
                    experiment_id=experiment_uuid,
                    artifact_metadata={
                        "format": output_format,
                        "include_sessions": include_sessions,
                        "include_requests": include_requests,
                        "redact_secrets": redact_secrets,
                        "exported_at": datetime.now(UTC).isoformat(),
                    },
                )

                created = asyncio.run(artifact_repo.create(artifact))
                console.print(f"[green]Artifact registered: {created.id}[/green]")

        except ValueError as e:
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(1) from e
        except Exception as e:
            console.print(f"[red]Error exporting experiment: {e}[/red]")
            raise typer.Exit(1) from e


@app.command("comparison")
def comparison_export(
    experiment_id: str = typer.Option(..., "--experiment", "-e", help="Experiment ID"),
    output: Path = typer.Option(
        Path("./output"),
        "--output",
        "-o",
        help="Output directory",
    ),
    output_format: str = typer.Option("json", "--format", "-f", help="Export format"),
) -> None:
    """Export experiment comparison results.

    This is an alias for the 'experiment' command for backward compatibility.
    """
    # Delegate to experiment command
    experiment(
        experiment_id=experiment_id,
        output=output,
        output_format=output_format,
        include_sessions=True,
        include_requests=False,
        redact_secrets=True,
        register_artifact=True,
    )


def _get_content_type(output_format: str) -> str:
    """Get MIME content type for export format.

    Args:
        output_format: The export format (json, csv, parquet).

    Returns:
        MIME content type string.
    """
    content_types = {
        "json": "application/json",
        "csv": "text/csv",
        "parquet": "application/vnd.apache.parquet",
    }
    return content_types.get(output_format, "application/octet-stream")
