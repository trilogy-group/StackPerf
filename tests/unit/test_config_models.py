"""Unit tests for config models and validation."""

import pytest
from pydantic import ValidationError

from benchmark_core.config import (
    ExperimentConfig,
    HarnessProfileConfig,
    ProviderConfig,
    TaskCardConfig,
    VariantConfig,
)
from benchmark_core.config.providers import ModelAlias, ProtocolSurface


class TestProviderConfig:
    """Tests for ProviderConfig validation."""

    def test_valid_provider_config(self) -> None:
        """A valid provider config passes validation."""
        config = ProviderConfig(
            name="test-provider",
            route_name="test-route",
            protocol_surface=ProtocolSurface.ANTHROPIC_MESSAGES,
            upstream_base_url_env="TEST_BASE_URL",
            api_key_env="TEST_API_KEY",
            models=[
                ModelAlias(alias="model-a", upstream_model="upstream/model-a"),
            ],
        )
        assert config.name == "test-provider"
        assert config.protocol_surface == ProtocolSurface.ANTHROPIC_MESSAGES

    def test_duplicate_model_aliases_rejected(self) -> None:
        """Model aliases must be unique within a provider."""
        with pytest.raises(ValidationError, match="unique"):
            ProviderConfig(
                name="test-provider",
                route_name="test-route",
                protocol_surface=ProtocolSurface.ANTHROPIC_MESSAGES,
                upstream_base_url_env="TEST_BASE_URL",
                api_key_env="TEST_API_KEY",
                models=[
                    ModelAlias(alias="dupe", upstream_model="upstream/model-a"),
                    ModelAlias(alias="dupe", upstream_model="upstream/model-b"),
                ],
            )

    def test_empty_models_rejected(self) -> None:
        """Provider must have at least one model."""
        with pytest.raises(ValidationError):
            ProviderConfig(
                name="test-provider",
                route_name="test-route",
                protocol_surface=ProtocolSurface.ANTHROPIC_MESSAGES,
                upstream_base_url_env="TEST_BASE_URL",
                api_key_env="TEST_API_KEY",
                models=[],
            )

    def test_invalid_name_rejected(self) -> None:
        """Name must follow kebab-case pattern."""
        with pytest.raises(ValidationError):
            ProviderConfig(
                name="Invalid Name!",
                route_name="test-route",
                protocol_surface=ProtocolSurface.ANTHROPIC_MESSAGES,
                upstream_base_url_env="TEST_BASE_URL",
                api_key_env="TEST_API_KEY",
                models=[
                    ModelAlias(alias="model-a", upstream_model="upstream/model-a"),
                ],
            )


class TestHarnessProfileConfig:
    """Tests for HarnessProfileConfig validation."""

    def test_valid_harness_profile(self) -> None:
        """A valid harness profile passes validation."""
        config = HarnessProfileConfig(
            name="test-harness",
            protocol_surface=ProtocolSurface.ANTHROPIC_MESSAGES,
            base_url_env="TEST_BASE_URL",
            api_key_env="TEST_API_KEY",
            model_env="TEST_MODEL",
        )
        assert config.name == "test-harness"


class TestVariantConfig:
    """Tests for VariantConfig validation."""

    def test_valid_variant(self) -> None:
        """A valid variant passes validation."""
        config = VariantConfig(
            name="test-variant",
            provider="test-provider",
            provider_route="test-route",
            model_alias="model-a",
            harness_profile="test-harness",
            benchmark_tags={
                "provider": "test",
                "model": "model-a",
                "harness": "test-harness",
            },
        )
        assert config.name == "test-variant"

    def test_missing_benchmark_tags_rejected(self) -> None:
        """Variant must have required benchmark tags."""
        with pytest.raises(ValidationError, match="Missing required benchmark tags"):
            VariantConfig(
                name="test-variant",
                provider="test-provider",
                provider_route="test-route",
                model_alias="model-a",
                harness_profile="test-harness",
                benchmark_tags={"provider": "test"},  # Missing model and harness
            )


class TestExperimentConfig:
    """Tests for ExperimentConfig validation."""

    def test_valid_experiment(self) -> None:
        """A valid experiment passes validation."""
        config = ExperimentConfig(
            name="test-experiment",
            variants=["variant-a", "variant-b"],
        )
        assert config.name == "test-experiment"

    def test_duplicate_variants_rejected(self) -> None:
        """Variants must be unique within an experiment."""
        with pytest.raises(ValidationError, match="unique"):
            ExperimentConfig(
                name="test-experiment",
                variants=["variant-a", "variant-a"],
            )

    def test_empty_variants_rejected(self) -> None:
        """Experiment must have at least one variant."""
        with pytest.raises(ValidationError):
            ExperimentConfig(
                name="test-experiment",
                variants=[],
            )


class TestTaskCardConfig:
    """Tests for TaskCardConfig validation."""

    def test_valid_task_card(self) -> None:
        """A valid task card passes validation."""
        config = TaskCardConfig(
            name="test-task",
            goal="Test goal",
            starting_prompt="Test prompt",
            stop_condition="Test condition",
        )
        assert config.name == "test-task"

    def test_missing_stop_condition_rejected(self) -> None:
        """Task card must have a stop condition."""
        with pytest.raises(ValidationError):
            TaskCardConfig(
                name="test-task",
                goal="Test goal",
                starting_prompt="Test prompt",
                stop_condition="",  # Empty
            )
