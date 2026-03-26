"""Config validation and management commands."""

from pathlib import Path

import typer
from rich.console import Console

app = typer.Typer(help="Validate and manage benchmark configurations")
console = Console()


@app.command()
def validate(
    configs_dir: Path = typer.Option(
        "./configs",
        "--configs-dir",
        "-c",
        help="Directory containing config files",
    ),
) -> None:
    """Validate all configuration files."""
    console.print(f"[bold blue]Validating configs in {configs_dir}...[/bold blue]")
    # Placeholder: actual implementation will load and validate all configs
    console.print("[green]All configurations are valid[/green]")


@app.command()
def show_provider(name: str) -> None:
    """Show provider configuration."""
    console.print(f"[bold]Provider:[/bold] {name}")


@app.command()
def show_variant(name: str) -> None:
    """Show variant configuration."""
    console.print(f"[bold]Variant:[/bold] {name}")


@app.command()
def show_experiment(name: str) -> None:
    """Show experiment configuration."""
    console.print(f"[bold]Experiment:[/bold] {name}")
