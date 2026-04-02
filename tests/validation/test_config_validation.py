"""Config validation smoke tests for CI.

Validates all YAML config files against their typed Pydantic schemas.
This ensures config regressions are caught automatically.
"""

from pathlib import Path

import pytest
import yaml

from benchmark_core.config import (
    Experiment,
    HarnessProfile,
    ProviderConfig,
    TaskCard,
    Variant,
)
from benchmark_core.config_loader import ConfigLoader

# Config directories
CONFIG_ROOT = Path(__file__).parent.parent.parent / "configs"
PROVIDERS_DIR = CONFIG_ROOT / "providers"
HARNESSES_DIR = CONFIG_ROOT / "harnesses"
VARIANTS_DIR = CONFIG_ROOT / "variants"
EXPERIMENTS_DIR = CONFIG_ROOT / "experiments"
TASK_CARDS_DIR = CONFIG_ROOT / "task-cards"


class TestProviderConfigs:
    """Validate all provider config files."""

    @pytest.fixture
    def provider_files(self) -> list[Path]:
        """Get all provider config files."""
        if not PROVIDERS_DIR.exists():
            return []
        return list(PROVIDERS_DIR.glob("*.yaml"))

    def test_providers_directory_exists(self) -> None:
        """Verify providers config directory exists."""
        assert PROVIDERS_DIR.exists(), f"Providers config directory not found: {PROVIDERS_DIR}"

    def test_all_provider_configs_valid(self, provider_files: list[Path]) -> None:
        """Validate all provider config files parse and validate correctly."""
        if not provider_files:
            pytest.skip("No provider config files found")

        for config_file in provider_files:
            with open(config_file) as f:
                data = yaml.safe_load(f)

            # Validate against schema
            try:
                ProviderConfig(**data)
            except Exception as e:
                pytest.fail(f"Provider config {config_file.name} failed validation: {e}")


class TestHarnessProfiles:
    """Validate all harness profile config files."""

    @pytest.fixture
    def harness_files(self) -> list[Path]:
        """Get all harness profile config files."""
        if not HARNESSES_DIR.exists():
            return []
        return list(HARNESSES_DIR.glob("*.yaml"))

    def test_harnesses_directory_exists(self) -> None:
        """Verify harnesses config directory exists."""
        assert HARNESSES_DIR.exists(), f"Harnesses config directory not found: {HARNESSES_DIR}"

    def test_all_harness_configs_valid(self, harness_files: list[Path]) -> None:
        """Validate all harness profile config files parse and validate correctly."""
        if not harness_files:
            pytest.skip("No harness config files found")

        for config_file in harness_files:
            with open(config_file) as f:
                data = yaml.safe_load(f)

            # Validate against schema
            try:
                HarnessProfile(**data)
            except Exception as e:
                pytest.fail(f"Harness profile {config_file.name} failed validation: {e}")


class TestVariantConfigs:
    """Validate all variant config files."""

    @pytest.fixture
    def variant_files(self) -> list[Path]:
        """Get all variant config files."""
        if not VARIANTS_DIR.exists():
            return []
        return list(VARIANTS_DIR.glob("*.yaml"))

    def test_variants_directory_exists(self) -> None:
        """Verify variants config directory exists."""
        assert VARIANTS_DIR.exists(), f"Variants config directory not found: {VARIANTS_DIR}"

    def test_all_variant_configs_valid(self, variant_files: list[Path]) -> None:
        """Validate all variant config files parse and validate correctly."""
        if not variant_files:
            pytest.skip("No variant config files found")

        for config_file in variant_files:
            with open(config_file) as f:
                data = yaml.safe_load(f)

            # Validate against schema
            try:
                Variant(**data)
            except Exception as e:
                pytest.fail(f"Variant config {config_file.name} failed validation: {e}")


class TestExperimentConfigs:
    """Validate all experiment config files."""

    @pytest.fixture
    def experiment_files(self) -> list[Path]:
        """Get all experiment config files."""
        if not EXPERIMENTS_DIR.exists():
            return []
        return list(EXPERIMENTS_DIR.glob("*.yaml"))

    def test_experiments_directory_exists(self) -> None:
        """Verify experiments config directory exists."""
        assert EXPERIMENTS_DIR.exists(), (
            f"Experiments config directory not found: {EXPERIMENTS_DIR}"
        )

    def test_all_experiment_configs_valid(self, experiment_files: list[Path]) -> None:
        """Validate all experiment config files parse and validate correctly."""
        if not experiment_files:
            pytest.skip("No experiment config files found")

        for config_file in experiment_files:
            with open(config_file) as f:
                data = yaml.safe_load(f)

            # Validate against schema
            try:
                Experiment(**data)
            except Exception as e:
                pytest.fail(f"Experiment config {config_file.name} failed validation: {e}")


class TestTaskCardConfigs:
    """Validate all task card config files."""

    @pytest.fixture
    def task_card_files(self) -> list[Path]:
        """Get all task card config files."""
        if not TASK_CARDS_DIR.exists():
            return []
        return list(TASK_CARDS_DIR.glob("*.yaml"))

    def test_task_cards_directory_exists(self) -> None:
        """Verify task cards config directory exists."""
        assert TASK_CARDS_DIR.exists(), f"Task cards config directory not found: {TASK_CARDS_DIR}"

    def test_all_task_card_configs_valid(self, task_card_files: list[Path]) -> None:
        """Validate all task card config files parse and validate correctly."""
        if not task_card_files:
            pytest.skip("No task card config files found")

        for config_file in task_card_files:
            with open(config_file) as f:
                data = yaml.safe_load(f)

            # Validate against schema
            try:
                TaskCard(**data)
            except Exception as e:
                pytest.fail(f"Task card config {config_file.name} failed validation: {e}")


class TestConfigLoaderIntegration:
    """Test ConfigLoader can load all configs."""

    def test_config_loader_providers(self) -> None:
        """Test loading all provider configs."""
        loader = ConfigLoader(PROVIDERS_DIR.parent)
        if PROVIDERS_DIR.exists():
            providers = loader.load_providers()
            assert isinstance(providers, dict)
            # Should have loaded at least one provider if files exist
            if list(PROVIDERS_DIR.glob("*.yaml")):
                assert len(providers) > 0, "No providers loaded from config directory"

    def test_config_loader_harness_profiles(self) -> None:
        """Test loading all harness profile configs."""
        loader = ConfigLoader(HARNESSES_DIR.parent)
        if HARNESSES_DIR.exists():
            profiles = loader.load_harness_profiles()
            assert isinstance(profiles, dict)
            # Should have loaded at least one profile if files exist
            if list(HARNESSES_DIR.glob("*.yaml")):
                assert len(profiles) > 0, "No harness profiles loaded from config directory"

    def test_config_loader_variants(self) -> None:
        """Test loading all variant configs."""
        loader = ConfigLoader(VARIANTS_DIR.parent)
        if VARIANTS_DIR.exists():
            variants = loader.load_variants()
            assert isinstance(variants, dict)
            # Should have loaded at least one variant if files exist
            if list(VARIANTS_DIR.glob("*.yaml")):
                assert len(variants) > 0, "No variants loaded from config directory"
