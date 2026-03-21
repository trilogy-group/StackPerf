"""Git metadata capture service."""

import subprocess
from pathlib import Path

from benchmark_core.models import GitMetadata


class GitMetadataError(Exception):
    """Error capturing git metadata."""


def capture_git_metadata(repo_path: Path | str | None = None) -> GitMetadata | None:
    """Capture git metadata from the current repository.

    Args:
        repo_path: Path to repository root. If None, uses current directory.

    Returns:
        GitMetadata if in a git repo, None otherwise.
    """
    start_path = Path(repo_path) if repo_path else Path.cwd()

    try:
        # Find repository root
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=start_path,
            capture_output=True,
            text=True,
            check=True,
        )
        repo_root = result.stdout.strip()

        # Get branch
        branch_result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
        )
        branch = branch_result.stdout.strip()

        # Get commit SHA
        sha_result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
        )
        commit_sha = sha_result.stdout.strip()

        # Check dirty state
        status_result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
        )
        dirty = bool(status_result.stdout.strip())

        # Get commit message (first line)
        msg_result = subprocess.run(
            ["git", "log", "-1", "--format=%s"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
        )
        commit_message = msg_result.stdout.strip()

        return GitMetadata(
            repo_root=repo_root,
            branch=branch,
            commit_sha=commit_sha,
            dirty=dirty,
            commit_message=commit_message,
        )

    except subprocess.CalledProcessError as e:
        raise GitMetadataError(f"Failed to capture git metadata: {e.stderr}") from e
    except FileNotFoundError:
        # Not in a git repository
        return None
