"""Config validation and onboarding commands."""

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table
from sqlalchemy.orm import Session as SQLAlchemySession

from benchmark_core.config_loader import ConfigLoader, ConfigValidationError
from benchmark_core.db.models import (
    Experiment,
    ExperimentVariant,
    HarnessProfile,
    Provider,
    ProviderModel,
    Variant,
)
from benchmark_core.db.models import TaskCard as DBTaskCard
from benchmark_core.db.session import get_db_session, init_db

app = typer.Typer(help="Validate and manage benchmark configurations")
console = Console()


def _load_registry(configs_dir: Path) -> ConfigLoader:
    loader = ConfigLoader(configs_dir=configs_dir)
    loader.load_all()
    return loader


def _print_name_table(title: str, names: list[str]) -> None:
    if not names:
        console.print(f"[yellow]No {title.lower()} found[/yellow]")
        return

    table = Table(title=title)
    table.add_column("Name", style="green")
    for name in names:
        table.add_row(name)
    console.print(table)


def _upsert_provider(db: SQLAlchemySession, provider_config) -> Provider:
    provider = db.query(Provider).filter_by(name=provider_config.name).one_or_none()
    if provider is None:
        provider = Provider(
            name=provider_config.name,
            protocol_surface=provider_config.protocol_surface,
            upstream_base_url_env=provider_config.upstream_base_url_env,
            api_key_env=provider_config.api_key_env,
        )
        db.add(provider)

    provider.route_name = provider_config.route_name
    provider.protocol_surface = provider_config.protocol_surface
    provider.upstream_base_url_env = provider_config.upstream_base_url_env
    provider.api_key_env = provider_config.api_key_env
    provider.routing_defaults = provider_config.routing_defaults.model_dump()

    provider.models.clear()
    for model in provider_config.models:
        provider.models.append(
            ProviderModel(alias=model.alias, upstream_model=model.upstream_model)
        )

    return provider


def _upsert_harness_profile(db: SQLAlchemySession, profile_config) -> HarnessProfile:
    profile = db.query(HarnessProfile).filter_by(name=profile_config.name).one_or_none()
    if profile is None:
        profile = HarnessProfile(
            name=profile_config.name,
            protocol_surface=profile_config.protocol_surface,
            base_url_env=profile_config.base_url_env,
            api_key_env=profile_config.api_key_env,
            model_env=profile_config.model_env,
        )
        db.add(profile)

    profile.protocol_surface = profile_config.protocol_surface
    profile.base_url_env = profile_config.base_url_env
    profile.api_key_env = profile_config.api_key_env
    profile.model_env = profile_config.model_env
    profile.extra_env = profile_config.extra_env
    profile.render_format = profile_config.render_format
    profile.launch_checks = profile_config.launch_checks
    return profile


def _upsert_variant(db: SQLAlchemySession, variant_config) -> Variant:
    variant = db.query(Variant).filter_by(name=variant_config.name).one_or_none()
    if variant is None:
        variant = Variant(
            name=variant_config.name,
            provider=variant_config.provider,
            model_alias=variant_config.model_alias,
            harness_profile=variant_config.harness_profile,
        )
        db.add(variant)

    variant.provider = variant_config.provider
    variant.provider_route = variant_config.provider_route
    variant.model_alias = variant_config.model_alias
    variant.harness_profile = variant_config.harness_profile
    variant.harness_env_overrides = variant_config.harness_env_overrides
    variant.benchmark_tags = variant_config.benchmark_tags
    return variant


def _upsert_task_card(db: SQLAlchemySession, task_card_config) -> DBTaskCard:
    task_card = db.query(DBTaskCard).filter_by(name=task_card_config.name).one_or_none()
    if task_card is None:
        task_card = DBTaskCard(
            name=task_card_config.name,
            goal=task_card_config.goal,
            starting_prompt=task_card_config.starting_prompt,
            stop_condition=task_card_config.stop_condition,
        )
        db.add(task_card)

    task_card.repo_path = task_card_config.repo_path
    task_card.goal = task_card_config.goal
    task_card.starting_prompt = task_card_config.starting_prompt
    task_card.stop_condition = task_card_config.stop_condition
    task_card.session_timebox_minutes = task_card_config.session_timebox_minutes
    task_card.notes = task_card_config.notes
    return task_card


def _upsert_experiment(
    db: SQLAlchemySession, experiment_config, variant_map: dict[str, Variant]
) -> Experiment:
    experiment = db.query(Experiment).filter_by(name=experiment_config.name).one_or_none()
    if experiment is None:
        experiment = Experiment(
            name=experiment_config.name, description=experiment_config.description
        )
        db.add(experiment)

    experiment.description = experiment_config.description
    experiment.experiment_variants.clear()
    db.flush()

    for variant_name in experiment_config.variants:
        experiment.experiment_variants.append(
            ExperimentVariant(variant_id=variant_map[variant_name].id)
        )

    return experiment


@app.command()
def validate(
    configs_dir: Path = typer.Option(
        Path("./configs"),
        "--configs-dir",
        "-c",
        help="Directory containing config files",
    ),
) -> None:
    """Validate all configuration files."""
    console.print(f"[bold blue]Validating configs in {configs_dir}...[/bold blue]")

    if not configs_dir.exists():
        console.print(f"[red]Error: Config directory does not exist: {configs_dir}[/red]")
        raise typer.Exit(1)

    if not configs_dir.is_dir():
        console.print(f"[red]Error: Path is not a directory: {configs_dir}[/red]")
        raise typer.Exit(1)

    try:
        loader = _load_registry(configs_dir)
    except ConfigValidationError as err:
        console.print("[red]Configuration validation failed:[/red]")
        for error in err.errors:
            console.print(f"  - {error}")
        raise typer.Exit(1) from err

    console.print("[green]Configuration validation passed[/green]")
    console.print(f"  Providers: {len(loader.registry.providers)}")
    console.print(f"  Harness profiles: {len(loader.registry.harness_profiles)}")
    console.print(f"  Variants: {len(loader.registry.variants)}")
    console.print(f"  Experiments: {len(loader.registry.experiments)}")
    console.print(f"  Task cards: {len(loader.registry.task_cards)}")


@app.command("list-providers")
def list_providers(
    configs_dir: Path = typer.Option(
        Path("configs"), "--configs-dir", help="Configuration directory"
    ),
) -> None:
    """List available providers from config files."""
    loader = _load_registry(configs_dir)
    _print_name_table("Providers", sorted(loader.registry.providers.keys()))


@app.command("list-harnesses")
def list_harnesses(
    configs_dir: Path = typer.Option(
        Path("configs"), "--configs-dir", help="Configuration directory"
    ),
) -> None:
    """List available harness profiles from config files."""
    loader = _load_registry(configs_dir)
    _print_name_table("Harness Profiles", sorted(loader.registry.harness_profiles.keys()))


@app.command("list-variants")
def list_variants(
    configs_dir: Path = typer.Option(
        Path("configs"), "--configs-dir", help="Configuration directory"
    ),
) -> None:
    """List available variants from config files."""
    loader = _load_registry(configs_dir)
    _print_name_table("Variants", sorted(loader.registry.variants.keys()))


@app.command("list-experiments")
def list_experiments(
    configs_dir: Path = typer.Option(
        Path("configs"), "--configs-dir", help="Configuration directory"
    ),
) -> None:
    """List available experiments from config files."""
    loader = _load_registry(configs_dir)
    _print_name_table("Experiments", sorted(loader.registry.experiments.keys()))


@app.command("list-task-cards")
def list_task_cards(
    configs_dir: Path = typer.Option(
        Path("configs"), "--configs-dir", help="Configuration directory"
    ),
) -> None:
    """List available task cards from config files."""
    loader = _load_registry(configs_dir)
    _print_name_table("Task Cards", sorted(loader.registry.task_cards.keys()))


@app.command("init-db")
def initialize_database(
    configs_dir: Path = typer.Option(
        Path("configs"), "--configs-dir", help="Configuration directory"
    ),
    skip_sync: bool = typer.Option(
        False, "--skip-sync", help="Only create schema, do not sync configs into the database"
    ),
) -> None:
    """Create the benchmark schema and sync configuration records into the database."""
    console.print("[bold blue]Initializing benchmark database...[/bold blue]")
    init_db()
    console.print("[green]Schema initialized[/green]")

    if skip_sync:
        return

    try:
        loader = _load_registry(configs_dir)
    except ConfigValidationError as err:
        console.print("[red]Configuration validation failed:[/red]")
        for error in err.errors:
            console.print(f"  - {error}")
        raise typer.Exit(1) from err

    with get_db_session() as db:
        for provider in loader.registry.providers.values():
            _upsert_provider(db, provider)

        for harness in loader.registry.harness_profiles.values():
            _upsert_harness_profile(db, harness)

        variant_map: dict[str, Variant] = {}
        for variant in loader.registry.variants.values():
            variant_map[variant.name] = _upsert_variant(db, variant)

        for task_card in loader.registry.task_cards.values():
            _upsert_task_card(db, task_card)

        for experiment in loader.registry.experiments.values():
            _upsert_experiment(db, experiment, variant_map)

    console.print("[green]Configuration records synced into the database[/green]")
    console.print(f"  Providers: {len(loader.registry.providers)}")
    console.print(f"  Harness profiles: {len(loader.registry.harness_profiles)}")
    console.print(f"  Variants: {len(loader.registry.variants)}")
    console.print(f"  Experiments: {len(loader.registry.experiments)}")
    console.print(f"  Task cards: {len(loader.registry.task_cards)}")


@app.command()
def show_provider(
    name: str,
    configs_dir: Path = typer.Option(
        Path("configs"), "--configs-dir", help="Configuration directory"
    ),
) -> None:
    """Show provider configuration."""
    loader = _load_registry(configs_dir)
    provider = loader.registry.providers.get(name)
    if provider is None:
        console.print(f"[red]Provider not found: {name}[/red]")
        raise typer.Exit(1)
    console.print(provider.model_dump_json(indent=2))


@app.command()
def show_variant(
    name: str,
    configs_dir: Path = typer.Option(
        Path("configs"), "--configs-dir", help="Configuration directory"
    ),
) -> None:
    """Show variant configuration."""
    loader = _load_registry(configs_dir)
    variant = loader.registry.variants.get(name)
    if variant is None:
        console.print(f"[red]Variant not found: {name}[/red]")
        raise typer.Exit(1)
    console.print(variant.model_dump_json(indent=2))


@app.command()
def show_experiment(
    name: str,
    configs_dir: Path = typer.Option(
        Path("configs"), "--configs-dir", help="Configuration directory"
    ),
) -> None:
    """Show experiment configuration."""
    loader = _load_registry(configs_dir)
    experiment = loader.registry.experiments.get(name)
    if experiment is None:
        console.print(f"[red]Experiment not found: {name}[/red]")
        raise typer.Exit(1)
    console.print(experiment.model_dump_json(indent=2))
