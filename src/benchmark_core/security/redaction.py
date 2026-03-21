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
    # Generic secret: long alphanumeric strings that look like keys
    ("generic_secret", re.compile(r"\b[a-zA-Z0-9]{32,}\b")),
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
        if key.lower() in cfg.sensitive_keys:
            result[key] = cfg.placeholder
        else:
            result[key] = redact_value(value, key, cfg)

    return result
