"""Git metadata capture utilities for benchmark sessions."""

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class GitMetadata:
    """Git metadata captured from a repository."""

    repo_path: str
    branch: str
    commit: str
    dirty: bool


def get_git_metadata(repo_path: str | None = None) -> GitMetadata | None:
    """Capture git metadata from a repository.

    Args:
        repo_path: Path to git repository. If None, uses current directory.

    Returns:
        GitMetadata object or None if not in a git repository.
    """
    if repo_path is None:
        repo_path = os.getcwd()

    repo_path = Path(repo_path).resolve()

    # Check if this is a git repository
    git_dir = repo_path / ".git"
    if not git_dir.exists():
        # Try to find .git in parent directories
        current = repo_path
        while current != current.parent:
            if (current / ".git").exists():
                repo_path = current
                break
            current = current.parent
        else:
            return None

    try:
        # Get branch name
        branch_result = subprocess.run(
            ["git", "-C", str(repo_path), "branch", "--show-current"],
            capture_output=True,
            text=True,
            check=True,
        )
        branch = branch_result.stdout.strip()

        # Get commit SHA
        commit_result = subprocess.run(
            ["git", "-C", str(repo_path), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        commit = commit_result.stdout.strip()

        # Check for dirty state
        status_result = subprocess.run(
            ["git", "-C", str(repo_path), "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=True,
        )
        dirty = len(status_result.stdout.strip()) > 0

        return GitMetadata(
            repo_path=str(repo_path),
            branch=branch,
            commit=commit,
            dirty=dirty,
        )
    except subprocess.CalledProcessError:
        return None
    except FileNotFoundError:
        # Git not installed
        return None


def get_repo_root(repo_path: str | None = None) -> str | None:
    """Get the root path of a git repository.

    Args:
        repo_path: Path within a git repository. If None, uses current directory.

    Returns:
        Absolute path to repository root or None if not in a git repository.
    """
    if repo_path is None:
        repo_path = os.getcwd()

    try:
        result = subprocess.run(
            ["git", "-C", str(repo_path), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None
    except FileNotFoundError:
        return None
