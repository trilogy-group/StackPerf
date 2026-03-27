"""Service for managing benchmark session lifecycle safely."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from benchmark_core.models import Session
from benchmark_core.repositories.base import (
    DuplicateIdentifierError,
    ReferentialIntegrityError,
    RepositoryError,
)
from benchmark_core.repositories.request_repository import SQLRequestRepository
from benchmark_core.repositories.session_repository import SQLSessionRepository
from collectors.litellm_collector import (
    CollectionDiagnostics,
    IngestWatermark,
    LiteLLMCollector,
)


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
        repository: SQLSessionRepository,
    ) -> None:
        """Initialize the session service.

        Args:
            repository: SessionRepository instance for database operations.
        """
        self._session_repo = repository
        # Store db_session for operations that need it
        self._db_session = repository._session

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
    ) -> Session:
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
            db_session = await self._session_repo.create_session_safe(
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
            # Convert DBSession to domain Session model
            return Session(
                session_id=db_session.id,
                experiment_id=str(db_session.experiment_id),
                variant_id=str(db_session.variant_id),
                task_card_id=str(db_session.task_card_id),
                harness_profile=db_session.harness_profile,
                repo_path=db_session.repo_path,
                git_branch=db_session.git_branch,
                git_commit=db_session.git_commit,
                git_dirty=db_session.git_dirty,
                operator_label=db_session.operator_label,
                proxy_credential_id=db_session.proxy_credential_id,
                started_at=db_session.started_at,
                ended_at=db_session.ended_at,
                status=db_session.status,
            )
        except DuplicateIdentifierError as e:
            raise SessionValidationError(f"Duplicate session identifier: {e}") from e
        except ReferentialIntegrityError as e:
            raise SessionValidationError(f"Invalid reference: {e}") from e
        except RepositoryError as e:
            raise SessionValidationError(f"Failed to create session: {e}") from e

    async def get_session(self, session_id: UUID) -> Session | None:
        """Retrieve a session by ID.

        Args:
            session_id: The session UUID.

        Returns:
            The session with experiment, variant, and task card loaded, or None.
        """
        db_session = await self._session_repo.get_by_id(session_id)
        if db_session is None:
            return None
        # Convert DBSession to domain Session model
        return Session(
            session_id=db_session.id,
            experiment_id=str(db_session.experiment_id),
            variant_id=str(db_session.variant_id),
            task_card_id=str(db_session.task_card_id),
            harness_profile=db_session.harness_profile,
            repo_path=db_session.repo_path,
            git_branch=db_session.git_branch,
            git_commit=db_session.git_commit,
            git_dirty=db_session.git_dirty,
            operator_label=db_session.operator_label,
            proxy_credential_id=db_session.proxy_credential_id,
            started_at=db_session.started_at,
            ended_at=db_session.ended_at,
            status=db_session.status,
        )

    async def finalize_session(
        self,
        session_id: UUID,
        status: str = "completed",
        ended_at: datetime | None = None,
    ) -> Session | None:
        """Finalize a session safely with end time and status.

        This method atomically:
        1. Retrieves the session
        2. Validates it exists and is active
        3. Sets ended_at to provided time or current UTC time
        4. Updates status
        5. Commits changes

        Args:
            session_id: The session UUID to finalize.
            status: The final status (default: 'completed', alternatives: 'failed', 'cancelled').
            ended_at: Optional end timestamp. Defaults to current UTC time.

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

        # Set default ended_at if not provided
        if ended_at is None:
            ended_at = datetime.now(UTC)

        session = await self._session_repo.get_by_id(session_id)
        if session is None:
            return None

        # Check if already finalized
        if session.ended_at is not None:
            raise SessionValidationError(
                f"Session {session_id} is already finalized (ended_at={session.ended_at})"
            )

        try:
            db_finalized = await self._session_repo.finalize_session(session_id, status, ended_at)
            if db_finalized is None:
                return None
            # Convert DBSession to domain Session model
            return Session(
                session_id=db_finalized.id,
                experiment_id=str(db_finalized.experiment_id),
                variant_id=str(db_finalized.variant_id),
                task_card_id=str(db_finalized.task_card_id),
                harness_profile=db_finalized.harness_profile,
                repo_path=db_finalized.repo_path,
                git_branch=db_finalized.git_branch,
                git_commit=db_finalized.git_commit,
                git_dirty=db_finalized.git_dirty,
                operator_label=db_finalized.operator_label,
                proxy_credential_id=db_finalized.proxy_credential_id,
                started_at=db_finalized.started_at,
                ended_at=db_finalized.ended_at,
                status=db_finalized.status,
            )
        except ReferentialIntegrityError as e:
            raise SessionValidationError(f"Failed to finalize session: {e}") from e

    async def fail_session(
        self, session_id: UUID, error_message: str | None = None
    ) -> Session | None:
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

    async def cancel_session(self, session_id: UUID) -> Session | None:
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
    ) -> list[Session]:
        """List all sessions for an experiment.

        Args:
            experiment_id: The experiment UUID.
            limit: Maximum number of sessions to return.
            offset: Number of sessions to skip.

        Returns:
            List of sessions.
        """
        return await self._session_repo.list_by_experiment(experiment_id, limit, offset)

    async def list_active_sessions(self, limit: int = 100) -> list[Session]:
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
        db_session = await self._session_repo.get_by_id(session_id)
        if db_session is None:
            return None

        return {
            "id": str(db_session.id),
            "status": db_session.status,
            "experiment_id": str(db_session.experiment_id),
            "variant_id": str(db_session.variant_id),
            "task_card_id": str(db_session.task_card_id),
            "harness_profile": db_session.harness_profile,
            "repo_path": db_session.repo_path,
            "git_branch": db_session.git_branch,
            "git_commit": db_session.git_commit,
            "git_dirty": db_session.git_dirty,
            "operator_label": db_session.operator_label,
            "started_at": db_session.started_at.isoformat() if db_session.started_at else None,
            "ended_at": db_session.ended_at.isoformat() if db_session.ended_at else None,
            "duration_seconds": (
                (db_session.ended_at - db_session.started_at).total_seconds()
                if db_session.ended_at and db_session.started_at
                else None
            ),
        }


@dataclass
class CollectionJobResult:
    """Result of a collection job execution."""

    success: bool
    requests_collected: int
    requests_normalized: int
    diagnostics: CollectionDiagnostics
    watermark: IngestWatermark
    error_message: str | None = None


class CollectionJobService:
    """Service for managing LiteLLM collection jobs.

    Handles raw request collection with idempotent ingest cursor handling,
    watermark tracking, and comprehensive diagnostics.
    """

    def __init__(
        self,
        litellm_base_url: str,
        litellm_api_key: str,
        repository: SQLRequestRepository,
    ) -> None:
        """Initialize the collection job service.

        Args:
            litellm_base_url: LiteLLM proxy base URL.
            litellm_api_key: LiteLLM API key.
            repository: Repository for persisting normalized requests.
        """
        self._collector = LiteLLMCollector(
            base_url=litellm_base_url,
            api_key=litellm_api_key,
            repository=repository,
        )
        self._repository = repository

    async def run_collection_job(
        self,
        session_id: UUID,
        start_time: str | None = None,
        end_time: str | None = None,
        watermark: IngestWatermark | None = None,
    ) -> CollectionJobResult:
        """Run a collection job for a specific session.

        Fetches raw requests from LiteLLM, normalizes them, and persists
        to the database. Uses watermark-based idempotency to avoid duplicates.

        Args:
            session_id: The benchmark session ID to collect for.
            start_time: Optional ISO format start time filter.
            end_time: Optional ISO format end time filter.
            watermark: Optional ingest watermark to resume from.

        Returns:
            CollectionJobResult with collection outcome
        """
        diagnostics = CollectionDiagnostics()

        try:
            # Fetch and normalize requests from LiteLLM
            requests, new_watermark = await self._collector.collect(
                session_id=session_id,
                start_time=start_time,
                end_time=end_time,
                watermark=watermark,
            )

            if not requests:
                return CollectionJobResult(
                    success=True,
                    requests_collected=0,
                    requests_normalized=0,
                    diagnostics=diagnostics,
                    watermark=new_watermark,
                )

            # Persist normalized requests
            created = await self._repository.create_many(requests)

            return CollectionJobResult(
                success=True,
                requests_collected=len(requests),
                requests_normalized=len(created),
                diagnostics=diagnostics,
                watermark=new_watermark,
            )

        except Exception as e:
            diagnostics.add_error(str(e))
            return CollectionJobResult(
                success=False,
                requests_collected=0,
                requests_normalized=0,
                diagnostics=diagnostics,
                watermark=IngestWatermark(cursor=""),
                error_message=str(e),
            )

    async def run_collection_lookback(
        self,
        session_id: UUID,
        lookback_hours: int = 24,
        watermark: IngestWatermark | None = None,
    ) -> CollectionJobResult:
        """Run a collection job with lookback window.

        Args:
            session_id: The benchmark session ID to collect for.
            lookback_hours: Hours to look back from now (default 24)
            watermark: Optional ingest watermark to resume from

        Returns:
            CollectionJobResult with collection outcome
        """
        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(hours=lookback_hours)

        return await self.run_collection_job(
            session_id=session_id,
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
            watermark=watermark,
        )

    def get_diagnostics_summary(self, diagnostics: CollectionDiagnostics) -> dict[str, Any]:
        """Generate a human-readable diagnostics summary.

        Provides clear visibility into collection health, including:
        - Total records processed
        - Normalization success rate
        - Missing field breakdown
        - Error details
        """
        total = diagnostics.total_raw_records
        normalized = diagnostics.normalized_count
        skipped = diagnostics.skipped_count

        summary: dict[str, Any] = {
            "total_raw_records": total,
            "normalized_count": normalized,
            "skipped_count": skipped,
            "success_rate": f"{normalized}/{total} ({normalized / total * 100:.1f}%)" if total > 0 else "N/A",
        }

        if diagnostics.missing_fields:
            summary["missing_fields"] = {
                field: f"{count} occurrences"
                for field, count in diagnostics.missing_fields.items()
            }

        if diagnostics.errors:
            summary["errors"] = diagnostics.errors[:10]  # Limit to first 10
            if len(diagnostics.errors) > 10:
                summary["errors_truncated"] = len(diagnostics.errors) - 10

        return summary
