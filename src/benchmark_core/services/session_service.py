"""Service for managing benchmark session lifecycle safely."""

from uuid import UUID

from sqlalchemy.orm import Session as SQLAlchemySession

from benchmark_core.db.models import Session as SessionORM
from benchmark_core.repositories.base import (
    DuplicateIdentifierError,
    ReferentialIntegrityError,
    RepositoryError,
)
from benchmark_core.repositories.session_repository import SQLSessionRepository


class SessionValidationError(Exception):
    """Raised when session validation fails."""

    pass


class SessionService:
    """Service for managing benchmark session lifecycle with safety guarantees.

    This service ensures:
    - Sessions are created with all required metadata before harness traffic starts
    - Duplicate session identifiers are rejected
    - Session finalization is atomic and safe
    - Referential integrity is preserved throughout the lifecycle
    """

    def __init__(
        self,
        db_session: SQLAlchemySession,
        session_repo: SQLSessionRepository | None = None,
    ) -> None:
        """Initialize the session service.

        Args:
            db_session: SQLAlchemy session for database operations.
            session_repo: Optional repository instance. If not provided, one is created.
        """
        self._db_session = db_session
        self._session_repo = session_repo or SQLSessionRepository(db_session)

    async def create_session(
        self,
        experiment_id: UUID,
        variant_id: UUID,
        task_card_id: UUID,
        harness_profile: str,
        repo_path: str,
        git_branch: str,
        git_commit: str,
        git_dirty: bool = False,
        operator_label: str | None = None,
        proxy_credential_id: str | None = None,
    ) -> SessionORM:
        """Create a new benchmark session safely.

        This method ensures:
        1. The session identifier is unique (if operator_label provided)
        2. All referenced entities exist (experiment, variant, task_card)
        3. The session captures all metadata before harness traffic starts
        4. The operation is atomic

        Args:
            experiment_id: The experiment UUID.
            variant_id: The variant UUID.
            task_card_id: The task card UUID.
            harness_profile: The harness profile name.
            repo_path: Absolute path to the repository.
            git_branch: Active git branch.
            git_commit: Commit SHA.
            git_dirty: Whether the working tree is dirty.
            operator_label: Optional operator-provided label (acts as external session ID).
            proxy_credential_id: Optional proxy credential identifier.

        Returns:
            The created session with all metadata populated.

        Raises:
            SessionValidationError: If validation fails (duplicate ID, missing refs).
            RepositoryError: If a database error occurs.
        """
        # Validate required fields
        if not experiment_id:
            raise SessionValidationError("experiment_id is required")
        if not variant_id:
            raise SessionValidationError("variant_id is required")
        if not task_card_id:
            raise SessionValidationError("task_card_id is required")
        if not harness_profile:
            raise SessionValidationError("harness_profile is required")
        if not repo_path:
            raise SessionValidationError("repo_path is required")
        if not git_branch:
            raise SessionValidationError("git_branch is required")
        if not git_commit:
            raise SessionValidationError("git_commit is required")

        # Validate git commit format (should be 7-64 hex chars)
        if len(git_commit) < 7 or len(git_commit) > 64:
            raise SessionValidationError(
                f"git_commit must be between 7 and 64 characters, got {len(git_commit)}"
            )

        try:
            session = await self._session_repo.create_session_safe(
                experiment_id=experiment_id,
                variant_id=variant_id,
                task_card_id=task_card_id,
                harness_profile=harness_profile,
                repo_path=repo_path,
                git_branch=git_branch,
                git_commit=git_commit,
                git_dirty=git_dirty,
                operator_label=operator_label,
                proxy_credential_id=proxy_credential_id,
            )
            return session
        except DuplicateIdentifierError as e:
            raise SessionValidationError(f"Duplicate session identifier: {e}") from e
        except ReferentialIntegrityError as e:
            raise SessionValidationError(f"Invalid reference: {e}") from e
        except RepositoryError as e:
            raise SessionValidationError(f"Failed to create session: {e}") from e

    async def get_session(self, session_id: UUID) -> SessionORM | None:
        """Retrieve a session by ID.

        Args:
            session_id: The session UUID.

        Returns:
            The session with experiment, variant, and task card loaded, or None.
        """
        return await self._session_repo.get_by_id(session_id)

    async def finalize_session(
        self, session_id: UUID, status: str = "completed"
    ) -> SessionORM | None:
        """Finalize a session safely with end time and status.

        This method atomically:
        1. Retrieves the session
        2. Validates it exists and is active
        3. Sets ended_at to current UTC time
        4. Updates status
        5. Commits changes

        Args:
            session_id: The session UUID to finalize.
            status: The final status (default: 'completed', alternatives: 'failed', 'cancelled').

        Returns:
            The finalized session, or None if not found.

        Raises:
            SessionValidationError: If the session cannot be finalized.
        """
        # Validate status
        valid_statuses = ["completed", "failed", "cancelled"]
        if status not in valid_statuses:
            raise SessionValidationError(
                f"Invalid status '{status}'. Must be one of: {valid_statuses}"
            )

        session = await self._session_repo.get_by_id(session_id)
        if session is None:
            return None

        # Check if already finalized
        if session.ended_at is not None:
            raise SessionValidationError(
                f"Session {session_id} is already finalized (ended_at={session.ended_at})"
            )

        try:
            finalized = await self._session_repo.finalize_session(session_id, status)
            return finalized
        except ReferentialIntegrityError as e:
            raise SessionValidationError(f"Failed to finalize session: {e}") from e

    async def fail_session(
        self, session_id: UUID, error_message: str | None = None
    ) -> SessionORM | None:
        """Mark a session as failed.

        Convenience method that calls finalize_session with status='failed'.

        Args:
            session_id: The session UUID to fail.
            error_message: Optional error message to log.

        Returns:
            The failed session, or None if not found.
        """
        session = await self.finalize_session(session_id, status="failed")
        if session and error_message:
            # Store error message in metadata if needed
            # For now, this is a placeholder for future enhancement
            pass
        return session

    async def cancel_session(self, session_id: UUID) -> SessionORM | None:
        """Cancel an active session.

        Convenience method that calls finalize_session with status='cancelled'.

        Args:
            session_id: The session UUID to cancel.

        Returns:
            The cancelled session, or None if not found.
        """
        return await self.finalize_session(session_id, status="cancelled")

    async def list_sessions_by_experiment(
        self, experiment_id: UUID, limit: int = 100, offset: int = 0
    ) -> list[SessionORM]:
        """List all sessions for an experiment.

        Args:
            experiment_id: The experiment UUID.
            limit: Maximum number of sessions to return.
            offset: Number of sessions to skip.

        Returns:
            List of sessions.
        """
        return await self._session_repo.list_by_experiment(experiment_id, limit, offset)

    async def list_active_sessions(self, limit: int = 100) -> list[SessionORM]:
        """List all active sessions.

        Args:
            limit: Maximum number of sessions to return.

        Returns:
            List of active sessions.
        """
        return await self._session_repo.list_active(limit)

    async def validate_session_exists(self, session_id: UUID) -> bool:
        """Check if a session exists.

        Args:
            session_id: The session UUID to check.

        Returns:
            True if the session exists.
        """
        return await self._session_repo.exists(session_id)

    async def is_session_active(self, session_id: UUID) -> bool:
        """Check if a session is active (not finalized).

        Args:
            session_id: The session UUID to check.

        Returns:
            True if the session exists and is active.
        """
        session = await self._session_repo.get_by_id(session_id)
        if session is None:
            return False
        return session.status == "active" and session.ended_at is None

    async def get_session_summary(self, session_id: UUID) -> dict | None:
        """Get a summary of session information.

        Args:
            session_id: The session UUID.

        Returns:
            Dictionary with session summary, or None if not found.
        """
        session = await self._session_repo.get_by_id(session_id)
        if session is None:
            return None

        return {
            "id": str(session.id),
            "status": session.status,
            "experiment_id": str(session.experiment_id),
            "variant_id": str(session.variant_id),
            "task_card_id": str(session.task_card_id),
            "harness_profile": session.harness_profile,
            "repo_path": session.repo_path,
            "git_branch": session.git_branch,
            "git_commit": session.git_commit,
            "git_dirty": session.git_dirty,
            "operator_label": session.operator_label,
            "started_at": session.started_at.isoformat() if session.started_at else None,
            "ended_at": session.ended_at.isoformat() if session.ended_at else None,
            "duration_seconds": (
                (session.ended_at - session.started_at).total_seconds()
                if session.ended_at and session.started_at
                else None
            ),
        }
