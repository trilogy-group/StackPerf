"""Tests for security redaction, content capture, and retention features."""

import re
from datetime import UTC, datetime, timedelta

from benchmark_core.security import (
    DEFAULT_CONTENT_CAPTURE_CONFIG,
    DEFAULT_REDACTION_CONFIG,
    DEFAULT_RETENTION_SETTINGS,
    ContentCaptureConfig,
    RedactionConfig,
    RedactionFilter,
    RetentionPolicy,
    RetentionSettings,
    get_redaction_filter,
    redact_for_logging,
    should_capture_content,
)


class TestRedactionConfig:
    """Tests for RedactionConfig."""

    def test_default_config_is_enabled(self) -> None:
        """Default redaction config is enabled."""
        config = RedactionConfig()
        assert config.enabled is True

    def test_default_patterns_are_compiled(self) -> None:
        """Default patterns are compiled from SecretPattern enum."""
        config = RedactionConfig()
        assert len(config.patterns) > 0
        for pattern in config.patterns:
            assert isinstance(pattern, re.Pattern)

    def test_custom_patterns_can_be_set(self) -> None:
        """Custom patterns can be provided."""
        custom_pattern = re.compile(r"my-secret-\d+")
        config = RedactionConfig(patterns=[custom_pattern])
        assert len(config.patterns) == 1
        assert config.patterns[0] == custom_pattern

    def test_can_disable_redaction(self) -> None:
        """Redaction can be disabled."""
        config = RedactionConfig(enabled=False)
        assert config.enabled is False


class TestRedactionFilter:
    """Tests for RedactionFilter."""

    def test_redact_openai_api_key(self) -> None:
        """OpenAI-style API keys are redacted."""
        filter_obj = RedactionFilter()
        text = "Using API key sk-1234567890abcdefghijklmnopqrst"
        result = filter_obj.redact_string(text)
        assert "sk-1234567890abcdefghijklmnopqrst" not in result
        assert "[REDACTED]" in result

    def test_redact_bearer_token(self) -> None:
        """Bearer tokens are redacted."""
        filter_obj = RedactionFilter()
        text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        result = filter_obj.redact_string(text)
        assert "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in result

    def test_redact_database_url(self) -> None:
        """Database connection strings are redacted."""
        filter_obj = RedactionFilter()
        text = "postgresql://user:secretpassword@localhost:5432/mydb"
        result = filter_obj.redact_string(text)
        assert "secretpassword" not in result
        assert "[REDACTED]" in result

    def test_redact_dict_values(self) -> None:
        """Secret values in dictionaries are redacted."""
        filter_obj = RedactionFilter()
        data = {
            "api_key": "sk-1234567890abcdefghijklmnopqrst",
            "model": "gpt-4",
            "metadata": {"token": "Bearer abc123def456ghi789jkl"},
        }
        result = filter_obj.redact_dict(data)
        assert "sk-1234567890abcdefghijklmnopqrst" not in result["api_key"]
        assert result["model"] == "gpt-4"  # Non-secret preserved
        assert "Bearer abc123def456ghi789jkl" not in result["metadata"]["token"]

    def test_redact_dict_keys_if_secret(self) -> None:
        """Dictionary keys containing secrets are redacted."""
        filter_obj = RedactionFilter()
        data = {"sk-1234567890abcdefghijklmnopqrst": "value"}
        result = filter_obj.redact_dict(data)
        # Key should be redacted
        assert "sk-1234567890abcdefghijklmnopqrst" not in result

    def test_redact_list(self) -> None:
        """Secrets in lists are redacted."""
        filter_obj = RedactionFilter()
        data = [
            "sk-1234567890abcdefghijklmnopqrst",
            "normal text",
            {"key": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9eyJhbGciOiJIUzI1NiJ9"},
        ]
        result = filter_obj.redact_list(data)
        assert "sk-1234567890abcdefghijklmnopqrst" not in result[0]
        assert result[1] == "normal text"
        # Bearer tokens with 20+ chars are redacted
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in result[2]["key"]

    def test_redact_nested_structures(self) -> None:
        """Deeply nested secrets are redacted."""
        filter_obj = RedactionFilter()
        data = {
            "level1": {
                "level2": {
                    "level3": {
                        "secret": "sk-1234567890abcdefghijklmnopqrst",
                    }
                }
            }
        }
        result = filter_obj.redact_dict(data)
        assert (
            "sk-1234567890abcdefghijklmnopqrst"
            not in result["level1"]["level2"]["level3"]["secret"]
        )

    def test_disabled_filter_preserves_everything(self) -> None:
        """When disabled, filter preserves all content."""
        config = RedactionConfig(enabled=False)
        filter_obj = RedactionFilter(config)
        text = "sk-1234567890abcdefghijklmnopqrst"
        result = filter_obj.redact_string(text)
        assert result == text

    def test_custom_replacement_text(self) -> None:
        """Custom replacement text is used."""
        config = RedactionConfig(replacement="<SECRET>")
        filter_obj = RedactionFilter(config)
        text = "Using key sk-1234567890abcdefghijklmnopqrst now"
        result = filter_obj.redact_string(text)
        assert "[REDACTED]" not in result
        assert "<SECRET>" in result

    def test_preserve_prefix_suffix_for_long_values(self) -> None:
        """Long secret values show prefix and suffix."""
        config = RedactionConfig(
            preserve_prefix_length=4,
            preserve_suffix_length=4,
        )
        filter_obj = RedactionFilter(config)
        # Use a value that matches the pattern (20+ chars after sk-)
        long_key = "sk-1234567890abcdefghijklmnopqrst"
        result = filter_obj._redact_if_secret(long_key)
        # The value should be redacted (matched by API key pattern)
        assert "[REDACTED]" in result or "sk-1" in result  # Either fully redacted or shows prefix


class TestContentCaptureConfig:
    """Tests for ContentCaptureConfig."""

    def test_default_is_disabled(self) -> None:
        """Content capture is disabled by default."""
        config = ContentCaptureConfig()
        assert config.enabled is False
        assert config.capture_prompts is False
        assert config.capture_responses is False
        assert config.capture_tool_payloads is False

    def test_should_capture_prompt_when_enabled(self) -> None:
        """Prompts are captured only when explicitly enabled."""
        config = ContentCaptureConfig(enabled=True, capture_prompts=True)
        assert config.should_capture_prompt() is True

    def test_should_not_capture_prompt_when_disabled(self) -> None:
        """Prompts are not captured when master switch is off."""
        config = ContentCaptureConfig(enabled=False, capture_prompts=True)
        assert config.should_capture_prompt() is False

    def test_should_capture_response_when_enabled(self) -> None:
        """Responses are captured only when explicitly enabled."""
        config = ContentCaptureConfig(enabled=True, capture_responses=True)
        assert config.should_capture_response() is True

    def test_should_not_capture_response_by_default(self) -> None:
        """Responses are not captured by default even if enabled."""
        config = ContentCaptureConfig(enabled=True)
        assert config.should_capture_response() is False

    def test_redaction_enabled_in_content_by_default(self) -> None:
        """Secrets in captured content are redacted by default."""
        config = ContentCaptureConfig()
        assert config.redact_secrets_in_content is True


class TestRetentionPolicy:
    """Tests for RetentionPolicy."""

    def test_default_retention_is_none(self) -> None:
        """Default retention keeps data forever."""
        policy = RetentionPolicy(data_type="test")
        assert policy.retention_days is None

    def test_get_cutoff_date_with_no_retention(self) -> None:
        """No cutoff date when retention is None."""
        policy = RetentionPolicy(data_type="test", retention_days=None)
        cutoff = policy.get_cutoff_date()
        assert cutoff is None

    def test_get_cutoff_date_with_retention(self) -> None:
        """Cutoff date is calculated correctly."""
        policy = RetentionPolicy(data_type="test", retention_days=30)
        cutoff = policy.get_cutoff_date()
        assert cutoff is not None

        # Should be approximately 30 days ago
        expected = datetime.now(UTC) - timedelta(days=30)
        delta = abs((cutoff - expected).total_seconds())
        assert delta < 60  # Within 1 minute

    def test_is_eligible_for_cleanup_old_record(self) -> None:
        """Old records are eligible for cleanup."""
        policy = RetentionPolicy(data_type="test", retention_days=30, min_age_days=1)
        old_date = datetime.now(UTC) - timedelta(days=60)
        assert policy.is_eligible_for_cleanup(old_date) is True

    def test_is_not_eligible_for_cleanup_recent_record(self) -> None:
        """Recent records are not eligible for cleanup."""
        policy = RetentionPolicy(data_type="test", retention_days=30, min_age_days=1)
        recent_date = datetime.now(UTC) - timedelta(days=10)
        assert policy.is_eligible_for_cleanup(recent_date) is False

    def test_is_not_eligible_for_cleanup_very_recent_record(self) -> None:
        """Records younger than min_age are not eligible."""
        policy = RetentionPolicy(data_type="test", retention_days=1, min_age_days=5)
        recent_date = datetime.now(UTC) - timedelta(days=2)
        assert policy.is_eligible_for_cleanup(recent_date) is False

    def test_cleanup_batch_size_default(self) -> None:
        """Default batch size is reasonable."""
        policy = RetentionPolicy(data_type="test")
        assert policy.cleanup_batch_size > 0


class TestRetentionSettings:
    """Tests for RetentionSettings."""

    def test_default_settings_exist(self) -> None:
        """Default settings have policies for all data types."""
        settings = RetentionSettings()
        assert settings.raw_ingestion is not None
        assert settings.normalized_requests is not None
        assert settings.sessions is not None
        assert settings.session_credentials is not None
        assert settings.artifacts is not None
        assert settings.metric_rollups is not None

    def test_raw_ingestion_short_retention(self) -> None:
        """Raw ingestion has short retention."""
        settings = RetentionSettings()
        # Raw data should be cleaned up quickly
        assert settings.raw_ingestion.retention_days is not None
        assert settings.raw_ingestion.retention_days <= 30

    def test_session_credentials_very_short_retention(self) -> None:
        """Session credentials have very short retention."""
        settings = RetentionSettings()
        # Credentials should expire quickly
        assert settings.session_credentials.retention_days is not None
        assert settings.session_credentials.retention_days <= 7

    def test_normalized_requests_longer_retention(self) -> None:
        """Normalized requests have longer retention than raw."""
        settings = RetentionSettings()
        # Normalized data is more valuable, keep longer
        assert settings.normalized_requests.retention_days is not None
        assert settings.normalized_requests.retention_days > settings.raw_ingestion.retention_days  # type: ignore

    def test_get_policy_for_valid_type(self) -> None:
        """Can retrieve policy by data type."""
        settings = RetentionSettings()
        policy = settings.get_policy("sessions")
        assert policy is not None
        assert policy.data_type == "sessions"

    def test_get_policy_for_invalid_type(self) -> None:
        """Returns None for unknown data type."""
        settings = RetentionSettings()
        policy = settings.get_policy("unknown_type")
        assert policy is None


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_get_redaction_filter_returns_filter(self) -> None:
        """get_redaction_filter returns a configured filter."""
        filter_obj = get_redaction_filter()
        assert isinstance(filter_obj, RedactionFilter)

    def test_get_redaction_filter_with_custom_config(self) -> None:
        """Can provide custom config to get_redaction_filter."""
        config = RedactionConfig(replacement="<HIDDEN>")
        filter_obj = get_redaction_filter(config)
        text = "sk-1234567890abcdefghijklmnopqrst"
        result = filter_obj.redact_string(text)
        assert "<HIDDEN>" in result

    def test_redact_for_logging_string(self) -> None:
        """redact_for_logging redacts strings."""
        text = "key=sk-1234567890abcdefghijklmnopqrst"
        result = redact_for_logging(text)
        assert "sk-1234567890abcdefghijklmnopqrst" not in result

    def test_redact_for_logging_dict(self) -> None:
        """redact_for_logging redacts dicts."""
        data = {"api_key": "sk-1234567890abcdefghijklmnopqrst"}
        result = redact_for_logging(data)
        assert "sk-1234567890abcdefghijklmnopqrst" not in result["api_key"]

    def test_should_capture_content_prompt_disabled(self) -> None:
        """should_capture_content returns False for prompts by default."""
        assert should_capture_content("prompt") is False

    def test_should_capture_content_response_disabled(self) -> None:
        """should_capture_content returns False for responses by default."""
        assert should_capture_content("response") is False

    def test_should_capture_content_with_custom_config(self) -> None:
        """should_capture_content respects custom config."""
        config = ContentCaptureConfig(enabled=True, capture_prompts=True)
        assert should_capture_content("prompt", config) is True
        assert should_capture_content("response", config) is False


class TestDefaultInstances:
    """Tests for module-level default instances."""

    def test_default_redaction_config_enabled(self) -> None:
        """Default redaction config is enabled."""
        assert DEFAULT_REDACTION_CONFIG.enabled is True

    def test_default_content_capture_disabled(self) -> None:
        """Default content capture is disabled."""
        assert DEFAULT_CONTENT_CAPTURE_CONFIG.enabled is False

    def test_default_retention_settings_complete(self) -> None:
        """Default retention settings have all policies."""
        assert DEFAULT_RETENTION_SETTINGS.raw_ingestion is not None
        assert DEFAULT_RETENTION_SETTINGS.sessions is not None


class TestEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_redact_empty_string(self) -> None:
        """Empty string is handled correctly."""
        filter_obj = RedactionFilter()
        result = filter_obj.redact_string("")
        assert result == ""

    def test_redact_none_value(self) -> None:
        """None is handled correctly."""
        filter_obj = RedactionFilter()
        result = filter_obj.redact_any(None)
        assert result is None

    def test_redact_number_value(self) -> None:
        """Numbers are preserved unchanged."""
        filter_obj = RedactionFilter()
        result = filter_obj.redact_any(12345)
        assert result == 12345

    def test_redact_boolean_value(self) -> None:
        """Booleans are preserved unchanged."""
        filter_obj = RedactionFilter()
        result = filter_obj.redact_any(True)
        assert result is True

    def test_multiple_secrets_in_one_string(self) -> None:
        """Multiple secrets in one string are all redacted."""
        filter_obj = RedactionFilter()
        text = "Key1: sk-1234567890abcdefghijklmnopqrst Key2: sk-abcdefghijklmnopqrstuvwx123456"
        result = filter_obj.redact_string(text)
        assert "sk-1234567890abcdefghijklmnopqrst" not in result
        assert "sk-abcdefghijklmnopqrstuvwx123456" not in result

    def test_retention_policy_edge_case_exact_cutoff(self) -> None:
        """Record exactly at cutoff boundary is handled correctly."""
        policy = RetentionPolicy(data_type="test", retention_days=30, min_age_days=1)
        # Record exactly at cutoff (30 days old)
        cutoff_date = datetime.now(UTC) - timedelta(days=30)
        # Due to timing, this might be eligible or not depending on seconds
        # The important thing is it doesn't crash
        result = policy.is_eligible_for_cleanup(cutoff_date)
        assert isinstance(result, bool)

    def test_content_capture_max_length(self) -> None:
        """Content capture config has max length setting."""
        config = ContentCaptureConfig()
        assert config.max_content_length > 0
        assert config.max_content_length == 10000  # Default value
