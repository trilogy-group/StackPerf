"""Pytest configuration for tests."""

import sys
from pathlib import Path

import pytest

# Add src to Python path for imports
SRC_DIR = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(SRC_DIR))


@pytest.fixture
def synthetic_secrets() -> dict[str, str]:
    """Provide synthetic secrets for testing redaction patterns.

    These are generated fake secrets that match real API key formats
    but are not actual production credentials.
    """
    return {
        "openai_api_key": "sk-test1234567890123456789012345678901234567890",
        # Anthropic key requires 80+ chars after sk-ant-api03-
        "anthropic_api_key": "sk-ant-api03-test1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ12345678901234567890",
        "bearer_token": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test12345.test67890",
        "jwt": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk",
        "aws_access_key": "AKIAIOSFODNN7EXAMPLE",
        "connection_string": "postgresql://user:secretpassword123@localhost:5432/db",
    }
