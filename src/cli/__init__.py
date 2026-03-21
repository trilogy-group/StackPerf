"""StackPerf CLI commands."""

import click
from rich.console import Console

from src import __version__

console = Console()


@click.group()
@click.version_option(version=__version__, prog_name="stackperf")
def main() -> None:
    """StackPerf - Harness-agnostic benchmarking system."""
    pass


@main.command()
def version() -> None:
    """Show version information."""
    console.print(f"StackPerf version: {__version__}")


if __name__ == "__main__":
    main()
