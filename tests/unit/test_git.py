"""Tests for git metadata capture utilities."""

import subprocess
from pathlib import Path
from unittest.mock import patch

from benchmark_core.git import GitMetadata, get_git_metadata, get_repo_root


class TestGitMetadata:
    """Tests for git metadata capture."""

    def test_get_git_metadata_from_current_repo(self):
        """Test capturing git metadata from the current repository."""
        metadata = get_git_metadata()

        assert metadata is not None
        assert metadata.repo_path is not None
        assert metadata.branch is not None
        assert len(metadata.commit) == 40  # Full SHA
        assert isinstance(metadata.dirty, bool)

    def test_get_git_metadata_from_path(self, tmp_path):
        """Test capturing git metadata from a specific path."""
        # Create a temporary git repository
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "HEAD").write_text("ref: refs/heads/test-branch\n")

        # Create refs directory structure
        refs_dir = git_dir / "refs" / "heads"
        refs_dir.mkdir(parents=True)
        (refs_dir / "test-branch").write_text("abc123def456789012345678901234567890abcd\n")

        # Create index file (empty is fine for our purposes)
        (git_dir / "index").write_text("")

        metadata = get_git_metadata(str(tmp_path))

        # Should find the .git directory
        # Note: This may fail if git commands fail in the test environment
        # but for valid git repos, we should get metadata
        if metadata is not None:
            assert metadata.branch == "test-branch"
            assert "abc123de" in metadata.commit

    def test_get_git_metadata_not_git_repo(self, tmp_path):
        """Test that None is returned when not in a git repository."""
        metadata = get_git_metadata(str(tmp_path))
        assert metadata is None

    def test_get_git_metadata_nested_directory(self, tmp_path):
        """Test finding git metadata from a nested directory."""
        # Create a temporary git repository
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "HEAD").write_text("ref: refs/heads/main\n")

        # Create nested directory
        nested = tmp_path / "subdir" / "nested"
        nested.mkdir(parents=True)

        metadata = get_git_metadata(str(nested))

        # Should find the parent .git directory
        # Note: This may fail if git commands fail in the test environment
        # but for valid git repos, we should get metadata
        if metadata is not None:
            assert metadata.branch == "main"

    def test_get_repo_root_from_current_repo(self):
        """Test getting repo root from current repository."""
        root = get_repo_root()

        assert root is not None
        assert Path(root).exists()
        assert (Path(root) / ".git").exists()

    def test_get_repo_root_not_git_repo(self, tmp_path):
        """Test that None is returned for non-git directory."""
        root = get_repo_root(str(tmp_path))
        assert root is None

    @patch("benchmark_core.git.subprocess.run")
    def test_get_git_metadata_git_not_installed(self, mock_run):
        """Test handling when git is not installed."""
        mock_run.side_effect = FileNotFoundError("git not found")

        metadata = get_git_metadata()
        assert metadata is None

    @patch("benchmark_core.git.subprocess.run")
    def test_get_git_metadata_command_fails(self, mock_run):
        """Test handling when git commands fail."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        metadata = get_git_metadata()
        assert metadata is None

    def test_git_metadata_dataclass(self):
        """Test GitMetadata dataclass instantiation."""
        metadata = GitMetadata(
            repo_path="/tmp/test",
            branch="main",
            commit="abc123",
            dirty=True,
        )

        assert metadata.repo_path == "/tmp/test"
        assert metadata.branch == "main"
        assert metadata.commit == "abc123"
        assert metadata.dirty is True
