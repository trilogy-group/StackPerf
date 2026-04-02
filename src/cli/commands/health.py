"""Health check and diagnostics commands."""

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from benchmark_core.services.diagnostics_service import (
    DiagnosticsService,
)
from benchmark_core.services.health_service import (
    HealthService,
    HealthStatus,
)

app = typer.Typer(help="Stack health checks and diagnostics")
console = Console()


@app.command()
def check(
    configs_dir: Path = typer.Option(
        Path("./configs"),
        "--configs-dir",
        "-c",
        help="Directory containing config files",
        exists=False,
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        "-j",
        help="Output in JSON format",
    ),
) -> None:
    """Run health checks on all stack components.

    Checks database connectivity, LiteLLM proxy health, Prometheus metrics,
    and configuration validity. Returns exit code 0 if healthy, 1 if unhealthy.

    This command should be run before launching benchmark sessions to ensure
    all required services are available and properly configured.
    """
    if not json_output:
        console.print("[bold blue]Running stack health checks...[/bold blue]\n")

    service = HealthService()
    report = service.run_health_checks(str(configs_dir))

    if json_output:
        import json

        output = {
            "status": report.status.value,
            "summary": report.summary,
            "checks": [
                {
                    "component": check.component,
                    "status": check.status.value,
                    "message": check.message,
                    "details": check.details,
                    "action": check.action,
                }
                for check in report.checks
            ],
        }
        print(json.dumps(output, indent=2))
    else:
        # Display results in a table
        table = Table(title="Health Check Results")
        table.add_column("Component", style="cyan", no_wrap=True)
        table.add_column("Status", no_wrap=True)
        table.add_column("Message")
        table.add_column("Action", style="dim")

        for check in report.checks:
            # Choose color and symbol based on status
            if check.status == HealthStatus.HEALTHY:
                status_str = "[green]✓ healthy[/green]"
            elif check.status == HealthStatus.DEGRADED:
                status_str = "[yellow]⚠ degraded[/yellow]"
            else:
                status_str = "[red]✗ unhealthy[/red]"

            table.add_row(
                check.component,
                status_str,
                check.message,
                check.action or "",
            )

        console.print(table)

        # Print summary
        console.print()
        if report.status == HealthStatus.HEALTHY:
            console.print(f"[green]✓ {report.summary}[/green]")
        elif report.status == HealthStatus.DEGRADED:
            console.print(f"[yellow]⚠ {report.summary}[/yellow]")
        else:
            console.print(f"[red]✗ {report.summary}[/red]")

    # Exit with appropriate code
    if report.is_healthy():
        raise typer.Exit(0)
    else:
        raise typer.Exit(1)


@app.command()
def diagnose(
    configs_dir: Path = typer.Option(
        Path("./configs"),
        "--configs-dir",
        "-c",
        help="Directory containing config files",
        exists=False,
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        "-j",
        help="Output in JSON format",
    ),
    category: str | None = typer.Option(
        None,
        "--category",
        "-C",
        help="Filter to specific category (environment, configuration, services)",
    ),
) -> None:
    """Run comprehensive diagnostics on environment, configuration, and services.

    Provides detailed information about:
    - Environment variables and paths
    - Configuration files and their validity
    - Service connectivity and status

    Diagnostics point directly to failing configuration or service issues
    and provide actionable suggestions for resolution.
    """
    if not json_output:
        console.print("[bold blue]Running stack diagnostics...[/bold blue]\n")

    service = DiagnosticsService(configs_dir=str(configs_dir))
    report = service.run_diagnostics()

    if json_output:
        import json

        output = {
            "has_errors": report.has_errors(),
            "errors_count": len(report.get_errors()),
            "warnings_count": len(report.get_warnings()),
            "environment": [
                {
                    "category": d.category,
                    "name": d.name,
                    "status": d.status,
                    "value": d.value,
                    "message": d.message,
                    "suggestion": d.suggestion,
                }
                for d in report.environment
            ],
            "configuration": [
                {
                    "category": d.category,
                    "name": d.name,
                    "status": d.status,
                    "value": d.value,
                    "message": d.message,
                    "suggestion": d.suggestion,
                }
                for d in report.configuration
            ],
            "services": [
                {
                    "category": d.category,
                    "name": d.name,
                    "status": d.status,
                    "value": d.value,
                    "message": d.message,
                    "suggestion": d.suggestion,
                }
                for d in report.services
            ],
        }
        print(json.dumps(output, indent=2))
    else:
        # Display diagnostics by category
        categories_to_show = ["environment", "configuration", "services"]
        if category and category in categories_to_show:
            categories_to_show = [category]

        for cat in categories_to_show:
            if cat == "environment":
                diagnostics = report.environment
                title = "Environment"
            elif cat == "configuration":
                diagnostics = report.configuration
                title = "Configuration"
            else:  # services
                diagnostics = report.services
                title = "Services"

            if not diagnostics:
                continue

            table = Table(title=f"{title} Diagnostics")
            table.add_column("Name", style="cyan", no_wrap=True)
            table.add_column("Status", no_wrap=True)
            table.add_column("Value")
            table.add_column("Message")
            table.add_column("Suggestion", style="dim")

            for diag in diagnostics:
                # Choose color based on status
                if diag.status == "ok":
                    status_str = "[green]✓ ok[/green]"
                elif diag.status == "warning":
                    status_str = "[yellow]⚠ warning[/yellow]"
                else:
                    status_str = "[red]✗ error[/red]"

                # Format value for display
                value_str = ""
                if diag.value is not None:
                    if isinstance(diag.value, dict):
                        value_str = ", ".join(f"{k}={v}" for k, v in list(diag.value.items())[:3])
                        if len(diag.value) > 3:
                            value_str += " ..."
                    elif isinstance(diag.value, list):
                        value_str = ", ".join(str(v) for v in diag.value[:3])
                        if len(diag.value) > 3:
                            value_str += " ..."
                    else:
                        value_str = str(diag.value)

                table.add_row(
                    diag.name,
                    status_str,
                    value_str[:50] if len(value_str) > 50 else value_str,
                    diag.message or "",
                    diag.suggestion or "",
                )

            console.print(table)
            console.print()

        # Print summary
        errors = report.get_errors()
        warnings = report.get_warnings()

        if errors:
            console.print(f"[red]✗ Found {len(errors)} error(s)[/red]")
            for error in errors[:3]:  # Show first 3 errors
                console.print(f"  [red]• {error.name}: {error.message}[/red]")
                if error.suggestion:
                    console.print(f"    [dim]Suggestion: {error.suggestion}[/dim]")
            if len(errors) > 3:
                console.print(f"  [dim]... and {len(errors) - 3} more errors[/dim]")
            console.print()

        if warnings:
            console.print(f"[yellow]⚠ Found {len(warnings)} warning(s)[/yellow]")
            for warning in warnings[:3]:  # Show first 3 warnings
                console.print(f"  [yellow]• {warning.name}: {warning.message}[/yellow]")
                if warning.suggestion:
                    console.print(f"    [dim]Suggestion: {warning.suggestion}[/dim]")
            if len(warnings) > 3:
                console.print(f"  [dim]... and {len(warnings) - 3} more warnings[/dim]")
            console.print()

        if not errors and not warnings:
            console.print("[green]✓ All diagnostics passed[/green]")

    # Exit with error code if there are errors
    if report.has_errors():
        raise typer.Exit(1)
    else:
        raise typer.Exit(0)
