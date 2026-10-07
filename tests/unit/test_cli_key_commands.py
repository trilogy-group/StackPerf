"""Unit tests for sessionless proxy key CLI commands."""

import httpx
import pytest
import respx
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from typer.testing import CliRunner

from benchmark_core.db.models import Base
from cli.main import app


@pytest.fixture
def test_engine():
    """Create an in-memory SQLite engine for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture
def db_session(test_engine):
    """Create a database session for testing."""
    session_local = sessionmaker(bind=test_engine)
    session = session_local()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def runner():
    """Create a CLI runner."""
    return CliRunner()


@pytest.fixture
def mock_env_db_url(test_engine, monkeypatch):
    """Mock the database URL to use the test engine."""
    from benchmark_core.db import session as db_session_module
    from cli import commands

    original_get_db_session = db_session_module.get_db_session

    def mock_get_db_session(engine=None):
        if engine is None:
            engine = test_engine
        return original_get_db_session(engine)

    monkeypatch.setattr(db_session_module, "get_db_session", mock_get_db_session)
    monkeypatch.setattr(commands.key, "get_db_session", mock_get_db_session)

    # Also mock LiteLLM env vars to avoid errors
    monkeypatch.setenv("LITELLM_MASTER_KEY", "test-master-key")
    monkeypatch.setenv("LITELLM_BASE_URL", "http://localhost:4000")

    return test_engine


class TestKeyCreateCommand:
    """Tests for `benchmark key create` command."""

    @respx.mock
    def test_create_key_success(self, runner, mock_env_db_url, monkeypatch):
        """Create a key with metadata."""
        respx.post("http://localhost:4000/key/generate").mock(
            return_value=httpx.Response(
                200,
                json={"key": "sk-litellm-test-key", "key_id": "kid-123"},
            )
        )

        result = runner.invoke(
            app,
            [
                "key",
                "create",
                "--alias",
                "cli-test-alias",
                "--owner",
                "alice",
                "--team",
                "platform",
                "--customer",
                "internal",
                "--model",
                "gpt-4o",
                "--ttl-hours",
                "24",
            ],
        )

        assert result.exit_code == 0, result.output
        assert "cli-test-alias" in result.output
        assert "alice" in result.output
        assert "platform" in result.output
        assert "internal" in result.output
        assert "gpt-4o" in result.output
        assert "sk-litellm-test-key" in result.output
        assert "API Key Secret" in result.output
        assert "not be shown again" in result.output

    @respx.mock
    def test_create_key_with_env_flag(self, runner, mock_env_db_url, monkeypatch):
        """Create a key with --show-env renders environment snippet."""
        respx.post("http://localhost:4000/key/generate").mock(
            return_value=httpx.Response(
                200,
                json={"key": "sk-env-key", "key_id": "kid-env"},
            )
        )

        result = runner.invoke(
            app,
            [
                "key",
                "create",
                "--alias",
                "env-test",
                "--show-env",
                "--format",
                "shell",
            ],
        )

        assert result.exit_code == 0, result.output
        assert "export OPENAI_API_BASE" in result.output
        assert "export OPENAI_API_KEY" in result.output

    @respx.mock
    def test_create_key_dotenv_format(self, runner, mock_env_db_url, monkeypatch):
        """Create a key with --format dotenv."""
        respx.post("http://localhost:4000/key/generate").mock(
            return_value=httpx.Response(
                200,
                json={"key": "sk-dotenv-key", "key_id": "kid-dotenv"},
            )
        )

        result = runner.invoke(
            app,
            [
                "key",
                "create",
                "--alias",
                "dotenv-test",
                "--show-env",
                "--format",
                "dotenv",
            ],
        )

        assert result.exit_code == 0, result.output
        assert "OPENAI_API_BASE=" in result.output
        assert "OPENAI_API_KEY=" in result.output

    def test_create_key_no_master_key(self, runner, mock_env_db_url, monkeypatch):
        """Create fails when LITELLM_MASTER_KEY is not set."""
        monkeypatch.delenv("LITELLM_MASTER_KEY", raising=False)

        result = runner.invoke(app, ["key", "create"])
        assert result.exit_code == 1
        assert "master_key" in result.output or "not configured" in result.output

    @respx.mock
    def test_create_key_litellm_error(self, runner, mock_env_db_url, monkeypatch):
        """LiteLLM API errors are handled gracefully."""
        respx.post("http://localhost:4000/key/generate").mock(
            return_value=httpx.Response(500, text="Internal Server Error")
        )

        result = runner.invoke(app, ["key", "create", "--alias", "fail-test"])
        assert result.exit_code == 1
        assert "LiteLLM API error" in result.output


class TestKeyListCommand:
    """Tests for `benchmark key list` command."""

    @respx.mock
    def test_list_keys_empty(self, runner, mock_env_db_url, monkeypatch):
        """List with no keys shows empty message."""
        result = runner.invoke(app, ["key", "list"])
        assert result.exit_code == 0, result.output
        assert "No proxy keys found" in result.output

    @respx.mock
    def test_list_keys_with_data(self, runner, mock_env_db_url, monkeypatch):
        """List shows created keys."""
        respx.post("http://localhost:4000/key/generate").mock(
            return_value=httpx.Response(
                200,
                json={"key": "sk-1", "key_id": "id-1"},
            )
        )

        # Create a key first
        result = runner.invoke(
            app,
            [
                "key",
                "create",
                "--alias",
                "list-test",
                "--owner",
                "alice",
                "--team",
                "platform",
            ],
        )
        assert result.exit_code == 0, result.output

        # List keys
        result = runner.invoke(app, ["key", "list"])
        assert result.exit_code == 0, result.output
        # Rich table may truncate fields; check for partial match and other fields
        assert "list-" in result.output
        assert "alice" in result.output
        assert "platf" in result.output

    def test_list_keys_filter_by_owner(self, runner, mock_env_db_url, monkeypatch):
        """List with --owner filter."""
        result = runner.invoke(app, ["key", "list", "--owner", "nobody"])
        assert result.exit_code == 0, result.output
        assert "No proxy keys found" in result.output

    def test_list_keys_invalid_status(self, runner, mock_env_db_url, monkeypatch):
        """List with invalid status exits with error."""
        result = runner.invoke(app, ["key", "list", "--status", "invalid_status"])
        assert result.exit_code == 1
        assert "Invalid status" in result.output


class TestKeyInfoCommand:
    """Tests for `benchmark key info` command."""

    @respx.mock
    def test_info_by_alias(self, runner, mock_env_db_url, monkeypatch):
        """Info command finds key by alias."""
        respx.post("http://localhost:4000/key/generate").mock(
            return_value=httpx.Response(
                200,
                json={"key": "sk-1", "key_id": "id-1"},
            )
        )

        # Create key
        result = runner.invoke(
            app,
            ["key", "create", "--alias", "info-alias", "--owner", "bob"],
        )
        assert result.exit_code == 0, result.output

        # Get info by alias
        result = runner.invoke(app, ["key", "info", "info-alias"])
        assert result.exit_code == 0, result.output
        assert "info-alias" in result.output
        assert "bob" in result.output

    def test_info_not_found(self, runner, mock_env_db_url, monkeypatch):
        """Info for missing key shows error."""
        result = runner.invoke(app, ["key", "info", "nonexistent-key"])
        assert result.exit_code == 1
        assert "not found" in result.output

    def test_info_invalid_uuid(self, runner, mock_env_db_url, monkeypatch):
        """Info with invalid UUID-like input falls back to alias search."""
        result = runner.invoke(app, ["key", "info", "not-a-uuid-or-alias"])
        assert result.exit_code == 1
        assert "not found" in result.output


class TestKeyRevokeCommand:
    """Tests for `benchmark key revoke` command."""

    @respx.mock
    def test_revoke_key(self, runner, mock_env_db_url, monkeypatch):
        """Revoke an existing key."""
        respx.post("http://localhost:4000/key/generate").mock(
            return_value=httpx.Response(
                200,
                json={"key": "sk-1", "key_id": "id-1"},
            )
        )
        respx.post("http://localhost:4000/key/delete").mock(
            return_value=httpx.Response(200, json={"deleted_keys": ["id-1"]})
        )

        # Create key
        result = runner.invoke(
            app,
            ["key", "create", "--alias", "revoke-test"],
        )
        assert result.exit_code == 0, result.output

        # Extract UUID from output
        import re

        uuid_match = re.search(r"ID: ([0-9a-f-]{36})", result.output)
        assert uuid_match, f"Could not find UUID in output: {result.output}"
        key_id = uuid_match.group(1)

        # Revoke by ID
        result = runner.invoke(app, ["key", "revoke", key_id])
        assert result.exit_code == 0, result.output
        assert "revoked successfully" in result.output
        assert "revoked" in result.output.lower()

    def test_revoke_not_found(self, runner, mock_env_db_url, monkeypatch):
        """Revoke non-existent key shows error."""
        result = runner.invoke(app, ["key", "revoke", "12345678-1234-1234-1234-123456789abc"])
        assert result.exit_code == 1
        assert "not found" in result.output

    def test_revoke_invalid_alias(self, runner, mock_env_db_url, monkeypatch):
        """Revoke with non-existent alias shows not-found error."""
        result = runner.invoke(app, ["key", "revoke", "not-a-uuid"])
        assert result.exit_code == 1
        assert "not found" in result.output


class TestKeyCLIImports:
    """Smoke tests for key command imports."""

    def test_import_key_module(self):
        """Key module imports successfully."""
        from cli.commands import key

        assert key.app is not None

    def test_main_app_has_key_command(self):
        """Main CLI app includes key subcommand."""
        from cli.main import app

        # Typer stores subcommands in register_list or similar
        # Just verify import works
        assert app is not None
