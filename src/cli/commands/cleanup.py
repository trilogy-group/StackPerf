"""CLI commands for retention cleanup and data lifecycle management."""

from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from benchmark_core.security import RetentionSettings
from collectors.retention_cleanup import (
    CleanupDiagnostics,
    CredentialCleanupJob,
    CredentialCleanupResult,
    RetentionCleanupJob,
)

app = typer.Typer(
    name="cleanup",
    help="Retention cleanup and data lifecycle management",
    rich_markup_mode="rich",
)
console = Console()


@app.command(name="retention")
def run_retention_cleanup(
    data_type: Annotated[
        str | None,
        typer.Option(
            "--type",
            "-t",
            help="Specific data type to cleanup (raw_ingestion, normalized_requests, sessions, session_credentials, artifacts, metric_rollups). Omit to cleanup all.",
        ),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            "-d",
            help="Show what would be cleaned without making changes",
        ),
    ] = False,
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            "-f",
            help="Skip confirmation prompt (use with caution)",
        ),
    ] = False,
    batch_size: Annotated[
        int,
        typer.Option(
            "--batch-size",
            "-b",
            help="Number of records to process per batch",
        ),
    ] = 1000,
) -> None:
    """Run retention cleanup to remove expired data.

    By default, this will remove data that has exceeded its retention period.
    Session credentials are cleaned with the shortest retention (1 day).
    Raw ingestion records are cleaned after 7 days.
    Normalized requests and artifacts after 30 days.
    Sessions and metric rollups after 90 days.

    Use --dry-run to preview what would be cleaned without making changes.
    """
    import asyncio

    # Load retention settings
    settings = RetentionSettings()

    # Show what will be cleaned
    console.print("[bold blue]Retention Cleanup[/bold blue]")
    console.print()

    # Determine data types to process
    if data_type:
        data_types = [data_type]
        if data_type not in [
            "raw_ingestion",
            "normalized_requests",
            "sessions",
            "session_credentials",
            "artifacts",
            "metric_rollups",
        ]:
            console.print(f"[red]Error: Unknown data type: {data_type}[/red]")
            console.print(
                "Valid types: raw_ingestion, normalized_requests, sessions, session_credentials, artifacts, metric_rollups"
            )
            raise typer.Exit(1)
    else:
        data_types = [
            "raw_ingestion",
            "normalized_requests",
            "sessions",
            "session_credentials",
            "artifacts",
            "metric_rollups",
        ]

    # Show retention policies
    table = Table("Data Type", "Retention Days", "Cutoff Date", "Archive Before Delete")
    for dt in data_types:
        policy = settings.get_policy(dt)
        if policy:
            cutoff = policy.get_cutoff_date()
            cutoff_str = cutoff.strftime("%Y-%m-%d") if cutoff else "No limit"
            table.add_row(
                dt,
                str(policy.retention_days) if policy.retention_days else "Keep forever",
                cutoff_str,
                "Yes" if policy.archive_before_delete else "No",
            )
    console.print(table)
    console.print()

    if dry_run:
        console.print("[yellow]DRY RUN MODE: No changes will be made[/yellow]")
        console.print()

    # Confirmation prompt for non-dry-run
    if not dry_run and not force:
        console.print(
            "[yellow]Warning: This will permanently delete data that has exceeded its retention period.[/yellow]"
        )
        if data_type == "sessions":
            console.print(
                "[red]Critical: Session deletion will cascade to related request records.[/red]"
            )
        console.print()

        confirmed = typer.confirm("Do you want to proceed with cleanup?")
        if not confirmed:
            console.print("[yellow]Cleanup cancelled.[/yellow]")
            raise typer.Exit(0)
        console.print()

    # Run cleanup
    async def _run_cleanup() -> CleanupDiagnostics:
        job = RetentionCleanupJob(settings=settings)
        return await job.run_cleanup(data_types=data_types if data_type else None)

    try:
        diagnostics = asyncio.run(_run_cleanup())

        # Display results
        console.print("[bold green]Cleanup Complete[/bold green]")
        console.print(f"Policies checked: {diagnostics.policies_checked}")
        console.print(f"Total eligible for cleanup: {diagnostics.total_eligible}")
        console.print()

        if diagnostics.cleanup_stats:
            results_table = Table(
                "Data Type", "Deleted", "Archived", "Skipped", "Errors", "Duration"
            )
            for data_type_key, result in diagnostics.cleanup_stats.items():
                duration_str = (
                    f"{result.duration_seconds:.1f}s" if result.duration_seconds else "N/A"
                )
                results_table.add_row(
                    data_type_key,
                    str(result.deleted_count),
                    str(result.archived_count),
                    str(result.skipped_count),
                    str(result.error_count),
                    duration_str,
                )
            console.print(results_table)

        if dry_run:
            console.print()
            console.print("[yellow]This was a dry run. No data was actually deleted.[/yellow]")
            console.print("Run without --dry-run to perform actual cleanup.")

    except Exception as e:
        console.print(f"[red]Error during cleanup: {e}[/red]")
        raise typer.Exit(1) from e


@app.command(name="credentials")
def cleanup_expired_credentials(
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            "-d",
            help="Show what would be cleaned without making changes",
        ),
    ] = False,
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            "-f",
            help="Skip confirmation prompt (use with caution)",
        ),
    ] = False,
) -> None:
    """Clean up expired session credentials.

    Session credentials have a very short retention period (1 day by default).
    This command finds and revokes credentials that have expired.
    """
    import asyncio

    console.print("[bold blue]Credential Cleanup[/bold blue]")
    console.print("Session credentials have a 1-day retention period.")
    console.print()

    if dry_run:
        console.print("[yellow]DRY RUN MODE: No credentials will be revoked[/yellow]")
        console.print()

    # Confirmation prompt
    if not dry_run and not force:
        console.print("[yellow]Warning: This will revoke expired session credentials.[/yellow]")
        confirmed = typer.confirm("Do you want to proceed?")
        if not confirmed:
            console.print("[yellow]Cleanup cancelled.[/yellow]")
            raise typer.Exit(0)
        console.print()

    # Run cleanup
    async def _run_cleanup() -> CredentialCleanupResult:
        job = CredentialCleanupJob()
        return await job.cleanup_expired_credentials()

    try:
        result = asyncio.run(_run_cleanup())

        console.print("[bold green]Credential Cleanup Complete[/bold green]")
        console.print(f"Total credentials checked: {result.total_checked}")
        console.print(f"Credentials revoked: {result.revoked_count}")
        console.print(f"Credentials expired: {result.expired_count}")

        if result.errors:
            console.print()
            console.print("[yellow]Errors encountered:[/yellow]")
            for error in result.errors:
                console.print(f"  - {error}")

        if dry_run:
            console.print()
            console.print(
                "[yellow]This was a dry run. No credentials were actually revoked.[/yellow]"
            )

    except Exception as e:
        console.print(f"[red]Error during credential cleanup: {e}[/red]")
        raise typer.Exit(1) from e


@app.command(name="status")
def show_retention_status() -> None:
    """Show current retention policy status.

    Displays the configured retention periods for each data type
    and shows the cutoff dates for cleanup eligibility.
    """
    settings = RetentionSettings()

    console.print("[bold blue]Retention Policy Status[/bold blue]")
    console.print()

    table = Table(
        "Data Type",
        "Retention (Days)",
        "Min Age (Days)",
        "Batch Size",
        "Cutoff Date",
        "Archive",
    )

    policies = [
        ("Raw Ingestion", settings.raw_ingestion),
        ("Normalized Requests", settings.normalized_requests),
        ("Sessions", settings.sessions),
        ("Session Credentials", settings.session_credentials),
        ("Artifacts", settings.artifacts),
        ("Metric Rollups", settings.metric_rollups),
    ]

    for name, policy in policies:
        cutoff = policy.get_cutoff_date()
        cutoff_str = cutoff.strftime("%Y-%m-%d %H:%M") if cutoff else "Never"
        retention_str = str(policy.retention_days) if policy.retention_days else "∞ (Keep forever)"

        table.add_row(
            name,
            retention_str,
            str(policy.min_age_days),
            str(policy.cleanup_batch_size),
            cutoff_str,
            "Yes" if policy.archive_before_delete else "No",
        )

    console.print(table)
    console.print()
    console.print("Use [bold]benchmark cleanup retention[/bold] to run cleanup.")
    console.print("Use [bold]benchmark cleanup retention --dry-run[/bold] to preview cleanup.")
