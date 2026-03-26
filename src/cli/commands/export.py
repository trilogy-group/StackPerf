"""Export commands for reports and comparisons."""

from pathlib import Path

import typer
from rich.console import Console

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
    format: str = typer.Option("json", "--format", "-f", help="Export format (json, csv)"),
) -> None:
    """Export a single session report."""
    console.print(f"[bold blue]Exporting session {session_id}...[/bold blue]")
    # Placeholder: actual implementation will export session data
    console.print(f"[green]Exported to {output}[/green]")


@app.command()
def comparison(
    experiment: str = typer.Option(..., "--experiment", "-e", help="Experiment ID"),
    output: Path = typer.Option(
        Path("./output"),
        "--output",
        "-o",
        help="Output directory",
    ),
    format: str = typer.Option("json", "--format", "-f", help="Export format"),
) -> None:
    """Export experiment comparison results."""
    console.print(f"[bold blue]Exporting comparison for {experiment}...[/bold blue]")
    # Placeholder: actual implementation will export comparison
    console.print(f"[green]Exported to {output}[/green]")


@app.command()
def artifacts(
    output: Path = typer.Option(
        Path("./output"),
        "--output",
        "-o",
        help="Output directory",
    ),
) -> None:
    """Export raw benchmark bundle."""
    console.print("[bold blue]Exporting artifacts...[/bold blue]")
    # Placeholder: actual implementation will export artifacts
    console.print(f"[green]Exported to {output}[/green]")
