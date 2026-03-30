"""CLI commands for request normalization and reconciliation reporting."""

from typing import Annotated
from uuid import UUID

import httpx
import typer
from rich.console import Console
from rich.table import Table
from sqlalchemy import func, select

from benchmark_core.db.models import Request as RequestORM
from benchmark_core.db.session import get_db_session
from benchmark_core.repositories.request_repository import SQLRequestRepository
from collectors.normalize_requests import (
    ReconciliationReport,
    RequestNormalizer,
    RequestNormalizerJob,
)

app = typer.Typer(
    name="normalize",
    help="Normalize LiteLLM request data into canonical request tables",
    rich_markup_mode="rich",
)

console = Console()


@app.command(name="run")
def run_normalization(
    session_id: Annotated[
        str,
        typer.Argument(help="Benchmark session ID to normalize requests for"),
    ],
    litellm_url: Annotated[
        str,
        typer.Option(
            "--litellm-url",
            "-u",
            help="LiteLLM proxy URL",
            envvar="LITELLM_URL",
        ),
    ] = "http://localhost:4000",
    litellm_key: Annotated[
        str,
        typer.Option(
            "--litellm-key",
            "-k",
            help="LiteLLM API key",
            envvar="LITELLM_API_KEY",
        ),
    ] = "",
    start_time: Annotated[
        str | None,
        typer.Option(
            "--start-time",
            "-s",
            help="Start time filter (ISO format)",
        ),
    ] = None,
    end_time: Annotated[
        str | None,
        typer.Option(
            "--end-time",
            "-e",
            help="End time filter (ISO format)",
        ),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            "-d",
            help="Show what would be normalized without writing to database",
        ),
    ] = False,
) -> None:
    """Run the request normalization job for a session.

    Fetches raw requests from LiteLLM, normalizes them into canonical
    request records, and writes them to the database with idempotent
    semantics. Generates a reconciliation report for any unmapped rows.
    """
    import asyncio

    try:
        session_uuid = UUID(session_id)
    except ValueError as err:
        console.print("[red]Error: Invalid session ID[/red]")
        raise typer.Exit(1) from err

    if not litellm_key:
        console.print(
            "[yellow]Warning: No LiteLLM API key provided. Set LITELLM_API_KEY env var.[/yellow]"
        )

    async def _run() -> tuple[int, ReconciliationReport]:
        # Fetch raw requests from LiteLLM
        raw_requests = await _fetch_litellm_requests(
            litellm_url=litellm_url,
            litellm_key=litellm_key,
            start_time=start_time,
            end_time=end_time,
        )

        if not raw_requests:
            return 0, ReconciliationReport()

        if dry_run:
            # In dry-run mode, just normalize and show report without writing
            normalizer = RequestNormalizer(session_id=session_uuid)
            report = ReconciliationReport()
            for i, raw in enumerate(raw_requests):
                normalized, diag = normalizer.normalize(raw, row_index=i)
                if normalized:
                    report.add_mapped()
                else:
                    report.add_unmapped(
                        raw_data=raw,
                        reason=diag.reason if diag else "Unknown",
                        missing_fields=diag.missing_fields if diag else [],
                        error_message=diag.error_message if diag else "",
                        row_index=i,
                    )
            return 0, report

        # Normal mode: write to database
        with get_db_session() as db_session:
            repository = SQLRequestRepository(db_session)
            normalizer_job = RequestNormalizerJob(
                repository=repository,
                session_id=session_uuid,
            )
            written, report = await normalizer_job.run(raw_requests)
            db_session.commit()
            return len(written), report

    try:
        count, report = asyncio.run(_run())

        # Display results
        console.print("\n[bold green]Normalization Complete[/bold green]")
        console.print(f"Total rows processed: {report.total_rows}")
        console.print(f"Successfully mapped: {report.mapped_count}")
        console.print(f"Unmapped rows: {report.unmapped_count}")

        if dry_run:
            console.print("\n[yellow]Dry run mode - no records written[/yellow]")
        else:
            console.print(f"Records written: {count}")

        if report.missing_field_counts:
            console.print("\n[bold]Missing Fields:[/bold]")
            table = Table("Field", "Count")
            for field, count in sorted(
                report.missing_field_counts.items(),
                key=lambda x: x[1],
                reverse=True,
            ):
                table.add_row(field, str(count))
            console.print(table)

        if report.error_counts:
            console.print("\n[bold]Error Categories:[/bold]")
            table = Table("Category", "Count")
            for category, count in sorted(
                report.error_counts.items(),
                key=lambda x: x[1],
                reverse=True,
            ):
                table.add_row(category, str(count))
            console.print(table)

        if report.unmapped_diagnostics and report.unmapped_count > 0:
            console.print("\n[yellow]First few unmapped rows:[/yellow]")
            for i, diag in enumerate(report.unmapped_diagnostics[:5]):
                console.print(f"  Row {diag.row_index or i}: {diag.reason}")

    except Exception as err:
        console.print(f"[red]Error during normalization: {err}[/red]")
        raise typer.Exit(1) from err


@app.command(name="report")
def show_reconciliation_report(
    session_id: Annotated[
        str,
        typer.Argument(help="Benchmark session ID to generate report for"),
    ],
    report_format: Annotated[
        str,
        typer.Option(
            "--format",
            "-f",
            help="Output format: markdown, json",
        ),
    ] = "markdown",
    output: Annotated[
        str | None,
        typer.Option(
            "--output",
            "-o",
            help="Output file path (default: stdout)",
        ),
    ] = None,
) -> None:
    """Generate a reconciliation report from a previous normalization run.

    This command retrieves the current state of normalized requests
    and generates a summary report.
    """
    import json

    try:
        UUID(session_id)
    except ValueError as err:
        console.print("[red]Error: Invalid session ID[/red]")
        raise typer.Exit(1) from err

    # Get request count for the session
    with get_db_session() as db_session:
        # Query the actual count of normalized requests for this session
        stmt = select(func.count()).where(RequestORM.session_id == UUID(session_id))
        count = db_session.execute(stmt).scalar() or 0

        # Query for any requests with errors
        error_stmt = select(func.count()).where(
            RequestORM.session_id == UUID(session_id),
            RequestORM.error == True,  # noqa: E712
        )
        error_count = db_session.execute(error_stmt).scalar() or 0

        report = ReconciliationReport()
        report.total_rows = count
        report.mapped_count = count  # All stored requests are successfully mapped

        # If there are errors, add to error counts
        if error_count > 0:
            report.error_counts["error_flag_set"] = error_count

        # Generate output
        if report_format == "json":
            output_text = json.dumps(report.to_dict(), indent=2)
        else:
            output_text = report.to_markdown()

        if output:
            with open(output, "w") as f:
                f.write(output_text)
            console.print(f"[green]Report written to {output}[/green]")
        else:
            console.print(output_text)

        # Summary
        console.print(f"\n[bold]Session {session_id}[/bold]")
        console.print(f"Total normalized requests: {count}")
        if error_count > 0:
            console.print(f"Requests with errors: {error_count}")


async def _fetch_litellm_requests(
    litellm_url: str,
    litellm_key: str,
    start_time: str | None,
    end_time: str | None,
) -> list[dict[str, object]]:
    """Fetch raw requests from LiteLLM spend logs endpoint."""
    headers = {
        "Authorization": f"Bearer {litellm_key}",
        "Content-Type": "application/json",
    }

    params: dict[str, str] = {}
    if start_time:
        params["start_time"] = start_time
    if end_time:
        params["end_time"] = end_time

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(
            f"{litellm_url.rstrip('/')}/spend/logs",
            headers=headers,
            params=params,
        )
        response.raise_for_status()
        data = response.json()

        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        if isinstance(data, dict) and isinstance(data.get("logs"), list):
            return [item for item in data["logs"] if isinstance(item, dict)]
        return []
