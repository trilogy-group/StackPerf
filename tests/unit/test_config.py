"""Unit tests for core configuration.

Tests verify default-off content capture and related security settings.
"""

from src.benchmark_core.config import (
    DEFAULT_CONTENT_CAPTURE_POLICY,
    DEFAULT_RETENTION_DAYS,
    DEFAULT_SECRET_HANDLING,
    MAX_SESSION_CREDENTIAL_TTL_SECONDS,
    MIN_SESSION_CREDENTIAL_TTL_SECONDS,
    ContentCapturePolicy,
    SecretHandling,
    is_content_capture_enabled,
    should_store_prompts,
    should_store_responses,
)


class TestContentCaptureDefaults:
    """Test that content capture defaults are secure.

    Core acceptance criterion: prompts and responses are not persisted by default.
    """

    def test_default_content_capture_is_disabled(self) -> None:
        """Default content capture policy should be DISABLED."""
        assert DEFAULT_CONTENT_CAPTURE_POLICY == ContentCapturePolicy.DISABLED

    def test_is_content_capture_enabled_returns_false_by_default(self) -> None:
        """Content capture should be disabled by default."""
        assert is_content_capture_enabled() is False

    def test_should_store_prompts_returns_false_by_default(self) -> None:
        """Prompts should NOT be stored by default."""
        assert should_store_prompts() is False

    def test_should_store_responses_returns_false_by_default(self) -> None:
        """Responses should NOT be stored by default."""
        assert should_store_responses() is False

    def test_disabled_policy_disables_all_content(self) -> None:
        """DISABLED policy should disable all content functions."""
        policy = ContentCapturePolicy.DISABLED
        assert is_content_capture_enabled(policy) is False
        assert should_store_prompts(policy) is False
        assert should_store_responses(policy) is False

    def test_metadata_only_disables_content(self) -> None:
        """METADATA_ONLY should not enable content capture."""
        policy = ContentCapturePolicy.METADATA_ONLY
        assert is_content_capture_enabled(policy) is False
        assert should_store_prompts(policy) is False
        assert should_store_responses(policy) is False

    def test_redacted_enables_content_capture(self) -> None:
        """REDACTED policy should enable content capture."""
        policy = ContentCapturePolicy.REDACTED
        assert is_content_capture_enabled(policy) is True
        assert should_store_prompts(policy) is False  # Not full capture
        assert should_store_responses(policy) is False

    def test_full_enables_all_content(self) -> None:
        """FULL policy should enable all content storage."""
        policy = ContentCapturePolicy.FULL
        assert is_content_capture_enabled(policy) is True
        assert should_store_prompts(policy) is True
        assert should_store_responses(policy) is True


class TestSecretHandlingDefaults:
    """Test that secret handling defaults are secure."""

    def test_default_secret_handling_is_redact(self) -> None:
        """Default secret handling should be REDACT."""
        assert DEFAULT_SECRET_HANDLING == SecretHandling.REDACT


class TestSessionCredentialTTL:
    """Test session credential TTL limits."""

    def test_min_ttl_is_reasonable(self) -> None:
        """Minimum TTL should be at least 1 hour."""
        assert MIN_SESSION_CREDENTIAL_TTL_SECONDS >= 3600

    def test_max_ttl_is_reasonable(self) -> None:
        """Maximum TTL should not exceed 24 hours."""
        assert MAX_SESSION_CREDENTIAL_TTL_SECONDS <= 86400

    def test_min_less_than_max(self) -> None:
        """Min TTL should be less than max TTL."""
        assert MIN_SESSION_CREDENTIAL_TTL_SECONDS < MAX_SESSION_CREDENTIAL_TTL_SECONDS


class TestRetentionDefaults:
    """Test that retention defaults are documented and reasonable."""

    def test_retention_defaults_exist(self) -> None:
        """Retention defaults should be defined."""
        assert len(DEFAULT_RETENTION_DAYS) > 0

    def test_raw_ingestion_has_short_retention(self) -> None:
        """Raw ingestion should have short retention (default 7 days)."""
        assert DEFAULT_RETENTION_DAYS.get("raw_ingestion", 0) <= 7

    def test_session_credentials_have_minimum_retention(self) -> None:
        """Session credentials should have minimum retention."""
        assert DEFAULT_RETENTION_DAYS.get("session_credentials", 1) <= 1

    def test_rollups_have_long_retention(self) -> None:
        """Rollups should have long retention for trend analysis."""
        assert DEFAULT_RETENTION_DAYS.get("rollups", 0) >= 365

    def test_artifacts_have_moderate_retention(self) -> None:
        """Artifacts should have moderate retention for audits."""
        retention = DEFAULT_RETENTION_DAYS.get("artifacts", 0)
        assert retention >= 30 and retention <= 365


class TestContentCapturePolicyEnum:
    """Test ContentCapturePolicy enum values."""

    def test_disabled_value(self) -> None:
        """DISABLED should have correct string value."""
        assert ContentCapturePolicy.DISABLED.value == "disabled"

    def test_metadata_only_value(self) -> None:
        """METADATA_ONLY should have correct string value."""
        assert ContentCapturePolicy.METADATA_ONLY.value == "metadata_only"

    def test_redacted_value(self) -> None:
        """REDACTED should have correct string value."""
        assert ContentCapturePolicy.REDACTED.value == "redacted"

    def test_full_value(self) -> None:
        """FULL should have correct string value."""
        assert ContentCapturePolicy.FULL.value == "full"
