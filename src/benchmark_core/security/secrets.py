"""Secret detection utilities.

This module provides functions to detect potential secrets in data,
enabling proactive warnings before secrets are logged or exported.
"""

import re
from dataclasses import dataclass, field
from typing import Any, Final


@dataclass
class SecretMatch:
    """Represents a detected secret."""

    pattern_name: str
    value: str
    start_pos: int
    end_pos: int
    confidence: float  # 0.0 to 1.0


@dataclass
class SecretDetector:
    """Detector for finding secrets in data.

    Default configuration uses conservative detection to minimize
    false positives while catching common secret formats.
    """

    enabled: bool = True
    min_confidence: float = 0.7
    # Patterns that indicate likely secrets
    patterns: list[tuple[str, re.Pattern[str], float]] = field(
        default_factory=lambda: [
            # (name, pattern, confidence)
            ("openai_key", re.compile(r"sk-[a-zA-Z0-9]{20,}"), 0.9),
            ("anthropic_key", re.compile(r"sk-ant-api03-[a-zA-Z0-9\-]{80,}"), 0.95),
            ("bearer_token", re.compile(r"Bearer\s+[a-zA-Z0-9\-._~+/]+", re.IGNORECASE), 0.85),
            (
                "jwt",
                re.compile(
                    r"eyJ[a-zA-Z0-9\-._~+/]+\.eyJ[a-zA-Z0-9\-._~+/]+\.[a-zA-Z0-9\-._~+/]+=*"
                ),
                0.9,
            ),
            (
                "aws_key",
                re.compile(r"(?:A3T[A-Z0-9]|AKIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16}"),
                0.95,
            ),
            (
                "private_key",
                re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"),
                0.99,
            ),
            (
                "connection_string_password",
                re.compile(r"(?:postgresql|postgres|mysql|redis|mongodb)://[^:]+:([^@]+)@"),
                0.85,
            ),
        ]
    )
    # Keys that commonly contain secrets
    sensitive_key_patterns: list[re.Pattern[str]] = field(
        default_factory=lambda: [
            re.compile(r".*_key$", re.IGNORECASE),
            re.compile(r".*_token$", re.IGNORECASE),
            re.compile(r".*_secret$", re.IGNORECASE),
            re.compile(r"^api[-_]?key$", re.IGNORECASE),
            re.compile(r"^auth", re.IGNORECASE),
            re.compile(r"^password", re.IGNORECASE),
            re.compile(r"^credential", re.IGNORECASE),
            re.compile(r"^private", re.IGNORECASE),
            re.compile(r"^token$", re.IGNORECASE),
        ]
    )


def detect_secrets(
    value: str,
    detector: SecretDetector | None = None,
) -> list[SecretMatch]:
    """Detect potential secrets in a string.

    Args:
        value: String to scan for secrets.
        detector: Secret detector configuration.

    Returns:
        List of detected secret matches.
    """
    if not value:
        return []

    det = detector or SecretDetector()
    if not det.enabled:
        return []

    matches: list[SecretMatch] = []

    for pattern_name, pattern, confidence in det.patterns:
        if confidence < det.min_confidence:
            continue

        for match in pattern.finditer(value):
            matches.append(
                SecretMatch(
                    pattern_name=pattern_name,
                    value=match.group(),
                    start_pos=match.start(),
                    end_pos=match.end(),
                    confidence=confidence,
                )
            )

    return matches


def is_likely_secret(
    value: str,
    key: str | None = None,
    detector: SecretDetector | None = None,
) -> bool:
    """Check if a value appears to be a secret.

    Args:
        value: Value to check.
        key: Key associated with this value (optional).
        detector: Secret detector configuration.

    Returns:
        True if the value appears to be a secret.
    """
    if not value:
        return False

    det = detector or SecretDetector()
    if not det.enabled:
        return False

    # Check key patterns first
    if key:
        for key_pattern in det.sensitive_key_patterns:
            if key_pattern.match(key):
                return True

    # Check value patterns
    matches = detect_secrets(value, det)
    return any(m.confidence >= det.min_confidence for m in matches)


def scan_dict_for_secrets(
    data: dict[str, Any],
    detector: SecretDetector | None = None,
) -> dict[str, list[SecretMatch]]:
    """Scan a dictionary for potential secrets.

    Args:
        data: Dictionary to scan.
        detector: Secret detector configuration.

    Returns:
        Dictionary mapping keys to their detected secrets.
    """
    det = detector or SecretDetector()
    results: dict[str, list[SecretMatch]] = {}

    for key, value in data.items():
        if isinstance(value, str):
            secrets = detect_secrets(value, det)
            if secrets:
                results[key] = secrets
        elif isinstance(value, dict):
            # Recursively scan nested dicts
            nested = scan_dict_for_secrets(value, det)
            for nested_key, nested_secrets in nested.items():
                results[f"{key}.{nested_key}"] = nested_secrets

    return results


# Common secret value patterns for testing
SYNTHETIC_SECRETS: Final[dict[str, str]] = {
    "openai_key": "sk-test1234567890abcdefghijklmnopqrstuvwxyz1234567890",
    "anthropic_key": "sk-ant-api03-test1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ12345678901234567890",
    "bearer_token": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test",
    "jwt": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
    "aws_key": "AKIAIOSFODNN7EXAMPLE",
    "connection_string": "postgresql://user:secretpassword123@localhost:5432/mydb",
}
