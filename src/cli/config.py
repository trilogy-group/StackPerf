"""Config management CLI commands."""

import click
from pathlib import Path
from rich.console import Console
from rich.table import Table

from benchmark_core.config import (
    ExperimentConfig,
    HarnessProfileConfig,
    ProviderConfig,
    Settings,
    TaskCardConfig,
    VariantConfig,
)

console = Console()


@click.group()
def config() -> None:
    """Configuration management commands."""
    pass


@config.command("validate")
@click.argument("config_file", type=click.Path(exists=True), required=False)
def validate_config(config_file: str | None) -> None:
    """Validate configuration files.

    If no file specified, validates all configs in the config root directory.
    """
    import yaml

    settings = Settings()
    config_root = settings.config_root

    errors: list[str] = []
    validated: list[str] = []

    def validate_yaml_file(path: Path, config_type: str, model_class: type) -> None:
        """Validate a single YAML config file."""
        try:
            content = yaml.safe_load(path.read_text())
            if content:
                model_class.model_validate(content)
                validated.append(f"{config_type}/{path.name}")
        except Exception as e:
            errors.append(f"{path}: {e}")

    if config_file:
        path = Path(config_file)
        # Infer config type from parent directory
        parent = path.parent.name
        model_map = {
            "providers": ProviderConfig,
            "harnesses": HarnessProfileConfig,
            "variants": VariantConfig,
            "experiments": ExperimentConfig,
            "task-cards": TaskCardConfig,
        }
        model_class = model_map.get(parent)
        if model_class:
            validate_yaml_file(path, parent, model_class)
    else:
        # Validate all config directories
        config_dirs = {
            "providers": ProviderConfig,
            "harnesses": HarnessProfileConfig,
            "variants": VariantConfig,
            "experiments": ExperimentConfig,
            "task-cards": TaskCardConfig,
        }

        for dir_name, model_class in config_dirs.items():
            dir_path = config_root / dir_name
            if dir_path.exists():
                for file_path in dir_path.glob("*.yaml"):
                    validate_yaml_file(file_path, dir_name, model_class)
                for file_path in dir_path.glob("*.yml"):
                    validate_yaml_file(file_path, dir_name, model_class)

    # Report results
    if validated:
        console.print("[green]Valid configurations:[/green]")
        for v in validated:
            console.print(f"  ✓ {v}")

    if errors:
        console.print("\n[red]Validation errors:[/red]")
        for e in errors:
            console.print(f"  ✗ {e}")
        raise click.Abort()

    if not validated and not errors:
        console.print("[dim]No configuration files found[/dim]")


@config.command("list")
@click.argument("config_type", type=click.Choice(["providers", "harnesses", "variants", "experiments", "task-cards", "all"]))
def list_configs(config_type: str) -> None:
    """List available configurations."""
    import yaml

    settings = Settings()
    config_root = settings.config_root

    config_dirs = ["providers", "harnesses", "variants", "experiments", "task-cards"]
    if config_type != "all":
        config_dirs = [config_type]

    for dir_name in config_dirs:
        dir_path = config_root / dir_name
        if not dir_path.exists():
            continue

        files = list(dir_path.glob("*.yaml")) + list(dir_path.glob("*.yml"))
        if not files:
            continue

        console.print(f"\n[bold]{dir_name.title()}:[/bold]")
        for file_path in files:
            try:
                content = yaml.safe_load(file_path.read_text())
                name = content.get("name", file_path.stem) if content else file_path.stem
                desc = content.get("description", "")[:50] if content else ""
                console.print(f"  • {name}")
                if desc:
                    console.print(f"    [dim]{desc}[/dim]")
            except Exception:
                console.print(f"  • {file_path.stem} [red](error loading)[/red]")


@config.command("show")
@click.argument("config_type", type=click.Choice(["provider", "harness", "variant", "experiment", "task-card"]))
@click.argument("name")
def show_config(config_type: str, name: str) -> None:
    """Show a specific configuration."""
    import yaml

    settings = Settings()
    config_root = settings.config_root

    # Map singular to plural
    type_map = {
        "provider": "providers",
        "harness": "harnesses",
        "variant": "variants",
        "experiment": "experiments",
        "task-card": "task-cards",
    }
    dir_name = type_map[config_type]
    dir_path = config_root / dir_name

    # Find the file
    for ext in [".yaml", ".yml"]:
        file_path = dir_path / f"{name}{ext}"
        if file_path.exists():
            break
    else:
        console.print(f"[red]Configuration not found: {config_type}/{name}[/red]")
        raise click.Abort()

    try:
        content = yaml.safe_load(file_path.read_text())
        console.print(f"\n[bold]{config_type.title()}: {name}[/bold]\n")
        console.print(yaml.dump(content, default_flow_style=False, sort_keys=False))
    except Exception as e:
        console.print(f"[red]Error loading configuration: {e}[/red]")
        raise click.Abort()
