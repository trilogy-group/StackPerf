"""Security utilities for redaction, content capture control, and retention management.

This module provides:
- Secret redaction for logs, exports, and string representations
- Content capture configuration and enforcement
- Retention policy management and cleanup utilities
"""

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any


class SecretPattern(StrEnum):
    """Common secret patterns for redaction."""

    # API Keys
    OPENAI_API_KEY = "sk-[a-zA-Z0-9]{20,}"
    ANTHROPIC_API_KEY = "sk-ant-[a-zA-Z0-9]{20,}"
    GENERIC_API_KEY = "sk-[a-zA-Z0-9_-]{20,}"
    BEARER_TOKEN = "Bearer\\s+[a-zA-Z0-9._-]{20,}"

    # Database connection strings
    POSTGRES_URL = "postgres(ql)?://[^:]+:[^@]+@[^/]+"
    MYSQL_URL = "mysql://[^:]+:[^@]+@[^/]+"
    REDIS_URL = "redis://[^:]+:[^@]+@[^/]+"
    GENERIC_DB_URL = "(postgres|mysql|redis|mongodb)://[^\\s]+"

    # Environment variable patterns
    ENV_SECRET = "(PASSWORD|SECRET|KEY|TOKEN|CREDENTIAL)[\"']?\\s*[:=]\\s*[\"']?[^\"'\\s]{8,}"

    # AWS credentials
    AWS_ACCESS_KEY = "AKIA[A-Z0-9]{16}"
    # AWS secret keys with context - require specific prefixes to avoid false positives
    AWS_SECRET_KEY_WITH_CONTEXT = "(?:aws_secret_access_key|SecretAccessKey|aws_secret_key)[\"']?\\s*[:=]\\s*[\"']?([A-Za-z0-9/+=]{40})"


@dataclass
class RedactionConfig:
    """Configuration for secret redaction behavior."""

    enabled: bool = True
    patterns: list[re.Pattern] = field(default_factory=list)
    replacement: str = "[REDACTED]"
    preserve_prefix_length: int = 4
    preserve_suffix_length: int = 4

    def __post_init__(self) -> None:
        """Initialize default patterns if none provided."""
        if not self.patterns:
            self.patterns = [re.compile(pattern.value, re.IGNORECASE) for pattern in SecretPattern]


class RedactionFilter:
    """Filter for redacting secrets from strings and data structures."""

    def __init__(self, config: RedactionConfig | None = None) -> None:
        """Initialize redaction filter with optional config.

        Args:
            config: Redaction configuration. Uses defaults if not provided.
        """
        self._config = config or RedactionConfig()

    def redact_string(self, text: str) -> str:
        """Redact secrets from a string.

        Args:
            text: Input string that may contain secrets.

        Returns:
            String with secrets replaced by redaction marker.
        """
        if not self._config.enabled:
            return text

        result = text
        for pattern in self._config.patterns:
            result = pattern.sub(self._config.replacement, result)
        return result

    def redact_dict(self, data: dict[str, Any]) -> dict[str, Any]:
        """Redact secrets from a dictionary, including keys and values.

        Args:
            data: Dictionary that may contain secrets.

        Returns:
            Dictionary with secrets redacted.
        """
        if not self._config.enabled:
            return data

        result: dict[str, Any] = {}
        for key, value in data.items():
            # Redact key if it looks like a secret
            redacted_key = self._redact_if_secret(key)

            # Redact value based on type
            if isinstance(value, str):
                result[redacted_key] = self.redact_string(value)
            elif isinstance(value, dict):
                result[redacted_key] = self.redact_dict(value)
            elif isinstance(value, list):
                result[redacted_key] = self.redact_list(value)
            else:
                result[redacted_key] = value

        return result

    def redact_list(self, data: list[Any]) -> list[Any]:
        """Redact secrets from a list.

        Args:
            data: List that may contain secrets.

        Returns:
            List with secrets redacted.
        """
        if not self._config.enabled:
            return data

        result: list[Any] = []
        for item in data:
            if isinstance(item, str):
                result.append(self.redact_string(item))
            elif isinstance(item, dict):
                result.append(self.redact_dict(item))
            elif isinstance(item, list):
                result.append(self.redact_list(item))
            else:
                result.append(item)

        return result

    def redact_any(self, data: Any) -> Any:
        """Redact secrets from any data type.

        Args:
            data: Data that may contain secrets.

        Returns:
            Data with secrets redacted.
        """
        if not self._config.enabled:
            return data

        if isinstance(data, str):
            return self.redact_string(data)
        elif isinstance(data, dict):
            return self.redact_dict(data)
        elif isinstance(data, list):
            return self.redact_list(data)
        else:
            return data

    def _redact_if_secret(self, value: str) -> str:
        """Redact a value if it matches secret patterns.

        Args:
            value: String to check.

        Returns:
            Original value or redacted version.
        """
        for pattern in self._config.patterns:
            if pattern.search(value):
                # For short values, fully redact
                if (
                    len(value)
                    <= self._config.preserve_prefix_length + self._config.preserve_suffix_length
                ):
                    return self._config.replacement
                # For longer values, show prefix/suffix
                prefix = value[: self._config.preserve_prefix_length]
                suffix = value[-self._config.preserve_suffix_length :]
                return f"{prefix}...{suffix} [REDACTED]"
        return value


@dataclass
class ContentCaptureConfig:
    """Configuration for content capture behavior.

    By default, prompt and response content is NOT captured.
    Only metadata, metrics, and correlation keys are stored.
    """

    # Master switch - when False, no content is captured
    enabled: bool = False

    # What content to capture when enabled
    capture_prompts: bool = False
    capture_responses: bool = False
    capture_tool_payloads: bool = False

    # Maximum content size to capture (characters)
    max_content_length: int = 10000

    # Redaction within captured content
    redact_secrets_in_content: bool = True

    def should_capture_prompt(self) -> bool:
        """Check if prompts should be captured."""
        return self.enabled and self.capture_prompts

    def should_capture_response(self) -> bool:
        """Check if responses should be captured."""
        return self.enabled and self.capture_responses

    def should_capture_tool_payload(self) -> bool:
        """Check if tool payloads should be captured."""
        return self.enabled and self.capture_tool_payloads


@dataclass
class RetentionPolicy:
    """Retention policy for a specific data type.

    Defines how long data should be retained before cleanup.
    """

    # Data type this policy applies to
    data_type: str

    # Retention period in days (None = keep forever)
    retention_days: int | None = None

    # Whether to archive before deletion
    archive_before_delete: bool = False

    # Batch size for cleanup operations
    cleanup_batch_size: int = 1000

    # Minimum age for cleanup (prevents recent data deletion)
    min_age_days: int = 1

    def get_cutoff_date(self) -> datetime | None:
        """Calculate the cutoff date for this retention policy.

        Returns:
            Datetime cutoff, or None if no retention limit.
        """
        if self.retention_days is None:
            return None
        return datetime.now(UTC) - timedelta(days=self.retention_days)

    def is_eligible_for_cleanup(self, created_at: datetime) -> bool:
        """Check if a record is eligible for cleanup.

        Args:
            created_at: Record creation timestamp.

        Returns:
            True if record should be cleaned up.
        """
        cutoff = self.get_cutoff_date()
        if cutoff is None:
            return False

        # Record must be older than cutoff
        if created_at > cutoff:
            return False

        # Record must be at least min_age_days old
        min_age_cutoff = datetime.now(UTC) - timedelta(days=self.min_age_days)
        return created_at <= min_age_cutoff


@dataclass
class RetentionSettings:
    """Global retention settings for all data types."""

    # Raw LiteLLM ingestion records
    raw_ingestion: RetentionPolicy = field(
        default_factory=lambda: RetentionPolicy(
            data_type="raw_ingestion",
            retention_days=7,
            cleanup_batch_size=1000,
        )
    )

    # Normalized request rows
    normalized_requests: RetentionPolicy = field(
        default_factory=lambda: RetentionPolicy(
            data_type="normalized_requests",
            retention_days=30,
            cleanup_batch_size=500,
        )
    )

    # Session records
    sessions: RetentionPolicy = field(
        default_factory=lambda: RetentionPolicy(
            data_type="sessions",
            retention_days=90,
            cleanup_batch_size=100,
        )
    )

    # Session credentials
    session_credentials: RetentionPolicy = field(
        default_factory=lambda: RetentionPolicy(
            data_type="session_credentials",
            retention_days=1,  # Short TTL for credentials
            min_age_days=0,  # Can cleanup immediately after expiration
        )
    )

    # Exported artifacts
    artifacts: RetentionPolicy = field(
        default_factory=lambda: RetentionPolicy(
            data_type="artifacts",
            retention_days=30,
            archive_before_delete=True,
            cleanup_batch_size=100,
        )
    )

    # Metric rollups
    metric_rollups: RetentionPolicy = field(
        default_factory=lambda: RetentionPolicy(
            data_type="metric_rollups",
            retention_days=90,
            cleanup_batch_size=1000,
        )
    )

    def get_policy(self, data_type: str) -> RetentionPolicy | None:
        """Get retention policy for a specific data type.

        Args:
            data_type: Data type identifier.

        Returns:
            Retention policy or None if not defined.
        """
        policy_map = {
            "raw_ingestion": self.raw_ingestion,
            "normalized_requests": self.normalized_requests,
            "sessions": self.sessions,
            "session_credentials": self.session_credentials,
            "artifacts": self.artifacts,
            "metric_rollups": self.metric_rollups,
        }
        return policy_map.get(data_type)


# Global default instances
DEFAULT_REDACTION_CONFIG = RedactionConfig()
DEFAULT_CONTENT_CAPTURE_CONFIG = ContentCaptureConfig()
DEFAULT_RETENTION_SETTINGS = RetentionSettings()


def get_redaction_filter(config: RedactionConfig | None = None) -> RedactionFilter:
    """Get a redaction filter instance.

    Args:
        config: Optional redaction config. Uses defaults if not provided.

    Returns:
        Configured RedactionFilter instance.
    """
    return RedactionFilter(config or DEFAULT_REDACTION_CONFIG)


def redact_for_logging(data: Any) -> Any:
    """Convenience function to redact data for logging.

    Args:
        data: Data to redact.

    Returns:
        Redacted data safe for logging.
    """
    return get_redaction_filter().redact_any(data)


def should_capture_content(content_type: str, config: ContentCaptureConfig | None = None) -> bool:
    """Check if a specific content type should be captured.

    Args:
        content_type: Type of content (prompt, response, tool_payload).
        config: Optional content capture config.

    Returns:
        True if content should be captured.
    """
    cfg = config or DEFAULT_CONTENT_CAPTURE_CONFIG

    if not cfg.enabled:
        return False

    type_map = {
        "prompt": cfg.should_capture_prompt(),
        "response": cfg.should_capture_response(),
        "tool_payload": cfg.should_capture_tool_payload(),
    }
    return type_map.get(content_type, False)
