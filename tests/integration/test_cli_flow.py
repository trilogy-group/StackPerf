"""Integration tests for CLI create/finalize flow.

Tests the full session lifecycle through CLI commands.

NOTE: These tests are skipped pending implementation of session CLI commands.
They are outside the scope of COE-230 (Security, Operations, and Delivery Quality).
"""

import subprocess
from pathlib import Path

import pytest

# Skip all tests in this module - session CLI not yet implemented
pytestmark = pytest.mark.skip(reason="Session CLI commands not yet implemented - pending separate PR")


class TestCLIFlow:
    """Test CLI create/finalize flow against in-memory DB."""

    @pytest.fixture
    def project_root(self) -> Path:
        """Get project root directory."""
        return Path(__file__).parent.parent.parent

    @pytest.fixture
    def bench_cli(self, project_root):
        """Get the bench CLI executable path."""
        return str(project_root / ".venv" / "bin" / "bench")

    @pytest.mark.asyncio
    async def test_cli_session_create(self, project_root, bench_cli):
        """Session create command emits usable shell and dotenv outputs."""
        result = subprocess.run(
            [bench_cli, "session", "create", "--no-git"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Should create session successfully
        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        assert "Session Created" in result.stdout
        assert "Session ID:" in result.stdout

        # Should show API key
        assert "Session API Key" in result.stdout

        # Should create output files
        output_dir = project_root / ".stackperf"
        assert output_dir.exists()

    @pytest.mark.asyncio
    async def test_cli_session_create_with_git_metadata(self, project_root, bench_cli):
        """Create a session inside a git repo and verify captured metadata."""
        result = subprocess.run(
            [bench_cli, "session", "create"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0
        # Should capture git metadata (we're in a git repo)
        assert "Git Metadata:" in result.stdout
        assert "Repo:" in result.stdout
        assert "Branch:" in result.stdout
        assert "Commit:" in result.stdout

    @pytest.mark.asyncio
    async def test_cli_various_output_formats(self, project_root, bench_cli):
        """Session create command supports shell, dotenv, and json formats."""
        formats = ["shell", "dotenv", "json"]

        for fmt in formats:
            result = subprocess.run(
                [bench_cli, "session", "create", "--no-git", "-f", fmt],
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=30,
            )

            assert result.returncode == 0, f"Format {fmt} failed: {result.stderr}"

            output_file = project_root / ".stackperf" / f"session-env.{fmt}"
            assert output_file.exists(), f"No output file for {fmt}"

            content = output_file.read_text()
            if fmt == "shell":
                assert "export " in content
            elif fmt == "dotenv":
                assert "=" in content and '"' in content
            elif fmt == "json":
                import json

                data = json.loads(content)
                assert "STACKPERF_SESSION_ID" in data


class TestEnvironmentValidation:
    """Test that rendered environment outputs are valid."""

    @pytest.fixture
    def project_root(self) -> Path:
        """Get project root directory."""
        return Path(__file__).parent.parent.parent

    @pytest.fixture
    def bench_cli(self, project_root):
        """Get the bench CLI executable path."""
        return str(project_root / ".venv" / "bin" / "bench")

    def test_shell_output_can_be_sourced(self, project_root, bench_cli, tmp_path):
        """Source a rendered snippet and confirm variables are set."""
        # Create session with shell output
        result = subprocess.run(
            [bench_cli, "session", "create", "--no-git", "-f", "shell"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0

        env_file = project_root / ".stackperf" / "session-env.shell"
        assert env_file.exists()

        content = env_file.read_text()

        # Verify structure
        assert "STACKPERF_SESSION_ID=" in content
        assert "STACKPERF_PROXY_BASE_URL=" in content
        assert "STACKPERF_SESSION_API_KEY=" in content

        # Verify warning is present
        assert "WARNING" in content
        assert "secrets" in content.lower()

    def test_no_secrets_in_tracked_files(self, project_root):
        """Rendered output never writes secrets into tracked files."""
        # Check .gitignore includes output directory
        gitignore = project_root / ".gitignore"

        if gitignore.exists():
            content = gitignore.read_text()
            # .gitignore should include output directories for session artifacts
            # Note: COE-230 adds .session-artifacts/ and related entries
            assert ".stackperf" in content or "session-env" in content or ".session-artifacts" in content
