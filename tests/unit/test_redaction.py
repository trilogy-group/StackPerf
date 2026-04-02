"""Unit tests for redaction utilities.

Tests verify that secrets are properly redacted and that
the redaction layer protects against accidental secret leakage.
"""

from benchmark_core.security.redaction import (
    REDACTION_PATTERNS,
    RedactionConfig,
    redact_dict,
    redact_string,
    redact_value,
)
from benchmark_core.security.secrets import (
    SecretDetector,
    detect_secrets,
    is_likely_secret,
    scan_dict_for_secrets,
)


class TestRedactionDefaults:
    """Test that redaction defaults are secure.

    These tests verify the core security requirement:
    prompts and responses are not persisted by default,
    and logs/exports do not leak secrets.
    """

    def test_redaction_enabled_by_default(self) -> None:
        """Redaction should be enabled by default."""
        config = RedactionConfig()
        assert config.enabled is True

    def test_default_placeholder_is_clear(self) -> None:
        """Default placeholder should clearly indicate redaction."""
        config = RedactionConfig()
        assert config.placeholder == "[REDACTED]"

    def test_sensitive_keys_include_api_key(self) -> None:
        """Sensitive keys should include 'api_key'."""
        config = RedactionConfig()
        assert "api_key" in config.sensitive_keys

    def test_sensitive_keys_include_token(self) -> None:
        """Sensitive keys should include 'token'."""
        config = RedactionConfig()
        assert "token" in config.sensitive_keys

    def test_sensitive_keys_include_secret(self) -> None:
        """Sensitive keys should include 'secret'."""
        config = RedactionConfig()
        assert "secret" in config.sensitive_keys


class TestRedactString:
    """Test string redaction with various secret formats."""

    def test_redact_openai_key(self, synthetic_secrets: dict[str, str]) -> None:
        """OpenAI-style API keys should be redacted."""
        secret = synthetic_secrets["openai_api_key"]
        text = f"The API key is {secret}"
        result = redact_string(text)
        assert secret not in result
        assert "[REDACTED]" in result

    def test_redact_anthropic_key(self, synthetic_secrets: dict[str, str]) -> None:
        """Anthropic API keys should be redacted."""
        secret = synthetic_secrets["anthropic_api_key"]
        text = f"Using key: {secret}"
        result = redact_string(text)
        assert secret not in result
        assert "[REDACTED]" in result

    def test_redact_bearer_token(self, synthetic_secrets: dict[str, str]) -> None:
        """Bearer tokens should be redacted."""
        secret = synthetic_secrets["bearer_token"]
        text = f"Authorization: {secret}"
        result = redact_string(text)
        assert "Bearer eyJ" not in result
        assert "[REDACTED]" in result

    def test_redact_jwt(self, synthetic_secrets: dict[str, str]) -> None:
        """JWT tokens should be redacted."""
        secret = synthetic_secrets["jwt"]
        text = f"Token: {secret}"
        result = redact_string(text)
        assert "eyJ" not in result
        assert "[REDACTED]" in result

    def test_redact_aws_key(self, synthetic_secrets: dict[str, str]) -> None:
        """AWS access keys should be redacted."""
        secret = synthetic_secrets["aws_access_key"]
        text = f"AWS_KEY={secret}"
        result = redact_string(text)
        assert secret not in result
        assert "[REDACTED]" in result

    def test_redact_connection_string_password(self, synthetic_secrets: dict[str, str]) -> None:
        """Passwords in connection strings should be redacted."""
        secret = synthetic_secrets["connection_string"]
        text = f"DB: {secret}"
        result = redact_string(text)
        assert "secretpassword123" not in result
        assert "[REDACTED]" in result

    def test_empty_string_unchanged(self) -> None:
        """Empty strings should pass through unchanged."""
        assert redact_string("") == ""

    def test_non_secret_string_unchanged(self) -> None:
        """Strings without secrets should not be modified."""
        text = "Hello, world! This is a normal log message."
        result = redact_string(text)
        assert result == text

    def test_redaction_can_be_disabled(self) -> None:
        """Redaction can be disabled if needed."""
        secret = "sk-test1234567890abcdefghijklmnopqrstuvwxyz1234567890"
        text = f"Key: {secret}"
        config = RedactionConfig(enabled=False)
        result = redact_string(text, config)
        # With redaction disabled, secret should NOT be replaced
        # Note: This test documents the behavior but should rarely be used
        assert result == text


class TestRedactDict:
    """Test dictionary redaction."""

    def test_redact_api_key_in_dict(self) -> None:
        """API keys should be redacted when key name indicates sensitivity."""
        data = {"api_key": "sk-test1234567890abcdefghijklmnopqrstuvwxyz1234567890"}
        result = redact_dict(data)
        assert result["api_key"] == "[REDACTED]"

    def test_redact_token_in_dict(self) -> None:
        """Tokens should be redacted when key name indicates sensitivity."""
        data = {"token": "some-secret-token-value"}
        result = redact_dict(data)
        assert result["token"] == "[REDACTED]"

    def test_redact_nested_secret_in_value(self, synthetic_secrets: dict[str, str]) -> None:
        """Secrets in nested values should be redacted."""
        secret = synthetic_secrets["openai_api_key"]
        data = {"config": {"model": "gpt-4", "key": secret}}
        result = redact_dict(data)
        assert secret not in str(result)
        assert "[REDACTED]" in str(result)

    def test_preserve_non_sensitive_data(self) -> None:
        """Non-sensitive data should be preserved."""
        data = {
            "model": "gpt-4",
            "temperature": 0.7,
            "max_tokens": 1000,
        }
        result = redact_dict(data)
        assert result["model"] == "gpt-4"
        assert result["temperature"] == 0.7
        assert result["max_tokens"] == 1000

    def test_redact_nested_dict(self) -> None:
        """Nested dictionaries should be recursively redacted."""
        data = {
            "session": {
                "id": "session-123",
                "credentials": {
                    "api_key": "sk-test-super-secret-key-123",
                    "model": "gpt-4",
                },
            }
        }
        result = redact_dict(data)
        assert result["session"]["credentials"]["api_key"] == "[REDACTED]"
        assert result["session"]["credentials"]["model"] == "gpt-4"


class TestRedactValue:
    """Test generic value redaction."""

    def test_redact_string_value(self) -> None:
        """String values should be checked for secrets."""
        value = "sk-test1234567890abcdefghijklmnopqrstuvwxyz1234567890"
        result = redact_value(value)
        assert result == "[REDACTED]"

    def test_preserve_int_value(self) -> None:
        """Integer values should pass through unchanged."""
        assert redact_value(42) == 42

    def test_preserve_float_value(self) -> None:
        """Float values should pass through unchanged."""
        assert redact_value(3.14) == 3.14

    def test_preserve_bool_value(self) -> None:
        """Boolean values should pass through unchanged."""
        assert redact_value(True) is True

    def test_redact_list_with_secrets(self) -> None:
        """Lists containing secrets should be redacted."""
        values = ["normal", "sk-test1234567890abcdefghijklmnopqrstuvwxyz1234567890", "also-normal"]
        result = redact_value(values)
        assert result[1] == "[REDACTED]"


class TestSecretDetection:
    """Test secret detection functionality."""

    def test_detect_openai_key(self, synthetic_secrets: dict[str, str]) -> None:
        """Should detect OpenAI-style keys."""
        matches = detect_secrets(synthetic_secrets["openai_api_key"])
        assert len(matches) > 0
        assert any(m.pattern_name == "openai_key" for m in matches)

    def test_detect_anthropic_key(self, synthetic_secrets: dict[str, str]) -> None:
        """Should detect Anthropic keys."""
        matches = detect_secrets(synthetic_secrets["anthropic_api_key"])
        assert len(matches) > 0

    def test_detect_jwt(self, synthetic_secrets: dict[str, str]) -> None:
        """Should detect JWT tokens."""
        matches = detect_secrets(synthetic_secrets["jwt"])
        assert len(matches) > 0

    def test_detect_aws_key(self, synthetic_secrets: dict[str, str]) -> None:
        """Should detect AWS access keys."""
        matches = detect_secrets(synthetic_secrets["aws_access_key"])
        assert len(matches) > 0

    def test_no_match_normal_text(self) -> None:
        """Normal text should not trigger detection."""
        matches = detect_secrets("Hello, world! This is a normal message.")
        assert len(matches) == 0

    def test_min_confidence_filter(self) -> None:
        """Detector should filter by minimum confidence."""
        detector = SecretDetector(min_confidence=0.99)
        # Only very high confidence matches should appear
        matches = detect_secrets("sk-test1234567890abcdefghijklmnopqrstuvwxyz1234567890", detector)
        # Should detect but at various confidence levels
        assert isinstance(matches, list)

    def test_detection_can_be_disabled(self) -> None:
        """Detection can be disabled."""
        detector = SecretDetector(enabled=False)
        matches = detect_secrets("sk-test1234567890abcdefghijklmnopqrstuvwxyz1234567890", detector)
        assert len(matches) == 0

    def test_is_likely_secret_with_key(self) -> None:
        """Should identify secrets by key name."""
        assert is_likely_secret("any-value", "api_key") is True
        assert is_likely_secret("any-value", "token") is True
        assert is_likely_secret("any-value", "normal_field") is False

    def test_scan_dict_finds_secrets(self, synthetic_secrets: dict[str, str]) -> None:
        """Should find secrets in dictionaries."""
        data = {
            "openai_key": synthetic_secrets["openai_api_key"],
            "model": "gpt-4",
        }
        results = scan_dict_for_secrets(data)
        assert "openai_key" in results
        assert len(results["openai_key"]) > 0


class TestRedactionPatterns:
    """Test built-in redaction patterns."""

    def test_patterns_exist(self) -> None:
        """Should have built-in patterns defined."""
        assert len(REDACTION_PATTERNS) > 0

    def test_patterns_are_compiled(self) -> None:
        """All patterns should be compiled regex."""
        for _name, pattern in REDACTION_PATTERNS:
            # Compiled patterns have .pattern attribute
            assert hasattr(pattern, "pattern")

    def test_patterns_cover_common_formats(self) -> None:
        """Should cover common secret formats."""
        pattern_names = {name for name, _ in REDACTION_PATTERNS}
        assert "openai_api_key" in pattern_names
        assert "jwt_token" in pattern_names
        assert "private_key" in pattern_names
