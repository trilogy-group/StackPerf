"""Core configuration constants and settings.

This module defines default-off content capture and security settings
as required by the security architecture.
"""

from enum import Enum
from typing import Final


class ContentCapturePolicy(str, Enum):
    """Policy for capturing prompt and response content.

    By default, content capture is DISABLED to protect sensitive data
    and comply with security requirements.
    """

    DISABLED = "disabled"  # Default: no content stored
    METADATA_ONLY = "metadata_only"  # Only metrics and IDs
    REDACTED = "redacted"  # Content stored with sensitive data redacted
    FULL = "full"  # Full content stored (requires explicit opt-in)


class SecretHandling(str, Enum):
    """Policy for handling secrets in logs and exports."""

    REDACT = "redact"  # Default: replace secrets with placeholder
    HASH = "hash"  # Hash secrets for correlation
    MASK = "mask"  # Partially mask secrets for debugging


# Default content capture policy - disabled by default
DEFAULT_CONTENT_CAPTURE_POLICY: Final[ContentCapturePolicy] = ContentCapturePolicy.DISABLED

# Default secret handling - redact by default
DEFAULT_SECRET_HANDLING: Final[SecretHandling] = SecretHandling.REDACT

# Secrets placeholder for redacted values
SECRET_REDACTED_PLACEHOLDER: Final[str] = "[REDACTED]"

# Minimum session credential TTL in seconds
MIN_SESSION_CREDENTIAL_TTL_SECONDS: Final[int] = 3600  # 1 hour

# Maximum session credential TTL in seconds
MAX_SESSION_CREDENTIAL_TTL_SECONDS: Final[int] = 86400  # 24 hours

# Default retention window in days for different data types
DEFAULT_RETENTION_DAYS: Final[dict[str, int]] = {
    "raw_ingestion": 7,  # Raw LiteLLM records: 1 week
    "normalized_requests": 30,  # Normalized request rows: 1 month
    "session_credentials": 1,  # Session credentials expire quickly
    "artifacts": 90,  # Exported artifacts: 3 months
    "rollups": 365,  # Metric rollups: 1 year
}


def is_content_capture_enabled(policy: ContentCapturePolicy | None = None) -> bool:
    """Check if content capture is enabled.

    Args:
        policy: Content capture policy, defaults to system default.

    Returns:
        True if any content capture is enabled beyond metadata only.
    """
    effective_policy = policy or DEFAULT_CONTENT_CAPTURE_POLICY
    return effective_policy in (
        ContentCapturePolicy.REDACTED,
        ContentCapturePolicy.FULL,
    )


def should_store_prompts(policy: ContentCapturePolicy | None = None) -> bool:
    """Check if prompt content should be persisted.

    By default, prompts are NOT persisted.

    Args:
        policy: Content capture policy, defaults to system default.

    Returns:
        True only if explicitly opted into full content capture.
    """
    effective_policy = policy or DEFAULT_CONTENT_CAPTURE_POLICY
    return effective_policy == ContentCapturePolicy.FULL


def should_store_responses(policy: ContentCapturePolicy | None = None) -> bool:
    """Check if response content should be persisted.

    By default, responses are NOT persisted.

    Args:
        policy: Content capture policy, defaults to system default.

    Returns:
        True only if explicitly opted into full content capture.
    """
    effective_policy = policy or DEFAULT_CONTENT_CAPTURE_POLICY
    return effective_policy == ContentCapturePolicy.FULL
