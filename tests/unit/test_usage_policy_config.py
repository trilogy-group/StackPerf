"""Tests for usage policy config schemas and validation."""

import tempfile
from pathlib import Path

import pytest
from pydantic import ValidationError

from benchmark_core.config import (
    RedactionPolicy,
    UsagePolicyConfig,
    UsagePolicyProfile,
)
from benchmark_core.config_loader import ConfigLoader, ConfigRegistry, ConfigValidationError

# Get configs directory relative to test file
TESTS_DIR = Path(__file__).parent.parent.parent
CONFIGS_DIR = TESTS_DIR / "configs"


class TestRedactionPolicy:
    """Tests for RedactionPolicy."""

    def test_valid_redaction_policy(self) -> None:
        """Test creating a valid RedactionPolicy."""
        policy = RedactionPolicy(
            policy_name="default-redaction",
            retain_prompts=False,
            retain_responses=False,
            retention_days=30,
        )
        assert policy.policy_name == "default-redaction"
        assert policy.retain_prompts is False
        assert policy.retention_days == 30

    def test_empty_redaction_policy(self) -> None:
        """Test creating an empty RedactionPolicy."""
        policy = RedactionPolicy()
        assert policy.policy_name is None
        assert policy.retain_prompts is None
        assert policy.retention_days is None

    def test_invalid_retention_days(self) -> None:
        """Test that non-positive retention_days raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            RedactionPolicy(retention_days=0)
        assert "retention_days" in str(exc_info.value)
        assert "positive" in str(exc_info.value)

    def test_empty_policy_name_raises(self) -> None:
        """Test that empty policy_name raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            RedactionPolicy(policy_name="")
        assert "policy_name" in str(exc_info.value)
        assert "empty" in str(exc_info.value)


class TestUsagePolicyProfile:
    """Tests for UsagePolicyProfile."""

    def test_valid_usage_policy_profile(self) -> None:
        """Test creating a valid UsagePolicyProfile."""
        profile = UsagePolicyProfile(
            name="platform-team-default",
            description="Default policy for platform team",
            allowed_models=["kimi-k2-5", "gpt-4o"],
            budget_duration="30d",
            budget_amount=1000.0,
            ttl_seconds=2592000,
            owner="platform-team",
            team="platform",
            customer="internal",
            metadata={"cost_center": "engineering"},
            redaction_policy=RedactionPolicy(
                policy_name="default-redaction",
                retention_days=30,
            ),
        )
        assert profile.name == "platform-team-default"
        assert profile.allowed_models == ["kimi-k2-5", "gpt-4o"]
        assert profile.budget_amount == 1000.0
        assert profile.owner == "platform-team"
        assert profile.redaction_policy is not None
        assert profile.redaction_policy.retention_days == 30

    def test_minimal_usage_policy_profile(self) -> None:
        """Test creating a minimal UsagePolicyProfile with only name."""
        profile = UsagePolicyProfile(name="minimal")
        assert profile.name == "minimal"
        assert profile.description == ""
        assert profile.allowed_models == []
        assert profile.budget_duration is None
        assert profile.budget_amount is None
        assert profile.ttl_seconds is None
        assert profile.owner is None
        assert profile.team is None
        assert profile.customer is None
        assert profile.metadata == {}
        assert profile.redaction_policy is None

    def test_empty_name_raises(self) -> None:
        """Test that empty name raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            UsagePolicyProfile(name="")
        assert "must not be empty or whitespace" in str(exc_info.value)

    def test_empty_allowed_model_raises(self) -> None:
        """Test that empty/whitespace allowed_models item raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            UsagePolicyProfile(name="test", allowed_models=[""])
        assert "allowed_models" in str(exc_info.value)
        assert "empty" in str(exc_info.value)

    def test_duplicate_allowed_model_raises(self) -> None:
        """Test that duplicate allowed_models items raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            UsagePolicyProfile(name="test", allowed_models=["gpt-4o", "gpt-4o"])
        assert "allowed_models" in str(exc_info.value)
        assert "duplicate" in str(exc_info.value)

    def test_empty_owner_raises(self) -> None:
        """Test that empty owner string raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            UsagePolicyProfile(name="test", owner="")
        assert "owner" in str(exc_info.value)
        assert "empty" in str(exc_info.value)

    def test_empty_team_raises(self) -> None:
        """Test that empty team string raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            UsagePolicyProfile(name="test", team="")
        assert "team" in str(exc_info.value)
        assert "empty" in str(exc_info.value)

    def test_empty_customer_raises(self) -> None:
        """Test that empty customer string raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            UsagePolicyProfile(name="test", customer="")
        assert "customer" in str(exc_info.value)
        assert "empty" in str(exc_info.value)

    def test_negative_budget_raises(self) -> None:
        """Test that negative budget_amount raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            UsagePolicyProfile(name="test", budget_amount=-1.0)
        assert "budget_amount" in str(exc_info.value)
        assert "positive" in str(exc_info.value)

    def test_zero_budget_raises(self) -> None:
        """Test that zero budget_amount raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            UsagePolicyProfile(name="test", budget_amount=0.0)
        assert "budget_amount" in str(exc_info.value)
        assert "positive" in str(exc_info.value)

    def test_invalid_budget_duration_raises(self) -> None:
        """Test that non-standard budget_duration format raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            UsagePolicyProfile(name="test", budget_duration="foobar")
        assert "budget_duration" in str(exc_info.value)
        assert "duration format" in str(exc_info.value)

    def test_budget_duration_formats(self) -> None:
        """Test that valid budget_duration formats are accepted."""
        for duration in ("1d", "30d", "12h", "5m", "100d"):
            profile = UsagePolicyProfile(name="test", budget_duration=duration)
            assert profile.budget_duration == duration

    def test_zero_budget_duration_raises(self) -> None:
        """Test that zero budget_duration (e.g. 0d) raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            UsagePolicyProfile(name="test", budget_duration="0d")
        assert "budget_duration" in str(exc_info.value)
        assert "duration format" in str(exc_info.value)

    def test_zero_ttl_raises(self) -> None:
        """Test that zero ttl_seconds raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            UsagePolicyProfile(name="test", ttl_seconds=0)
        assert "ttl_seconds" in str(exc_info.value)
        assert "positive" in str(exc_info.value)

    def test_rejects_sk_in_name(self) -> None:
        """Test that sk- prefix in name is rejected as secret-like."""
        with pytest.raises(ValidationError) as exc_info:
            UsagePolicyProfile(name="sk-0123456789012345678901234567890")
        assert "secret-like values" in str(exc_info.value)
        assert "name" in str(exc_info.value)

    def test_rejects_sk_in_owner(self) -> None:
        """Test that sk- prefix in owner is rejected as secret-like."""
        with pytest.raises(ValidationError) as exc_info:
            UsagePolicyProfile(
                name="test",
                owner="sk-ant-0123456789012345678901234567890",
            )
        assert "secret-like values" in str(exc_info.value)
        assert "owner" in str(exc_info.value)

    def test_rejects_secret_in_metadata(self) -> None:
        """Test that secret-like values in metadata are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            UsagePolicyProfile(
                name="test",
                metadata={"api_key": "sk-ant-0123456789012345678901234567890"},
            )
        assert "secret-like values" in str(exc_info.value)
        assert "metadata.api_key" in str(exc_info.value)

    def test_allows_non_secret_strings(self) -> None:
        """Test that normal strings are not flagged as secrets."""
        profile = UsagePolicyProfile(
            name="team-alpha",
            description="Normal description",
            owner="alice",
            team="platform",
            customer="acme-corp",
            metadata={"region": "us-east-1"},
        )
        assert profile.name == "team-alpha"
        assert profile.metadata["region"] == "us-east-1"

    def test_rejects_bearer_token_in_description(self) -> None:
        """Test that bearer token in description is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            UsagePolicyProfile(
                name="test",
                description="Bearer abcdefghijklmnopqrstuvwxyz123456",
            )
        assert "secret-like values" in str(exc_info.value)
        assert "description" in str(exc_info.value)

    def test_field_error_name(self) -> None:
        """Test that profile name errors are field-specific."""
        with pytest.raises(ValidationError) as exc_info:
            UsagePolicyProfile(name="")
        error_str = str(exc_info.value)
        assert "name" in error_str.lower()
        assert "must not be empty or whitespace" in error_str

    def test_field_error_ttl(self) -> None:
        """Test that ttl_seconds errors are field-specific."""
        with pytest.raises(ValidationError) as exc_info:
            UsagePolicyProfile(name="test", ttl_seconds=-1)
        error_str = str(exc_info.value)
        assert "ttl_seconds" in error_str.lower()
        assert "positive" in error_str


class TestUsagePolicyConfig:
    """Tests for UsagePolicyConfig."""

    def test_valid_usage_policy_config(self) -> None:
        """Test creating a valid UsagePolicyConfig with multiple profiles."""
        config = UsagePolicyConfig(
            profiles=[
                UsagePolicyProfile(name="team-alpha"),
                UsagePolicyProfile(name="team-beta"),
            ]
        )
        assert len(config.profiles) == 2
        assert config.profiles[0].name == "team-alpha"
        assert config.profiles[1].name == "team-beta"

    def test_empty_usage_policy_config(self) -> None:
        """Test creating an empty UsagePolicyConfig."""
        config = UsagePolicyConfig()
        assert config.profiles == []

    def test_duplicate_profile_names(self) -> None:
        """Test that duplicate profile names raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            UsagePolicyConfig(
                profiles=[
                    UsagePolicyProfile(name="team-alpha"),
                    UsagePolicyProfile(name="team-alpha"),
                ]
            )
        assert "duplicate usage policy profile names" in str(exc_info.value)


class TestUsagePolicyRegistry:
    """Tests for ConfigRegistry with usage policies."""

    def test_register_usage_policy(self) -> None:
        """Test registering a usage policy profile."""
        registry = ConfigRegistry()
        profile = UsagePolicyProfile(name="test-policy")
        registry.register_usage_policy(profile)
        assert "test-policy" in registry.usage_policies
        assert registry.usage_policies["test-policy"].name == "test-policy"

    def test_register_duplicate_usage_policy(self) -> None:
        """Test that duplicate usage policy registration raises error."""
        registry = ConfigRegistry()
        profile = UsagePolicyProfile(name="test-policy")
        registry.register_usage_policy(profile)
        with pytest.raises(ConfigValidationError) as exc_info:
            registry.register_usage_policy(profile)
        assert "Duplicate usage policy name" in str(exc_info.value)


class TestUsagePolicyLoader:
    """Tests for ConfigLoader with usage policies."""

    def test_load_usage_policies_from_examples(self) -> None:
        """Test loading usage policies from example configs."""
        loader = ConfigLoader(CONFIGS_DIR)
        policies = loader.load_usage_policies()

        # Should load the default.yaml usage policies
        assert "platform-team-default" in policies
        assert "data-science-team" in policies

        platform = policies["platform-team-default"]
        assert platform.team == "platform"
        assert platform.customer == "internal"
        assert platform.budget_amount == 1000.0
        assert platform.budget_duration == "30d"
        assert "kimi-k2-5" in platform.allowed_models
        assert platform.redaction_policy is not None
        assert platform.redaction_policy.retention_days == 30

        ds = policies["data-science-team"]
        assert ds.team == "data-science"
        assert ds.budget_amount == 5000.0
        assert ds.redaction_policy is not None
        assert ds.redaction_policy.retention_days == 90

    def test_load_all_includes_usage_policies(self) -> None:
        """Test that load_all includes usage policies without breaking benchmark configs."""
        loader = ConfigLoader(CONFIGS_DIR)
        registry = loader.load_all()

        # Benchmark configs still work
        assert "fireworks" in registry.providers
        assert "claude-code" in registry.harness_profiles
        assert "fireworks-kimi-k2-5-claude-code" in registry.variants

        # Usage policies loaded
        assert "platform-team-default" in registry.usage_policies
        assert "data-science-team" in registry.usage_policies

    def test_load_usage_policies_missing_dir(self) -> None:
        """Test that missing usage-policies directory returns empty dict."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ConfigLoader(tmpdir)
            policies = loader.load_usage_policies()
            assert policies == {}

    def test_load_all_without_usage_policies_dir(self) -> None:
        """Test that load_all works without usage-policies directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ConfigLoader(tmpdir)
            registry = loader.load_all()
            assert registry.usage_policies == {}
            assert registry.providers == {}

    def test_load_usage_policies_file_with_multiple_profiles(self) -> None:
        """Test loading a single file with multiple profiles."""
        loader = ConfigLoader(CONFIGS_DIR)
        policies = loader.load_usage_policies()

        assert len(policies) >= 2
        names = set(policies.keys())
        assert "platform-team-default" in names
        assert "data-science-team" in names

    def test_load_all_preserves_existing_config_compatibility(self) -> None:
        """Regression test: existing config types are unaffected by usage policy loading."""
        loader = ConfigLoader(CONFIGS_DIR)
        registry = loader.load_all()

        # Existing types are still accessible
        assert isinstance(registry.providers, dict)
        assert isinstance(registry.harness_profiles, dict)
        assert isinstance(registry.variants, dict)
        assert isinstance(registry.experiments, dict)
        assert isinstance(registry.task_cards, dict)
        assert isinstance(registry.usage_policies, dict)

        # Validate cross-references still work
        assert registry.validate_references() == []
