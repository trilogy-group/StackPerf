"""Main CLI entry point using Typer."""

import typer
from rich.console import Console

from cli.commands import config, export, normalize, session

app = typer.Typer(
    name="benchmark",
    help="LiteLLM Benchmarking System CLI",
    rich_markup_mode="rich",
)

# Register subcommands
app.add_typer(config.app, name="config", help="Config validation and management")
app.add_typer(session.app, name="session", help="Session lifecycle commands")
app.add_typer(export.app, name="export", help="Export commands for reports")
app.add_typer(normalize.app, name="normalize", help="Normalize LiteLLM request data")

console = Console()


@app.callback()
def callback() -> None:
    """LiteLLM Benchmarking System - Compare providers, models, harnesses, and configurations."""
    pass


@app.command()
def version() -> None:
    """Show version information."""
    from benchmark_core import __version__

    console.print(f"[bold green]LiteLLM Benchmark[/bold green] version {__version__}")


if __name__ == "__main__":
    app()
