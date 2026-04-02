"""Redaction utilities for protecting secrets in logs and exports.

This module provides redaction functions to ensure secrets are never
leaked in logs, exports, or error messages.
"""

import re
from dataclasses import dataclass, field
from typing import Any, Final


@dataclass
class RedactionConfig:
    """Configuration for redaction behavior.

    Default configuration enforces redaction of common secret patterns.
    """

    enabled: bool = True
    placeholder: str = "[REDACTED]"
    # Additional patterns to redact beyond built-in secrets
    custom_patterns: list[re.Pattern[str]] = field(default_factory=list)
    # Keys that should be redacted even if they don't match secret patterns
    sensitive_keys: set[str] = field(
        default_factory=lambda: {
            "api_key",
            "apikey",
            "key",
            "token",
            "secret",
            "password",
            "passwd",
            "credential",
            "auth",
            "authorization",
            "bearer",
            "private_key",
            "access_token",
            "refresh_token",
            "session_key",
            "litellm_key",
            "virtual_key",
        }
    )


# Built-in patterns for common secret formats
# These patterns are designed to catch common secret formats
# while avoiding false positives on non-secret data
REDACTION_PATTERNS: Final[list[tuple[str, re.Pattern[str]]]] = [
    # OpenAI-style API keys: sk-... (48+ chars after sk-)
    ("openai_api_key", re.compile(r"sk-[a-zA-Z0-9]{20,}")),
    # Anthropic API keys: sk-ant-...
    ("anthropic_api_key", re.compile(r"sk-ant-api03-[a-zA-Z0-9\-]{80,}")),
    # Generic Bearer tokens
    ("bearer_token", re.compile(r"Bearer\s+[a-zA-Z0-9\-._~+/]+=*", re.IGNORECASE)),
    # JWT tokens (three base64 parts separated by dots)
    (
        "jwt_token",
        re.compile(r"eyJ[a-zA-Z0-9\-._~+/]+\.eyJ[a-zA-Z0-9\-._~+/]+\.[a-zA-Z0-9\-._~+/]+=*"),
    ),
    # AWS-style access keys
    (
        "aws_access_key",
        re.compile(r"(?:A3T[A-Z0-9]|AKIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16}"),
    ),
    # Generic API key: hex-encoded secrets (32+ hex chars)
    ("hex_secret", re.compile(r"\b[a-f0-9]{32,}\b", re.IGNORECASE)),
    # Generic API key: base64-like strings with mixed case and digits
    ("base64_like_secret", re.compile(r"\b[A-Za-z0-9+/]{32,}={0,2}\b")),
    # Connection strings with passwords
    (
        "connection_string",
        re.compile(r"(?:postgresql|postgres|mysql|redis|mongodb)://[^:]+:([^@]+)@"),
    ),
    # LiteLLM master key pattern
    ("litellm_key", re.compile(r"sk-[a-zA-Z0-9]{32,}")),
    # GitHub Personal Access Tokens (classic and fine-grained)
    ("github_pat", re.compile(r"ghp_[a-zA-Z0-9]{36}")),
    ("github_fine_grained_pat", re.compile(r"github_pat_[a-zA-Z0-9]{22}_[a-zA-Z0-9]{59}")),
    ("github_oauth_token", re.compile(r"gho_[a-zA-Z0-9]{36}")),
    ("github_app_token", re.compile(r"ghu_[a-zA-Z0-9]{36}")),
    # Stripe API keys
    ("stripe_key", re.compile(r"sk_live_[a-zA-Z0-9]{24,}")),
    ("stripe_test_key", re.compile(r"sk_test_[a-zA-Z0-9]{24,}")),
    # Generic API key pattern: <key_name>=<long_string>
    (
        "generic_key_assignment",
        re.compile(r"(api_key|apikey|token|secret|password)\s*[=:]\s*[a-zA-Z0-9_\-]{20,}"),
    ),
    # Private key markers
    ("private_key", re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----")),
    # Base64 encoded secrets (long sequences)
    (
        "base64_secret",
        re.compile(r"(?:[A-Za-z0-9+/]{4}){20,}(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?"),
    ),
]


def redact_string(value: str, config: RedactionConfig | None = None) -> str:
    """Redact secrets in a string.

    Args:
        value: String to redact.
        config: Redaction configuration.

    Returns:
        String with secrets replaced by placeholder.
    """
    if not value:
        return value

    cfg = config or RedactionConfig()
    if not cfg.enabled:
        return value

    result = value

    # Apply built-in patterns
    for _pattern_name, pattern in REDACTION_PATTERNS:
        result = pattern.sub(cfg.placeholder, result)

    # Apply custom patterns
    for pattern in cfg.custom_patterns:
        result = pattern.sub(cfg.placeholder, result)

    return result


def redact_value(
    value: Any,
    key: str | None = None,
    config: RedactionConfig | None = None,
) -> Any:
    """Redact a value, handling both strings and nested structures.

    Args:
        value: Value to potentially redact.
        key: Key associated with this value (for sensitive key detection).
        config: Redaction configuration.

    Returns:
        Redacted value or original if not a secret.
    """
    cfg = config or RedactionConfig()

    if not cfg.enabled:
        return value

    # Handle strings
    if isinstance(value, str):
        # Check if key indicates sensitive data
        if key and key.lower() in cfg.sensitive_keys:
            return cfg.placeholder
        return redact_string(value, cfg)

    # Handle dicts recursively
    if isinstance(value, dict):
        return redact_dict(value, cfg)

    # Handle lists/tuples
    if isinstance(value, (list, tuple)):
        redacted = [redact_value(item, None, cfg) for item in value]
        return tuple(redacted) if isinstance(value, tuple) else redacted

    # Non-sensitive types pass through
    return value


def redact_dict(
    data: dict[str, Any],
    config: RedactionConfig | None = None,
) -> dict[str, Any]:
    """Redact sensitive values in a dictionary.

    Args:
        data: Dictionary to redact.
        config: Redaction configuration.

    Returns:
        New dictionary with sensitive values redacted.
    """
    cfg = config or RedactionConfig()

    if not cfg.enabled:
        return data.copy()

    result: dict[str, Any] = {}

    for key, value in data.items():
        # Check if key itself indicates sensitive data
        key_lower = key.lower()
        # Check if key is a sensitive key or if key name itself matches secret patterns
        if key_lower in cfg.sensitive_keys or _is_key_patterned_secret(key, cfg):
            result[key] = cfg.placeholder
        else:
            result[key] = redact_value(value, key, cfg)

    return result


def _is_key_patterned_secret(key: str, config: RedactionConfig) -> bool:
    """Check if a key name itself appears to contain a secret value.

    This catches keys like "api_key_sk-abc123" or "token_eyJxxxxx" where
    the key name suffix/prefix contains what looks like a secret.

    Args:
        key: The dictionary key to check.
        config: Redaction configuration.

    Returns:
        True if the key appears to contain a secret pattern.
    """
    # Check if key contains any secret patterns (like sk-, eyJ for JWT, etc.)
    for pattern_name, pattern in REDACTION_PATTERNS:
        # Skip overly generic patterns that would match normal identifiers
        if pattern_name in ("hex_secret", "base64_like_secret", "base64_secret"):
            continue
        if pattern.search(key):
            return True

    # Check for common secret-containing key suffixes
    secret_indicators = [
        "_key_",
        "_token_",
        "_secret_",
        "_password_",
        "_credential_",
        "sk-",
        "eyJ",  # JWT prefix
    ]
    key_lower = key.lower()
    for indicator in secret_indicators:
        if indicator in key_lower:
            # Check if what follows looks like a secret value
            parts = key_lower.split(indicator)
            if len(parts) > 1 and parts[-1]:
                # The part after the indicator looks like a secret fragment
                suffix = parts[-1]
                if len(suffix) >= 8 and suffix.isalnum():
                    return True

    return False
