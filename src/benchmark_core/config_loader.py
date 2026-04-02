"""Config loader with YAML loading, validation, and deterministic precedence rules."""

from pathlib import Path

import yaml

from benchmark_core.config import (
    Experiment,
    HarnessProfile,
    ProviderConfig,
    ProviderModel,
    RoutingDefaults,
    TaskCard,
    Variant,
)

# Default config paths
DEFAULT_CONFIGS_DIR = Path("configs")


class ConfigValidationError(Exception):
    """Raised when config validation fails with precise field-level errors."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("\n".join(errors))


class ConfigRegistry:
    """Registry for loaded configs with cross-reference validation."""

    def __init__(self) -> None:
        self.providers: dict[str, ProviderConfig] = {}
        self.harness_profiles: dict[str, HarnessProfile] = {}
        self.variants: dict[str, Variant] = {}
        self.experiments: dict[str, Experiment] = {}
        self.task_cards: dict[str, TaskCard] = {}

    def _validate_no_duplicates(self, name: str, config_type: str, existing: dict) -> None:
        """Validate no duplicate names within the same config type."""
        if name in existing:
            raise ConfigValidationError([f"Duplicate {config_type} name: '{name}' already exists"])

    def register_provider(self, config: ProviderConfig) -> None:
        """Register a provider config."""
        self._validate_no_duplicates(config.name, "provider", self.providers)
        self.providers[config.name] = config

    def register_harness_profile(self, config: HarnessProfile) -> None:
        """Register a harness profile."""
        self._validate_no_duplicates(config.name, "harness profile", self.harness_profiles)
        self.harness_profiles[config.name] = config

    def register_variant(self, config: Variant) -> None:
        """Register a variant config."""
        self._validate_no_duplicates(config.name, "variant", self.variants)
        self.variants[config.name] = config

    def register_experiment(self, config: Experiment) -> None:
        """Register an experiment config."""
        self._validate_no_duplicates(config.name, "experiment", self.experiments)
        self.experiments[config.name] = config

    def register_task_card(self, config: TaskCard) -> None:
        """Register a task card."""
        self._validate_no_duplicates(config.name, "task card", self.task_cards)
        self.task_cards[config.name] = config

    def validate_references(self) -> list[str]:
        """Validate all cross-references between configs.

        Returns:
            List of validation error messages (empty if all valid).
        """
        errors: list[str] = []

        # Validate variant references
        for variant_name, variant in self.variants.items():
            # Check provider reference
            if variant.provider not in self.providers:
                errors.append(
                    f"Variant '{variant_name}': referenced provider '{variant.provider}' not found"
                )
            else:
                # Check model_alias exists in provider
                provider = self.providers[variant.provider]
                alias_names = [m.alias for m in provider.models]
                if variant.model_alias not in alias_names:
                    errors.append(
                        f"Variant '{variant_name}': model alias "
                        f"'{variant.model_alias}' not found in provider "
                        f"'{variant.provider}' (available: {alias_names})"
                    )

            # Check harness profile reference
            if variant.harness_profile not in self.harness_profiles:
                errors.append(
                    f"Variant '{variant_name}': referenced harness profile "
                    f"'{variant.harness_profile}' not found"
                )
            else:
                # Check protocol surface compatibility
                variant_provider = self.providers.get(variant.provider)
                harness = self.harness_profiles.get(variant.harness_profile)
                if (
                    variant_provider
                    and harness
                    and variant_provider.protocol_surface != harness.protocol_surface
                ):
                    errors.append(
                        f"Variant '{variant_name}': protocol surface mismatch "
                        f"(provider '{variant.provider}': "
                        f"{variant_provider.protocol_surface}, "
                        f"harness '{variant.harness_profile}': "
                        f"{harness.protocol_surface})"
                    )

        # Validate experiment references
        for exp_name, experiment in self.experiments.items():
            for variant_name in experiment.variants:
                if variant_name not in self.variants:
                    errors.append(
                        f"Experiment '{exp_name}': referenced variant '{variant_name}' not found"
                    )

        return errors

    def validate_all(self) -> None:
        """Run all validations and raise if errors found."""
        errors = self.validate_references()
        if errors:
            raise ConfigValidationError(errors)


class ConfigLoader:
    """Load and validate configs from YAML files."""

    def __init__(self, configs_dir: Path | str | None = None) -> None:
        """Initialize config loader.

        Args:
            configs_dir: Base directory for configs. Defaults to 'configs'.
        """
        self.configs_dir = Path(configs_dir) if configs_dir else DEFAULT_CONFIGS_DIR
        self.registry = ConfigRegistry()

    def _load_yaml_file(self, path: Path) -> dict:
        """Load and parse a YAML file."""
        with open(path) as f:
            return yaml.safe_load(f) or {}

    def _resolve_path(self, subdir: str) -> Path:
        """Resolve path to a config subdirectory."""
        return self.configs_dir / subdir

    def load_providers(self) -> dict[str, ProviderConfig]:
        """Load all provider configs from configs/providers/*.yaml."""
        providers_dir = self._resolve_path("providers")
        if not providers_dir.exists():
            return {}

        for yaml_file in sorted(providers_dir.glob("*.yaml")):
            data = self._load_yaml_file(yaml_file)
            if not data:
                continue

            # Transform models list
            models_data = data.pop("models", [])
            models = [ProviderModel(**m) for m in models_data]

            # Transform routing_defaults
            routing_data = data.pop("routing_defaults", {})
            routing_defaults = RoutingDefaults(**routing_data)

            config = ProviderConfig(**data, models=models, routing_defaults=routing_defaults)
            self.registry.register_provider(config)

        return self.registry.providers

    def load_harness_profiles(self) -> dict[str, HarnessProfile]:
        """Load all harness profiles from configs/harnesses/*.yaml."""
        harnesses_dir = self._resolve_path("harnesses")
        if not harnesses_dir.exists():
            return {}

        for yaml_file in sorted(harnesses_dir.glob("*.yaml")):
            data = self._load_yaml_file(yaml_file)
            if not data:
                continue

            config = HarnessProfile(**data)
            self.registry.register_harness_profile(config)

        return self.registry.harness_profiles

    def load_harness_profile(self, name: str) -> dict | None:
        """Load a single harness profile by name.

        Args:
            name: Harness profile name.

        Returns:
            Raw config dict if found, None otherwise.
        """
        profile_path = self._resolve_path("harnesses") / f"{name}.yaml"
        if not profile_path.exists():
            return None
        return self._load_yaml_file(profile_path)

    def list_harness_profiles(self) -> list[str]:
        """List all available harness profile names.

        Returns:
            List of profile names (without .yaml extension).
        """
        harnesses_dir = self._resolve_path("harnesses")
        if not harnesses_dir.exists():
            return []
        return [f.stem for f in sorted(harnesses_dir.glob("*.yaml"))]

    def load_variants(self) -> dict[str, Variant]:
        """Load all variant configs from configs/variants/*.yaml."""
        variants_dir = self._resolve_path("variants")
        if not variants_dir.exists():
            return {}

        for yaml_file in sorted(variants_dir.glob("*.yaml")):
            data = self._load_yaml_file(yaml_file)
            if not data:
                continue

            config = Variant(**data)
            self.registry.register_variant(config)

        return self.registry.variants

    def load_variant(self, name: str) -> dict | None:
        """Load a single variant by name.

        Args:
            name: Variant name.

        Returns:
            Raw config dict if found, None otherwise.
        """
        variant_path = self._resolve_path("variants") / f"{name}.yaml"
        if not variant_path.exists():
            return None
        return self._load_yaml_file(variant_path)

    def list_variants(self) -> list[str]:
        """List all available variant names.

        Returns:
            List of variant names (without .yaml extension).
        """
        variants_dir = self._resolve_path("variants")
        if not variants_dir.exists():
            return []
        return [f.stem for f in sorted(variants_dir.glob("*.yaml"))]

    def load_experiments(self) -> dict[str, Experiment]:
        """Load all experiment configs from configs/experiments/*.yaml."""
        experiments_dir = self._resolve_path("experiments")
        if not experiments_dir.exists():
            return {}

        for yaml_file in sorted(experiments_dir.glob("*.yaml")):
            data = self._load_yaml_file(yaml_file)
            if not data:
                continue

            config = Experiment(**data)
            self.registry.register_experiment(config)

        return self.registry.experiments

    def load_task_cards(self) -> dict[str, TaskCard]:
        """Load all task cards from configs/task-cards/*.yaml."""
        task_cards_dir = self._resolve_path("task-cards")
        if not task_cards_dir.exists():
            return {}

        for yaml_file in sorted(task_cards_dir.glob("*.yaml")):
            data = self._load_yaml_file(yaml_file)
            if not data:
                continue

            config = TaskCard(**data)
            self.registry.register_task_card(config)

        return self.registry.task_cards

    def load_all(self) -> ConfigRegistry:
        """Load all config types and validate.

        Loads in dependency order: providers, harnesses, variants,
        experiments, task-cards.

        Returns:
            ConfigRegistry with all loaded and validated configs.

        Raises:
            ConfigValidationError: If validation fails.
        """
        # Load in dependency order
        self.load_providers()
        self.load_harness_profiles()
        self.load_variants()
        self.load_experiments()
        self.load_task_cards()

        # Validate cross-references
        self.registry.validate_all()

        return self.registry


def load_all_configs(configs_dir: Path | str | None = None) -> ConfigRegistry:
    """Convenience function to load all configs.

    Args:
        configs_dir: Base directory for configs. Defaults to 'configs'.

    Returns:
        ConfigRegistry with all loaded and validated configs.

    Raises:
        ConfigValidationError: If validation fails.
    """
    loader = ConfigLoader(configs_dir)
    return loader.load_all()
