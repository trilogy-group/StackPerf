"""Session service for managing benchmark session lifecycle."""
from datetime import UTC, datetime
from uuid import UUID

from benchmark_core.models import Session
from benchmark_core.repositories import SessionRepository


class SessionService:
    """Service for managing benchmark session lifecycle."""

    def __init__(self, repository: SessionRepository) -> None:
        self._repository = repository

    async def create_session(
        self,
        experiment_id: str,
        variant_id: str,
        task_card_id: str,
        harness_profile: str,
        repo_path: str,
        git_branch: str,
        git_commit: str,
        git_dirty: bool = False,
        operator_label: str | None = None,
    ) -> Session:
        """Create a new benchmark session record."""
        session = Session(
            experiment_id=experiment_id,
            variant_id=variant_id,
            task_card_id=task_card_id,
            harness_profile=harness_profile,
            repo_path=repo_path,
            git_branch=git_branch,
            git_commit=git_commit,
            git_dirty=git_dirty,
            operator_label=operator_label,
        )
        return await self._repository.create(session)

    async def get_session(self, session_id: UUID) -> Session | None:
        """Retrieve a session by ID."""
        return await self._repository.get_by_id(session_id)

    async def finalize_session(
        self,
        session_id: UUID,
        status: str = "completed",
        ended_at: datetime | None = None,
    ) -> Session | None:
        """Finalize a session with end time and status.

        Args:
            session_id: UUID of the session to finalize.
            status: Final status (completed, failed, cancelled).
            ended_at: Optional end timestamp. Defaults to current UTC time.

        Returns:
            Updated session or None if not found.
        """
        if ended_at is None:
            ended_at = datetime.now(UTC)

        session = await self._repository.get_by_id(session_id)
        if session is None:
            return None

        updated = session.model_copy(update={"ended_at": ended_at, "status": status})
        return await self._repository.update(updated)
