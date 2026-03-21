"""Unit tests for YAML config file validation."""

from pathlib import Path

import pytest
import yaml

from benchmark_core.config import (
    ExperimentConfig,
    HarnessProfileConfig,
    ProviderConfig,
    TaskCardConfig,
    VariantConfig,
)


@pytest.fixture
def configs_dir() -> Path:
    """Path to the configs directory."""
    return Path(__file__).parent.parent.parent / "configs"


class TestYAMLConfigLoading:
    """Tests for loading YAML config files."""

    def test_provider_yaml_valid(self, configs_dir: Path) -> None:
        """Provider YAML files should be valid."""
        providers_dir = configs_dir / "providers"
        if not providers_dir.exists():
            pytest.skip("No providers config directory")

        for yaml_file in providers_dir.glob("*.yaml"):
            content = yaml.safe_load(yaml_file.read_text())
            # Should not raise validation error
            config = ProviderConfig.model_validate(content)
            assert config is not None

    def test_harness_yaml_valid(self, configs_dir: Path) -> None:
        """Harness YAML files should be valid."""
        harnesses_dir = configs_dir / "harnesses"
        if not harnesses_dir.exists():
            pytest.skip("No harnesses config directory")

        for yaml_file in harnesses_dir.glob("*.yaml"):
            content = yaml.safe_load(yaml_file.read_text())
            config = HarnessProfileConfig.model_validate(content)
            assert config is not None

    def test_variant_yaml_valid(self, configs_dir: Path) -> None:
        """Variant YAML files should be valid."""
        variants_dir = configs_dir / "variants"
        if not variants_dir.exists():
            pytest.skip("No variants config directory")

        for yaml_file in variants_dir.glob("*.yaml"):
            content = yaml.safe_load(yaml_file.read_text())
            config = VariantConfig.model_validate(content)
            assert config is not None

    def test_experiment_yaml_valid(self, configs_dir: Path) -> None:
        """Experiment YAML files should be valid."""
        experiments_dir = configs_dir / "experiments"
        if not experiments_dir.exists():
            pytest.skip("No experiments config directory")

        for yaml_file in experiments_dir.glob("*.yaml"):
            content = yaml.safe_load(yaml_file.read_text())
            config = ExperimentConfig.model_validate(content)
            assert config is not None

    def test_task_card_yaml_valid(self, configs_dir: Path) -> None:
        """TaskCard YAML files should be valid."""
        task_cards_dir = configs_dir / "task-cards"
        if not task_cards_dir.exists():
            pytest.skip("No task-cards config directory")

        for yaml_file in task_cards_dir.glob("*.yaml"):
            content = yaml.safe_load(yaml_file.read_text())
            config = TaskCardConfig.model_validate(content)
            assert config is not None
