"""Tests for typed config schemas and validation."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from benchmark_core.config import (
    Experiment,
    HarnessProfile,
    ProviderConfig,
    ProviderModel,
    RoutingDefaults,
    TaskCard,
    Variant,
)
from benchmark_core.config_loader import ConfigLoader, ConfigRegistry, ConfigValidationError

# Get configs directory relative to test file
TESTS_DIR = Path(__file__).parent.parent.parent
CONFIGS_DIR = TESTS_DIR / "configs"


class TestProviderModel:
    """Tests for ProviderModel."""

    def test_valid_provider_model(self) -> None:
        """Test creating a valid ProviderModel."""
        model = ProviderModel(alias="kimi-k2-5", upstream_model="accounts/fireworks/models/kimi-k2p5")
        assert model.alias == "kimi-k2-5"
        assert model.upstream_model == "accounts/fireworks/models/kimi-k2p5"


class TestRoutingDefaults:
    """Tests for RoutingDefaults."""

    def test_valid_routing_defaults(self) -> None:
        """Test creating valid RoutingDefaults."""
        defaults = RoutingDefaults(
            timeout_seconds=180,
            extra_headers={"x-session-affinity": "{{ session_affinity_key }}"}
        )
        assert defaults.timeout_seconds == 180
        assert defaults.extra_headers["x-session-affinity"] == "{{ session_affinity_key }}"

    def test_empty_routing_defaults(self) -> None:
        """Test creating empty RoutingDefaults."""
        defaults = RoutingDefaults()
        assert defaults.timeout_seconds is None
        assert defaults.extra_headers == {}


class TestProviderConfig:
    """Tests for ProviderConfig."""

    def test_valid_provider_config(self) -> None:
        """Test creating a valid ProviderConfig."""
        config = ProviderConfig(
            name="fireworks",
            route_name="fireworks-main",
            protocol_surface="anthropic_messages",
            upstream_base_url_env="FIREWORKS_BASE_URL",
            api_key_env="FIREWORKS_API_KEY",
            models=[
                ProviderModel(alias="kimi-k2-5", upstream_model="accounts/fireworks/models/kimi-k2p5")
            ],
            routing_defaults=RoutingDefaults(timeout_seconds=180)
        )
        assert config.name == "fireworks"
        assert config.protocol_surface == "anthropic_messages"
        assert config.models[0].alias == "kimi-k2-5"

    def test_provider_config_empty_name(self) -> None:
        """Test that empty name raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ProviderConfig(
                name="",
                protocol_surface="anthropic_messages",
                upstream_base_url_env="FIREWORKS_BASE_URL",
                api_key_env="FIREWORKS_API_KEY"
            )
        assert "must not be empty or whitespace" in str(exc_info.value)

    def test_provider_config_whitespace_name(self) -> None:
        """Test that whitespace-only name raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ProviderConfig(
                name="   ",
                protocol_surface="anthropic_messages",
                upstream_base_url_env="FIREWORKS_BASE_URL",
                api_key_env="FIREWORKS_API_KEY"
            )
        assert "must not be empty or whitespace" in str(exc_info.value)

    def test_provider_config_duplicate_aliases(self) -> None:
        """Test that duplicate model aliases raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ProviderConfig(
                name="fireworks",
                protocol_surface="anthropic_messages",
                upstream_base_url_env="FIREWORKS_BASE_URL",
                api_key_env="FIREWORKS_API_KEY",
                models=[
                    ProviderModel(alias="kimi-k2-5", upstream_model="model1"),
                    ProviderModel(alias="kimi-k2-5", upstream_model="model2")
                ]
            )
        assert "duplicate model aliases found" in str(exc_info.value)

    def test_provider_config_invalid_protocol(self) -> None:
        """Test that invalid protocol surface raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ProviderConfig(
                name="fireworks",
                protocol_surface="invalid_protocol",  # type: ignore
                upstream_base_url_env="FIREWORKS_BASE_URL",
                api_key_env="FIREWORKS_API_KEY"
            )
        assert "anthropic_messages" in str(exc_info.value) or "openai_responses" in str(exc_info.value)


class TestHarnessProfile:
    """Tests for HarnessProfile."""

    def test_valid_harness_profile_anthropic(self) -> None:
        """Test creating a valid Anthropic-surface harness profile."""
        profile = HarnessProfile(
            name="claude-code",
            protocol_surface="anthropic_messages",
            base_url_env="ANTHROPIC_BASE_URL",
            api_key_env="ANTHROPIC_API_KEY",
            model_env="ANTHROPIC_MODEL",
            extra_env={
                "ANTHROPIC_DEFAULT_SONNET_MODEL": "{{ model_alias }}"
            },
            render_format="shell",
            launch_checks=["base URL points to local LiteLLM"]
        )
        assert profile.name == "claude-code"
        assert profile.protocol_surface == "anthropic_messages"
        assert profile.extra_env["ANTHROPIC_DEFAULT_SONNET_MODEL"] == "{{ model_alias }}"

    def test_valid_harness_profile_openai(self) -> None:
        """Test creating a valid OpenAI-surface harness profile."""
        profile = HarnessProfile(
            name="openai-cli",
            protocol_surface="openai_responses",
            base_url_env="OPENAI_BASE_URL",
            api_key_env="OPENAI_API_KEY",
            model_env="OPENAI_MODEL",
            extra_env={},
            render_format="shell",
            launch_checks=["base URL points to local LiteLLM"]
        )
        assert profile.name == "openai-cli"
        assert profile.protocol_surface == "openai_responses"

    def test_harness_profile_empty_name(self) -> None:
        """Test that empty name raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            HarnessProfile(
                name="",
                protocol_surface="anthropic_messages",
                base_url_env="ANTHROPIC_BASE_URL",
                api_key_env="ANTHROPIC_API_KEY",
                model_env="ANTHROPIC_MODEL"
            )
        assert "must not be empty or whitespace" in str(exc_info.value)


class TestVariant:
    """Tests for Variant."""

    def test_valid_variant(self) -> None:
        """Test creating a valid Variant."""
        variant = Variant(
            name="fireworks-kimi-k2-5-claude-code",
            provider="fireworks",
            provider_route="fireworks-main",
            model_alias="kimi-k2-5",
            harness_profile="claude-code",
            harness_env_overrides={"CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS": "1"},
            benchmark_tags={
                "harness": "claude-code",
                "provider": "fireworks",
                "model": "kimi-k2-5"
            }
        )
        assert variant.name == "fireworks-kimi-k2-5-claude-code"
        assert variant.provider == "fireworks"
        assert variant.model_alias == "kimi-k2-5"

    def test_variant_missing_benchmark_tags(self) -> None:
        """Test that missing required benchmark tags raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Variant(
                name="test-variant",
                provider="fireworks",
                model_alias="kimi-k2-5",
                harness_profile="claude-code",
                benchmark_tags={"harness": "claude-code"}  # Missing provider and model
            )
        assert "benchmark_tags must include" in str(exc_info.value)
        assert "provider" in str(exc_info.value)
        assert "model" in str(exc_info.value)

    def test_variant_empty_name(self) -> None:
        """Test that empty name raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Variant(
                name="",
                provider="fireworks",
                model_alias="kimi-k2-5",
                harness_profile="claude-code",
                benchmark_tags={
                    "harness": "claude-code",
                    "provider": "fireworks",
                    "model": "kimi-k2-5"
                }
            )
        assert "must not be empty or whitespace" in str(exc_info.value)


class TestExperiment:
    """Tests for Experiment."""

    def test_valid_experiment(self) -> None:
        """Test creating a valid Experiment."""
        experiment = Experiment(
            name="fireworks-terminal-agents-comparison",
            description="Compare Fireworks models across harnesses",
            variants=[
                "fireworks-kimi-k2-5-claude-code",
                "fireworks-glm-5-claude-code"
            ]
        )
        assert experiment.name == "fireworks-terminal-agents-comparison"
        assert len(experiment.variants) == 2

    def test_experiment_duplicate_variants(self) -> None:
        """Test that duplicate variant names raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Experiment(
                name="test-experiment",
                variants=["variant-1", "variant-1"]
            )
        assert "duplicate variant names found" in str(exc_info.value)

    def test_experiment_empty_name(self) -> None:
        """Test that empty name raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Experiment(name="", variants=[])
        assert "must not be empty or whitespace" in str(exc_info.value)


class TestTaskCard:
    """Tests for TaskCard."""

    def test_valid_task_card(self) -> None:
        """Test creating a valid TaskCard."""
        task_card = TaskCard(
            name="repo-auth-analysis",
            repo_path="/path/to/repo",
            goal="identify auth flow, trust boundaries, and risky edge cases",
            starting_prompt="Analyze the authentication architecture in this repository.",
            stop_condition="produce a written summary with file references and identified risks",
            session_timebox_minutes=30,
            notes=["work from the current git commit only"]
        )
        assert task_card.name == "repo-auth-analysis"
        assert task_card.session_timebox_minutes == 30

    def test_task_card_empty_goal(self) -> None:
        """Test that empty goal raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            TaskCard(
                name="repo-auth-analysis",
                goal="",
                starting_prompt="Analyze the authentication architecture.",
                stop_condition="produce a written summary"
            )
        assert "must not be empty or whitespace" in str(exc_info.value)

    def test_task_card_empty_stop_condition(self) -> None:
        """Test that empty stop_condition raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            TaskCard(
                name="repo-auth-analysis",
                goal="Analyze auth",
                starting_prompt="Analyze the authentication architecture.",
                stop_condition=""
            )
        assert "must not be empty or whitespace" in str(exc_info.value)

    def test_task_card_invalid_timebox(self) -> None:
        """Test that invalid timebox raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            TaskCard(
                name="repo-auth-analysis",
                goal="Analyze auth",
                starting_prompt="Analyze.",
                stop_condition="produce summary",
                session_timebox_minutes=0
            )
        assert "session_timebox_minutes must be positive" in str(exc_info.value)


class TestConfigRegistry:
    """Tests for ConfigRegistry."""

    def test_register_duplicate_provider(self) -> None:
        """Test that duplicate provider registration raises error."""
        registry = ConfigRegistry()
        config = ProviderConfig(
            name="fireworks",
            protocol_surface="anthropic_messages",
            upstream_base_url_env="FIREWORKS_BASE_URL",
            api_key_env="FIREWORKS_API_KEY"
        )
        registry.register_provider(config)

        with pytest.raises(ConfigValidationError) as exc_info:
            registry.register_provider(config)
        assert "Duplicate provider name" in str(exc_info.value)

    def test_validate_missing_provider_reference(self) -> None:
        """Test validation catches missing provider reference."""
        registry = ConfigRegistry()
        registry.register_variant(Variant(
            name="test-variant",
            provider="nonexistent-provider",
            model_alias="kimi-k2-5",
            harness_profile="claude-code",
            benchmark_tags={
                "harness": "claude-code",
                "provider": "fireworks",
                "model": "kimi-k2-5"
            }
        ))

        errors = registry.validate_references()
        assert len(errors) == 2  # Missing provider + missing harness
        assert "referenced provider 'nonexistent-provider' not found" in errors[0]

    def test_validate_protocol_mismatch(self) -> None:
        """Test validation catches protocol surface mismatch."""
        registry = ConfigRegistry()

        # Register provider with anthropic_messages
        registry.register_provider(ProviderConfig(
            name="fireworks",
            protocol_surface="anthropic_messages",
            upstream_base_url_env="FIREWORKS_BASE_URL",
            api_key_env="FIREWORKS_API_KEY",
            models=[ProviderModel(alias="kimi-k2-5", upstream_model="model1")]
        ))

        # Register harness with openai_responses
        registry.register_harness_profile(HarnessProfile(
            name="openai-cli",
            protocol_surface="openai_responses",
            base_url_env="OPENAI_BASE_URL",
            api_key_env="OPENAI_API_KEY",
            model_env="OPENAI_MODEL"
        ))

        # Register variant combining them
        registry.register_variant(Variant(
            name="test-variant",
            provider="fireworks",
            model_alias="kimi-k2-5",
            harness_profile="openai-cli",
            benchmark_tags={
                "harness": "openai-cli",
                "provider": "fireworks",
                "model": "kimi-k2-5"
            }
        ))

        errors = registry.validate_references()
        assert len(errors) == 1
        assert "protocol surface mismatch" in errors[0]

    def test_validate_missing_model_alias(self) -> None:
        """Test validation catches missing model alias in provider."""
        registry = ConfigRegistry()

        registry.register_provider(ProviderConfig(
            name="fireworks",
            protocol_surface="anthropic_messages",
            upstream_base_url_env="FIREWORKS_BASE_URL",
            api_key_env="FIREWORKS_API_KEY",
            models=[ProviderModel(alias="kimi-k2-5", upstream_model="model1")]
        ))

        registry.register_harness_profile(HarnessProfile(
            name="claude-code",
            protocol_surface="anthropic_messages",
            base_url_env="ANTHROPIC_BASE_URL",
            api_key_env="ANTHROPIC_API_KEY",
            model_env="ANTHROPIC_MODEL"
        ))

        registry.register_variant(Variant(
            name="test-variant",
            provider="fireworks",
            model_alias="nonexistent-model",
            harness_profile="claude-code",
            benchmark_tags={
                "harness": "claude-code",
                "provider": "fireworks",
                "model": "nonexistent-model"
            }
        ))

        errors = registry.validate_references()
        assert len(errors) == 1
        assert "model alias 'nonexistent-model' not found" in errors[0]


class TestConfigLoader:
    """Tests for ConfigLoader."""

    def test_load_all_configs(self) -> None:
        """Test loading all config types from the configs directory."""
        loader = ConfigLoader(CONFIGS_DIR)
        registry = loader.load_all()

        # Verify providers loaded
        assert "fireworks" in registry.providers
        assert "openai" in registry.providers

        # Verify harnesses loaded
        assert "claude-code" in registry.harness_profiles
        assert "openai-cli" in registry.harness_profiles

        # Verify variants loaded
        assert "fireworks-kimi-k2-5-claude-code" in registry.variants
        assert "openai-gpt-4o-cli" in registry.variants

        # Verify experiments loaded
        assert "fireworks-terminal-agents-comparison" in registry.experiments

        # Verify task cards loaded
        assert "repo-auth-analysis" in registry.task_cards

    def test_provider_protocol_surface(self) -> None:
        """Test that provider protocol surfaces are loaded correctly."""
        loader = ConfigLoader(CONFIGS_DIR)
        registry = loader.load_all()

        # Fireworks uses anthropic_messages
        fireworks = registry.providers["fireworks"]
        assert fireworks.protocol_surface == "anthropic_messages"

        # OpenAI uses openai_responses
        openai = registry.providers["openai"]
        assert openai.protocol_surface == "openai_responses"

    def test_harness_protocol_surface(self) -> None:
        """Test that harness protocol surfaces are loaded correctly."""
        loader = ConfigLoader(CONFIGS_DIR)
        registry = loader.load_all()

        # Claude Code uses anthropic_messages
        claude = registry.harness_profiles["claude-code"]
        assert claude.protocol_surface == "anthropic_messages"

        # OpenAI CLI uses openai_responses
        openai_cli = registry.harness_profiles["openai-cli"]
        assert openai_cli.protocol_surface == "openai_responses"

    def test_valid_protocol_compatibility(self) -> None:
        """Test that valid protocol surface combinations pass validation."""
        loader = ConfigLoader(CONFIGS_DIR)
        registry = loader.load_all()

        # All configs should load without validation errors
        # Fireworks-Kimi-Claude: anthropic_messages + anthropic_messages ✓
        variant1 = registry.variants["fireworks-kimi-k2-5-claude-code"]
        assert variant1.provider == "fireworks"
        assert variant1.harness_profile == "claude-code"

        # OpenAI-GPT-4o-CLI: openai_responses + openai_responses ✓
        variant2 = registry.variants["openai-gpt-4o-cli"]
        assert variant2.provider == "openai"
        assert variant2.harness_profile == "openai-cli"


class TestFieldLevelErrors:
    """Tests for precise field-level error messages."""

    def test_provider_field_error_name(self) -> None:
        """Test that provider name errors are field-specific."""
        with pytest.raises(ValidationError) as exc_info:
            ProviderConfig(
                name="",  # Empty name
                protocol_surface="anthropic_messages",
                upstream_base_url_env="FIREWORKS_BASE_URL",
                api_key_env="FIREWORKS_API_KEY"
            )
        error_str = str(exc_info.value)
        assert "name" in error_str.lower()
        assert "must not be empty or whitespace" in error_str

    def test_provider_field_error_api_key_env(self) -> None:
        """Test that api_key_env errors are field-specific."""
        with pytest.raises(ValidationError) as exc_info:
            ProviderConfig(
                name="fireworks",
                protocol_surface="anthropic_messages",
                upstream_base_url_env="FIREWORKS_BASE_URL",
                api_key_env="   "  # Whitespace only
            )
        error_str = str(exc_info.value)
        assert "api_key_env" in error_str.lower()
        assert "must not be empty or whitespace" in error_str

    def test_variant_field_error_benchmark_tags(self) -> None:
        """Test that benchmark_tags errors list missing fields."""
        with pytest.raises(ValidationError) as exc_info:
            Variant(
                name="test-variant",
                provider="fireworks",
                model_alias="kimi-k2-5",
                harness_profile="claude-code",
                benchmark_tags={}  # Missing required tags
            )
        error_str = str(exc_info.value)
        assert "benchmark_tags" in error_str.lower() or "benchmark tags" in error_str.lower()
        assert "harness" in error_str
        assert "provider" in error_str
        assert "model" in error_str

    def test_task_card_field_error_timebox(self) -> None:
        """Test that timebox errors are field-specific."""
        with pytest.raises(ValidationError) as exc_info:
            TaskCard(
                name="test-task",
                goal="Test goal",
                starting_prompt="Test prompt",
                stop_condition="Test condition",
                session_timebox_minutes=-5  # Negative timebox
            )
        error_str = str(exc_info.value)
        assert "session_timebox_minutes" in error_str.lower()
        assert "positive" in error_str


class TestTypedObjects:
    """Tests that valid configs load into typed objects."""

    def test_provider_loads_as_typed_object(self) -> None:
        """Test that provider config loads as ProviderConfig object."""
        data = {
            "name": "fireworks",
            "route_name": "fireworks-main",
            "protocol_surface": "anthropic_messages",
            "upstream_base_url_env": "FIREWORKS_BASE_URL",
            "api_key_env": "FIREWORKS_API_KEY",
            "models": [{"alias": "kimi-k2-5", "upstream_model": "accounts/fireworks/models/kimi-k2p5"}],
            "routing_defaults": {"timeout_seconds": 180}
        }
        config = ProviderConfig(**data)
        assert isinstance(config, ProviderConfig)
        assert isinstance(config.models[0], ProviderModel)
        assert isinstance(config.routing_defaults, RoutingDefaults)

    def test_harness_loads_as_typed_object(self) -> None:
        """Test that harness profile loads as HarnessProfile object."""
        data = {
            "name": "claude-code",
            "protocol_surface": "anthropic_messages",
            "base_url_env": "ANTHROPIC_BASE_URL",
            "api_key_env": "ANTHROPIC_API_KEY",
            "model_env": "ANTHROPIC_MODEL",
            "extra_env": {"ANTHROPIC_DEFAULT_SONNET_MODEL": "{{ model_alias }}"},
            "render_format": "shell",
            "launch_checks": ["base URL points to local LiteLLM"]
        }
        profile = HarnessProfile(**data)
        assert isinstance(profile, HarnessProfile)
        assert profile.extra_env["ANTHROPIC_DEFAULT_SONNET_MODEL"] == "{{ model_alias }}"

    def test_variant_loads_as_typed_object(self) -> None:
        """Test that variant loads as Variant object."""
        data = {
            "name": "test-variant",
            "provider": "fireworks",
            "model_alias": "kimi-k2-5",
            "harness_profile": "claude-code",
            "benchmark_tags": {
                "harness": "claude-code",
                "provider": "fireworks",
                "model": "kimi-k2-5"
            }
        }
        variant = Variant(**data)
        assert isinstance(variant, Variant)
        assert variant.benchmark_tags["provider"] == "fireworks"

    def test_experiment_loads_as_typed_object(self) -> None:
        """Test that experiment loads as Experiment object."""
        data = {
            "name": "test-experiment",
            "description": "Test description",
            "variants": ["variant-1", "variant-2"]
        }
        experiment = Experiment(**data)
        assert isinstance(experiment, Experiment)
        assert experiment.variants == ["variant-1", "variant-2"]

    def test_task_card_loads_as_typed_object(self) -> None:
        """Test that task card loads as TaskCard object."""
        data = {
            "name": "repo-auth-analysis",
            "repo_path": "/path/to/repo",
            "goal": "identify auth flow",
            "starting_prompt": "Analyze auth.",
            "stop_condition": "produce summary",
            "session_timebox_minutes": 30,
            "notes": ["note 1"]
        }
        task_card = TaskCard(**data)
        assert isinstance(task_card, TaskCard)
        assert task_card.notes == ["note 1"]
