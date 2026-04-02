"""Environment rendering commands for harness profiles."""

from pathlib import Path

import typer
from rich.console import Console
from rich.syntax import Syntax

from benchmark_core.config import HarnessProfile, Variant
from benchmark_core.config_loader import ConfigLoader
from benchmark_core.services.rendering import (
    EnvRenderingService,
    ProfileValidationError,
    RenderingError,
)

app = typer.Typer(help="Render and validate harness environment snippets")
console = Console()


@app.command("env")
def render_env(
    variant_name: str = typer.Option(..., "--variant", "-v", help="Variant name"),
    harness_profile: str | None = typer.Option(
        None, "--profile", "-p", help="Harness profile name (overrides variant)"
    ),
    credential: str | None = typer.Option(
        None, "--credential", "-c", help="Session credential (API key)"
    ),
    proxy_url: str = typer.Option(
        "http://localhost:4000", "--proxy", "-u", help="LiteLLM proxy base URL"
    ),
    output_format: str = typer.Option(
        "shell", "--format", "-f", help="Output format: shell, dotenv, json, or toml"
    ),
    include_secrets: bool = typer.Option(
        False, "--secrets", "-s", help="Include actual credential value in output"
    ),
    configs_dir: Path = typer.Option(
        Path("configs"),
        "--configs-dir",
        help="Configuration directory containing harnesses/ and variants/",
    ),
) -> None:
    """Render environment snippet for a variant and harness profile.

    The rendered output:
    - Uses correct variable names for the harness profile
    - Includes variant overrides deterministically
    - Never writes secrets into tracked files (use --secrets to override)

    Examples:
        # Render shell environment for a variant
        benchmark render env --variant fireworks-glm-5-claude-code

        # Render dotenv format
        benchmark render env --variant openai-gpt-4o-cli --format dotenv

        # Include actual credential value (for copy-paste to harness)
        benchmark render env --variant my-variant --secrets --credential sk-xxx
    """
    try:
        # Load configurations
        loader = ConfigLoader(configs_dir=configs_dir)

        # Load variant
        variant_config = loader.load_variant(variant_name)
        if variant_config is None:
            console.print(f"[red]Error: Variant '{variant_name}' not found[/red]")
            console.print(
                f"[dim]Looking in: {configs_dir / 'variants' / f'{variant_name}.yaml'}[/dim]"
            )
            raise typer.Exit(1)

        variant = Variant(**variant_config)

        # Determine harness profile (use override or from variant)
        profile_name = harness_profile if harness_profile else variant.harness_profile

        # Load harness profile
        profile_config = loader.load_harness_profile(profile_name)
        if profile_config is None:
            console.print(f"[red]Error: Harness profile '{profile_name}' not found[/red]")
            console.print(
                f"[dim]Looking in: {configs_dir / 'harnesses' / f'{profile_name}.yaml'}[/dim]"
            )
            raise typer.Exit(1)

        profile = HarnessProfile(**profile_config)

        # Create rendering service
        service = EnvRenderingService()

        # Validate compatibility
        compatibility_errors = service.validate_variant_profile_compatibility(variant, profile)
        if compatibility_errors:
            console.print("[yellow]Compatibility warnings:[/yellow]")
            for error in compatibility_errors:
                console.print(f"  - {error}")
            console.print()

        # Validate format
        if output_format not in ("shell", "dotenv", "json", "toml"):
            console.print(
                f"[red]Error: Invalid format '{output_format}'. Use 'shell', 'dotenv', 'json', or 'toml'.[/red]"
            )
            raise typer.Exit(1)

        # Render environment snippet
        try:
            snippet = service.render_env_snippet(
                harness_profile=profile,
                variant=variant,
                credential=credential,
                proxy_base_url=proxy_url,
                format_override=output_format,
                include_secrets=include_secrets,
            )

            # Display metadata
            console.print(f"[bold blue]Environment for variant: {variant_name}[/bold blue]")
            console.print(f"  Harness Profile: {profile_name}")
            console.print(f"  Model: {variant.model_alias}")
            console.print(f"  Format: {snippet.format}")
            console.print(f"  Variables: {len(snippet.env_vars)}")
            if include_secrets and credential:
                console.print("[yellow]  ⚠️  Secrets exposed in output - do not commit![/yellow]")
            else:
                console.print("[dim]  Secrets protected (use --secrets to expose)[/dim]")
            console.print()

            # Display rendered content with syntax highlighting
            language = {
                "shell": "bash",
                "dotenv": "sh",
                "json": "json",
                "toml": "toml",
            }[snippet.format]
            syntax = Syntax(snippet.content, language, theme="monokai", line_numbers=False)
            console.print(syntax)

        except RenderingError as e:
            console.print(f"[red]Rendering error: {e}[/red]")
            raise typer.Exit(1) from None

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from e


@app.command("validate")
def validate_profile(
    profile_name: str = typer.Option(..., "--profile", "-p", help="Harness profile name"),
    configs_dir: Path = typer.Option(
        Path("configs"),
        "--config-dir",
        help="Configuration directory",
    ),
) -> None:
    """Validate a harness profile configuration.

    Checks:
    - Required environment variable names are present
    - Template syntax in extra_env is valid
    - No duplicate environment variable names

    Example:
        benchmark render validate --profile claude-code
    """
    try:
        # Load configuration
        loader = ConfigLoader(configs_dir=configs_dir)
        profile_config = loader.load_harness_profile(profile_name)

        if profile_config is None:
            console.print(f"[red]Error: Harness profile '{profile_name}' not found[/red]")
            raise typer.Exit(1)

        profile = HarnessProfile(**profile_config)

        # Validate profile
        service = EnvRenderingService()
        warnings = service.validate_profile(profile)

        # Display results
        console.print(f"[bold green]✓ Profile '{profile_name}' is valid[/bold green]")
        console.print(f"  Protocol: {profile.protocol_surface}")
        console.print(f"  Format: {profile.render_format}")
        console.print(f"  Base URL env: {profile.base_url_env}")
        console.print(f"  API key env: {profile.api_key_env}")
        console.print(f"  Model env: {profile.model_env}")
        if profile.extra_env:
            console.print(f"  Extra env vars: {', '.join(profile.extra_env.keys())}")

        if warnings:
            console.print()
            console.print("[yellow]Warnings:[/yellow]")
            for warning in warnings:
                console.print(f"  ⚠️  {warning}")

    except ProfileValidationError as e:
        console.print(f"[red]✗ Validation failed: {e}[/red]")
        raise typer.Exit(1) from None
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from e


@app.command("list-profiles")
def list_profiles(
    configs_dir: Path = typer.Option(
        Path("configs"),
        "--config-dir",
        help="Configuration directory",
    ),
) -> None:
    """List available harness profiles.

    Example:
        benchmark render list-profiles
    """
    try:
        loader = ConfigLoader(configs_dir=configs_dir)
        profiles = loader.list_harness_profiles()

        if not profiles:
            console.print("[yellow]No harness profiles found[/yellow]")
            console.print(f"[dim]Looking in: {configs_dir / 'harnesses' / '*.yaml'}[/dim]")
            return

        console.print(f"[bold blue]Harness Profiles ({len(profiles)}):[/bold blue]")
        console.print()

        for profile_name in sorted(profiles):
            profile_config = loader.load_harness_profile(profile_name)
            if profile_config:
                profile = HarnessProfile(**profile_config)
                console.print(f"  [green]{profile.name}[/green]")
                console.print(f"    Protocol: {profile.protocol_surface}")
                console.print(f"    Format: {profile.render_format}")
                console.print(
                    f"    Env vars: {profile.base_url_env}, {profile.api_key_env}, {profile.model_env}"
                )
                if profile.extra_env:
                    console.print(f"    Extra: {', '.join(profile.extra_env.keys())}")
                console.print()

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from e


@app.command("check-compatibility")
def check_compatibility(
    variant_name: str = typer.Option(..., "--variant", "-v", help="Variant name"),
    configs_dir: Path = typer.Option(
        Path("configs"),
        "--config-dir",
        help="Configuration directory",
    ),
) -> None:
    """Check compatibility between a variant and its harness profile.

    Example:
        benchmark render check-compatibility --variant fireworks-glm-5-claude-code
    """
    try:
        loader = ConfigLoader(configs_dir=configs_dir)

        # Load variant
        variant_config = loader.load_variant(variant_name)
        if variant_config is None:
            console.print(f"[red]Error: Variant '{variant_name}' not found[/red]")
            raise typer.Exit(1)

        variant = Variant(**variant_config)

        # Load harness profile
        profile_config = loader.load_harness_profile(variant.harness_profile)
        if profile_config is None:
            console.print(
                f"[red]Error: Harness profile '{variant.harness_profile}' not found[/red]"
            )
            raise typer.Exit(1)

        profile = HarnessProfile(**profile_config)

        # Check compatibility
        service = EnvRenderingService()
        errors = service.validate_variant_profile_compatibility(variant, profile)

        # Display results
        console.print(f"[bold]Variant: {variant_name}[/bold]")
        console.print(f"  Provider: {variant.provider}")
        console.print(f"  Model: {variant.model_alias}")
        console.print(f"  Profile: {variant.harness_profile}")
        console.print()

        if errors:
            console.print("[yellow]Compatibility Issues:[/yellow]")
            for error in errors:
                console.print(f"  ✗ {error}")
            console.print()
            console.print(
                "[yellow]Recommendation: Fix variant configuration or use a compatible profile[/yellow]"
            )
            raise typer.Exit(1)
        else:
            console.print("[green]✓ Variant and profile are compatible[/green]")
            if variant.harness_env_overrides:
                console.print(f"  Overrides: {len(variant.harness_env_overrides)}")
                for key, value in sorted(variant.harness_env_overrides.items()):
                    console.print(f"    - {key}={value}")

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from e
