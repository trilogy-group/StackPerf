"""CLI commands for data collection from LiteLLM and Prometheus."""

from typing import Annotated
from uuid import UUID

import httpx
import typer
from rich.console import Console
from rich.table import Table
from sqlalchemy.orm import Session as SQLAlchemySession

from benchmark_core.db.session import get_db_session
from benchmark_core.repositories.request_repository import SQLRequestRepository
from benchmark_core.repositories.rollup_repository import SQLRollupRepository
from collectors.litellm_collector import CollectionDiagnostics, LiteLLMCollector
from collectors.normalize_requests import RequestNormalizerJob
from collectors.prometheus_collector import PrometheusCollector
from collectors.rollup_job import RollupJob

app = typer.Typer(
    name="collect",
    help="Collect and normalize benchmark data from LiteLLM and Prometheus",
    rich_markup_mode="rich",
)

console = Console()


@app.command(name="litellm")
def collect_litellm(
    session_id: Annotated[
        str,
        typer.Argument(help="Benchmark session ID to collect requests for"),
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
            help="Show what would be collected without writing to database",
        ),
    ] = False,
) -> None:
    """Collect and normalize request data from LiteLLM for a session.

    Fetches raw requests from LiteLLM spend logs, normalizes them into
    canonical request records, and writes them to the benchmark database.
    """
    import asyncio

    try:
        session_uuid = UUID(session_id)
    except ValueError as err:
        console.print("[red]Error: Invalid session ID[/red]")
        raise typer.Exit(1) from err

    if not litellm_key:
        console.print("[yellow]Warning: No LiteLLM API key provided. Set LITELLM_API_KEY env var.[/yellow]")

    def _run() -> tuple[int, CollectionDiagnostics]:
        db_session: SQLAlchemySession = get_db_session()
        try:
            repository = SQLRequestRepository(db_session)

            # Fetch raw requests synchronously
            raw_requests = asyncio.run(_fetch_litellm_requests(
                litellm_url=litellm_url,
                litellm_key=litellm_key,
                start_time=start_time,
                end_time=end_time,
            ))

            if not raw_requests:
                return 0, CollectionDiagnostics()

            if dry_run:
                diagnostics = CollectionDiagnostics()
                diagnostics.total_raw_records = len(raw_requests)
                diagnostics.normalized_count = sum(1 for r in raw_requests if r.get("request_id") and r.get("startTime"))
                return 0, diagnostics

            job = RequestNormalizerJob(
                repository=repository,
                session_id=session_uuid,
            )
            written, report = asyncio.run(job.run(raw_requests))

            # Convert report to diagnostics
            diagnostics = CollectionDiagnostics()
            diagnostics.total_raw_records = report.total_rows
            diagnostics.normalized_count = report.mapped_count
            diagnostics.skipped_count = report.unmapped_count
            diagnostics.missing_fields = report.missing_field_counts
            diagnostics.errors = [f"{k}: {v}" for k, v in report.error_counts.items()]

            db_session.commit()
            return len(written), diagnostics

        except Exception:
            db_session.rollback()
            raise
        finally:
            db_session.close()

    try:
        count, diagnostics = _run()

        # Display results
        console.print("\n[bold green]Collection Complete[/bold green]")
        console.print(f"Total raw records: {diagnostics.total_raw_records}")
        console.print(f"Normalized records: {diagnostics.normalized_count}")
        console.print(f"Skipped records: {diagnostics.skipped_count}")

        if dry_run:
            console.print("\n[yellow]Dry run mode - no records written[/yellow]")
        else:
            console.print(f"Records written: {count}")

        if diagnostics.missing_fields:
            console.print("\n[bold]Missing Fields:[/bold]")
            table = Table("Field", "Count")
            for field, count in sorted(
                diagnostics.missing_fields.items(),
                key=lambda x: x[1],
                reverse=True,
            ):
                table.add_row(field, str(count))
            console.print(table)

        if diagnostics.errors:
            console.print("\n[bold]Error Categories:[/bold]")
            for error in diagnostics.errors:
                console.print(f"  - {error}")

    except Exception as err:
        console.print(f"[red]Error during collection: {err}[/red]")
        raise typer.Exit(1) from err


@app.command(name="prometheus")
def collect_prometheus(
    session_id: Annotated[
        str,
        typer.Argument(help="Benchmark session ID to collect metrics for"),
    ],
    prometheus_url: Annotated[
        str,
        typer.Option(
            "--prometheus-url",
            "-u",
            help="Prometheus URL",
            envvar="PROMETHEUS_URL",
        ),
    ] = "http://localhost:9090",
    start_time: Annotated[
        str,
        typer.Option(
            "--start-time",
            "-s",
            help="Start time (RFC3339 or Unix timestamp)",
        ),
    ] = None,
    end_time: Annotated[
        str,
        typer.Option(
            "--end-time",
            "-e",
            help="End time (RFC3339 or Unix timestamp)",
        ),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            "-d",
            help="Show what would be collected without writing to database",
        ),
    ] = False,
) -> None:
    """Collect metrics from Prometheus for a session.

    Queries Prometheus for LLM metrics and computes derived rollups
    including latency percentiles, throughput, and error rates.
    """
    import asyncio

    from datetime import datetime, timezone, timedelta

    try:
        session_uuid = UUID(session_id)
    except ValueError as err:
        console.print("[red]Error: Invalid session ID[/red]")
        raise typer.Exit(1) from err

    # Default time range if not provided
    if not start_time:
        start_time = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    if not end_time:
        end_time = datetime.now(timezone.utc).isoformat()

    def _run() -> int:
        db_session: SQLAlchemySession = get_db_session()
        try:
            repository = SQLRollupRepository(db_session)
            collector = PrometheusCollector(
                base_url=prometheus_url,
                session_id=session_uuid,
            )

            rollups = asyncio.run(collector.collect_session_metrics(start_time, end_time))

            if not rollups:
                return 0

            if dry_run:
                return len(rollups)

            written = repository.create_many(rollups)
            db_session.commit()
            return len(written)

        except Exception:
            db_session.rollback()
            raise
        finally:
            db_session.close()

    try:
        count = _run()

        console.print("\n[bold green]Prometheus Collection Complete[/bold green]")
        console.print(f"Time range: {start_time} to {end_time}")

        if dry_run:
            console.print("\n[yellow]Dry run mode - no records written[/yellow]")
            console.print(f"Would write {count} rollups")
        else:
            console.print(f"Rollups written: {count}")

    except Exception as err:
        console.print(f"[red]Error during Prometheus collection: {err}[/red]")
        raise typer.Exit(1) from err


@app.command(name="rollup")
def compute_rollups(
    session_id: Annotated[
        str,
        typer.Argument(help="Benchmark session ID to compute rollups for"),
    ],
    compute_request: Annotated[
        bool,
        typer.Option(
            "--request-level",
            "-r",
            help="Compute request-level metrics",
        ),
    ] = True,
    compute_session: Annotated[
        bool,
        typer.Option(
            "--session-level",
            "-s",
            help="Compute session-level metrics",
        ),
    ] = True,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            "-d",
            help="Show what would be computed without writing to database",
        ),
    ] = False,
) -> None:
    """Compute rollup metrics for a session.

    Computes request-level and session-level metrics from normalized
    request data stored in the benchmark database.
    """
    import asyncio

    from sqlalchemy import select
    from benchmark_core.db.models import Request as RequestORM

    try:
        session_uuid = UUID(session_id)
    except ValueError as err:
        console.print("[red]Error: Invalid session ID[/red]")
        raise typer.Exit(1) from err

    def _run() -> tuple[int, int]:
        db_session: SQLAlchemySession = get_db_session()
        try:
            # Fetch all requests for the session
            stmt = select(RequestORM).where(RequestORM.session_id == session_uuid)
            result = db_session.execute(stmt)
            requests_orm = result.scalars().all()

            # Convert to domain models
            from benchmark_core.models import Request
            requests = [
                Request(
                    request_id=r.request_id,
                    session_id=r.session_id,
                    provider=r.provider,
                    model=r.model,
                    timestamp=r.timestamp,
                    latency_ms=r.latency_ms,
                    ttft_ms=r.ttft_ms,
                    tokens_prompt=r.tokens_prompt,
                    tokens_completion=r.tokens_completion,
                    error=r.error,
                    error_message=r.error_message,
                    cache_hit=r.cache_hit,
                    metadata=r.request_metadata,
                )
                for r in requests_orm
            ]

            rollup_job = RollupJob()
            rollups = []

            # Compute request-level metrics
            request_rollup_count = 0
            if compute_request:
                for request in requests:
                    request_rollups = asyncio.run(rollup_job.compute_request_metrics(request))
                    rollups.extend(request_rollups)
                    request_rollup_count += len(request_rollups)

            # Compute session-level metrics
            session_rollup_count = 0
            if compute_session:
                session_rollups = asyncio.run(rollup_job.compute_session_metrics(session_uuid, requests))
                rollups.extend(session_rollups)
                session_rollup_count = len(session_rollups)

            if dry_run or not rollups:
                return request_rollup_count, session_rollup_count

            # Write rollups to database
            repository = SQLRollupRepository(db_session)
            repository.create_many(rollups)
            db_session.commit()

            return request_rollup_count, session_rollup_count

        except Exception:
            db_session.rollback()
            raise
        finally:
            db_session.close()

    try:
        request_count, session_count = _run()

        console.print("\n[bold green]Rollup Computation Complete[/bold green]")
        console.print(f"Session ID: {session_id}")
        console.print(f"Request-level rollups: {request_count}")
        console.print(f"Session-level rollups: {session_count}")

        if dry_run:
            console.print("\n[yellow]Dry run mode - no records written[/yellow]")
        else:
            console.print(f"Total rollups written: {request_count + session_count}")

    except Exception as err:
        console.print(f"[red]Error during rollup computation: {err}[/red]")
        raise typer.Exit(1) from err


async def _fetch_litellm_requests(
    litellm_url: str,
    litellm_key: str,
    start_time: str | None,
    end_time: str | None,
) -> list[dict]:
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
            return data
        elif isinstance(data, dict) and "logs" in data:
            return data["logs"]
        else:
            return []