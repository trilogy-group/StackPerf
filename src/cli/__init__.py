"""CLI commands for StackPerf benchmarking."""

import click

from benchmark_core import __version__


@click.group()
@click.version_option(version=__version__)
def main() -> None:
    """StackPerf - LiteLLM benchmarking system."""
    pass


@main.command()
def config_validate() -> None:
    """Validate all configuration files."""
    click.echo("Config validation: TODO")


@main.command()
def experiment_list() -> None:
    """List available experiments."""
    click.echo("Experiments: TODO")


@main.command()
def variant_list() -> None:
    """List available variants."""
    click.echo("Variants: TODO")


@main.command()
def task_card_list() -> None:
    """List available task cards."""
    click.echo("Task cards: TODO")


if __name__ == "__main__":
    main()
