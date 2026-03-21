"""Shared pytest fixtures and configuration."""

import os
from pathlib import Path

import pytest


@pytest.fixture
def test_data_dir() -> Path:
    """Return path to test data directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def synthetic_secrets() -> dict[str, str]:
    """Provide synthetic secrets for testing redaction.

    These are FAKE secrets for testing purposes only.
    NEVER use real credentials in tests.
    """
    return {
        "openai_api_key": "sk-test1234567890abcdefghijklmnopqrstuvwxyz1234567890",
        "anthropic_api_key": "sk-ant-api03-test1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ12345678901234567890",
        "bearer_token": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test",
        "jwt": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
        "aws_access_key": "AKIAIOSFODNN7EXAMPLE",
        "connection_string": "postgresql://user:secretpassword123@localhost:5432/mydb",
    }


@pytest.fixture
def env_clean(monkeypatch: pytest.MonkeyPatch) -> None:
    """Clean environment of StackPerf-related variables."""
    for key in list(os.environ.keys()):
        if key.startswith(("STACKPERF_", "LITELLM_", "DATABASE_URL")):
            monkeypatch.delenv(key, raising=False)
