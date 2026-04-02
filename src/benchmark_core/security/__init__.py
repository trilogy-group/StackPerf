"""Security utilities for redaction, secret handling, and audit controls.

This package provides security utilities for redaction, secret detection,
content capture, and retention management.
"""

# Package submodule exports (standard interface)
from .redaction import (
    REDACTION_PATTERNS,
    RedactionConfig,
    redact_dict,
    redact_string,
    redact_value,
)
from .secrets import (
    SecretDetector,
    detect_secrets,
    is_likely_secret,
    scan_dict_for_secrets,
)

# Legacy security.py module exports (for backward compatibility with existing code)
# Import directly from module file to avoid circular import
import importlib.util
import sys
from pathlib import Path

_security_spec = importlib.util.spec_from_file_location(
    "_legacy_security", str(Path(__file__).parent.parent / "security.py")
)
_legacy_security = importlib.util.module_from_spec(_security_spec)
sys.modules["_legacy_security"] = _legacy_security
_security_spec.loader.exec_module(_legacy_security)

# Re-export legacy module classes (do NOT override package classes)
ContentCaptureConfig = _legacy_security.ContentCaptureConfig
DEFAULT_CONTENT_CAPTURE_CONFIG = _legacy_security.DEFAULT_CONTENT_CAPTURE_CONFIG
DEFAULT_REDACTION_CONFIG = _legacy_security.DEFAULT_REDACTION_CONFIG
DEFAULT_RETENTION_SETTINGS = _legacy_security.DEFAULT_RETENTION_SETTINGS
RedactionFilter = _legacy_security.RedactionFilter
RetentionPolicy = _legacy_security.RetentionPolicy
RetentionSettings = _legacy_security.RetentionSettings
SecretPattern = _legacy_security.SecretPattern
get_redaction_filter = _legacy_security.get_redaction_filter
redact_for_logging = _legacy_security.redact_for_logging
should_capture_content = _legacy_security.should_capture_content

__all__ = [
    # Package exports (primary interface)
    "REDACTION_PATTERNS",
    "RedactionConfig",
    "redact_dict",
    "redact_string",
    "redact_value",
    "SecretDetector",
    "detect_secrets",
    "is_likely_secret",
    "scan_dict_for_secrets",
    # Legacy module exports (backward compatibility)
    "ContentCaptureConfig",
    "DEFAULT_CONTENT_CAPTURE_CONFIG",
    "DEFAULT_REDACTION_CONFIG",
    "DEFAULT_RETENTION_SETTINGS",
    "RedactionFilter",
    "RetentionPolicy",
    "RetentionSettings",
    "SecretPattern",
    "get_redaction_filter",
    "redact_for_logging",
    "should_capture_content",
]
