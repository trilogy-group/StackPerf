"""Session lifecycle service."""
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from benchmark_core.models import Session, SessionStatus
from benchmark_core.repositories.session_repository import (
    DuplicateSessionError,
    SessionRepository,
)


class SessionService:
    """Service for session lifecycle operations."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.session_repo = SessionRepository()

    async def create_session(
        self,
        session_id: UUID,
        experiment_id: UUID,
        variant_id: UUID,
        task_card_id: UUID,
        harness_profile_id: UUID,
        operator_label: Optional[str] = None,
        repo_root: Optional[str] = None,
        git_branch: Optional[str] = None,
        git_commit_sha: Optional[str] = None,
        git_dirty: Optional[bool] = None,
        proxy_key_alias: Optional[str] = None,
        proxy_virtual_key_id: Optional[str] = None,
    ) -> Session:
        """Create a new benchmark session.

        Args:
            session_id: Unique session identifier
            experiment_id: Experiment this session belongs to
            variant_id: Variant configuration for this session
            task_card_id: Task card defining the work
            harness_profile_id: Harness profile in use
            operator_label: Optional operator-provided label
            repo_root: Repository root path
            git_branch: Current git branch
            git_commit_sha: Current git commit SHA
            git_dirty: Whether repo has uncommitted changes
            proxy_key_alias: Alias for the proxy key
            proxy_virtual_key_id: LiteLLM virtual key ID

        Returns:
            Created session domain model

        Raises:
            DuplicateSessionError: If session with same ID or proxy_key_alias exists
        """
        new_session = Session(
            session_id=session_id,
            experiment_id=experiment_id,
            variant_id=variant_id,
            task_card_id=task_card_id,
            harness_profile_id=harness_profile_id,
            status=SessionStatus.PENDING,
            started_at=datetime.utcnow(),
            operator_label=operator_label,
            repo_root=repo_root,
            git_branch=git_branch,
            git_commit_sha=git_commit_sha,
            git_dirty=git_dirty,
            proxy_key_alias=proxy_key_alias,
            proxy_virtual_key_id=proxy_virtual_key_id,
        )
        
        await self.session_repo.create(self.session, new_session)
        return new_session

    async def finalize_session(
        self,
        session_id: UUID,
        status: SessionStatus,
        ended_at: Optional[datetime] = None,
    ) -> Optional[Session]:
        """Finalize a session with final status.

        Args:
            session_id: Session to finalize
            status: Final status (COMPLETED, ABORTED, or INVALID)
            ended_at: End timestamp (defaults to now)

        Returns:
            Updated session model or None if not found
        """
        if ended_at is None:
            ended_at = datetime.utcnow()

        model = await self.session_repo.finalize(
            self.session, str(session_id), status, ended_at
        )
        if model:
            return Session(
                session_id=UUID(model.session_id),
                experiment_id=UUID(model.experiment_id),
                variant_id=UUID(model.variant_id),
                task_card_id=UUID(model.task_card_id),
                harness_profile_id=UUID(model.harness_profile_id),
                status=model.status,
                started_at=model.started_at,
                ended_at=model.ended_at,
                operator_label=model.operator_label,
                repo_root=model.repo_root,
                git_branch=model.git_branch,
                git_commit_sha=model.git_commit_sha,
                git_dirty=model.git_dirty,
                proxy_key_alias=model.proxy_key_alias,
                proxy_virtual_key_id=model.proxy_virtual_key_id,
            )
        return None

    async def get_session(self, session_id: UUID) -> Optional[Session]:
        """Get session by ID."""
        model = await self.session_repo.get_by_id(self.session, str(session_id))
        if model:
            return Session(
                session_id=UUID(model.session_id),
                experiment_id=UUID(model.experiment_id),
                variant_id=UUID(model.variant_id),
                task_card_id=UUID(model.task_card_id),
                harness_profile_id=UUID(model.harness_profile_id),
                status=model.status,
                started_at=model.started_at,
                ended_at=model.ended_at,
                operator_label=model.operator_label,
                repo_root=model.repo_root,
                git_branch=model.git_branch,
                git_commit_sha=model.git_commit_sha,
                git_dirty=model.git_dirty,
                proxy_key_alias=model.proxy_key_alias,
                proxy_virtual_key_id=model.proxy_virtual_key_id,
            )
        return None
