"""Pytest configuration and fixtures."""

import pytest


@pytest.fixture
def test_settings():
    """Provide test settings with safe defaults."""
    from benchmark_core.config import Settings
    return Settings(
        litellm_base_url="http://localhost:4000",
        database_url="postgresql+asyncpg://test:test@localhost:5432/test_stackperf",
        capture_content=False,
    )
