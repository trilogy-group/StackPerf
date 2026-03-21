"""StackPerf benchmark CLI."""

import click
from rich.console import Console

console = Console()


@click.group()
@click.version_option(version="0.1.0", prog_name="stackperf")
def main() -> None:
    """StackPerf - Local-first benchmarking system for LLM providers and harnesses."""
    pass


# Define sub-command groups
@main.group()
def session() -> None:
    """Session lifecycle commands."""
    pass


# Import and register commands after groups are defined
from . import session as session_commands  # noqa: E402, F401
