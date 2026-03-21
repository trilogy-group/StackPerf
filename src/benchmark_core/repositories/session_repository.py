"""Repository for Session entity."""
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from benchmark_core.db.models import SessionModel
from benchmark_core.models import Session, SessionStatus


class DuplicateSessionError(Exception):
    """Raised when attempting to create a session with duplicate identifier."""
    pass


class SessionRepository:
    """Repository for Session CRUD operations with duplicate rejection."""

    async def create(self, session: AsyncSession, sess: Session) -> SessionModel:
        """Create a new session.
        
        Raises:
            DuplicateSessionError: If session_id or proxy_key_alias already exists.
        """
        model = SessionModel(
            session_id=str(sess.session_id),
            experiment_id=str(sess.experiment_id),
            variant_id=str(sess.variant_id),
            task_card_id=str(sess.task_card_id),
            harness_profile_id=str(sess.harness_profile_id),
            status=sess.status,
            started_at=sess.started_at,
            ended_at=sess.ended_at,
            operator_label=sess.operator_label,
            repo_root=sess.repo_root,
            git_branch=sess.git_branch,
            git_commit_sha=sess.git_commit_sha,
            git_dirty=sess.git_dirty,
            proxy_key_alias=sess.proxy_key_alias,
            proxy_virtual_key_id=sess.proxy_virtual_key_id,
        )
        session.add(model)
        try:
            await session.commit()
            await session.refresh(model)
            return model
        except IntegrityError as e:
            await session.rollback()
            if "session_id" in str(e) or "proxy_key_alias" in str(e):
                raise DuplicateSessionError(
                    f"Session with identifier already exists: {sess.session_id}"
                ) from e
            raise

    async def get_by_id(self, session: AsyncSession, session_id: str) -> Optional[SessionModel]:
        """Get session by ID."""
        result = await session.execute(
            select(SessionModel).where(SessionModel.session_id == session_id)
        )
        return result.scalar_one_or_none()

    async def get_by_proxy_key_alias(
        self, session: AsyncSession, alias: str
    ) -> Optional[SessionModel]:
        """Get session by proxy key alias."""
        result = await session.execute(
            select(SessionModel).where(SessionModel.proxy_key_alias == alias)
        )
        return result.scalar_one_or_none()

    async def get_all(self, session: AsyncSession, limit: int = 100) -> List[SessionModel]:
        """Get all sessions."""
        result = await session.execute(select(SessionModel).limit(limit))
        return list(result.scalars().all())

    async def get_by_status(
        self, session: AsyncSession, status: SessionStatus
    ) -> List[SessionModel]:
        """Get sessions by status."""
        result = await session.execute(
            select(SessionModel).where(SessionModel.status == status)
        )
        return list(result.scalars().all())

    async def get_by_experiment(
        self, session: AsyncSession, experiment_id: str
    ) -> List[SessionModel]:
        """Get sessions by experiment ID."""
        result = await session.execute(
            select(SessionModel).where(SessionModel.experiment_id == experiment_id)
        )
        return list(result.scalars().all())

    async def get_by_variant(
        self, session: AsyncSession, variant_id: str
    ) -> List[SessionModel]:
        """Get sessions by variant ID."""
        result = await session.execute(
            select(SessionModel).where(SessionModel.variant_id == variant_id)
        )
        return list(result.scalars().all())

    async def finalize(
        self,
        session: AsyncSession,
        session_id: str,
        status: SessionStatus,
        ended_at: datetime,
    ) -> Optional[SessionModel]:
        """Finalize a session with final status."""
        model = await self.get_by_id(session, session_id)
        if model:
            model.status = status
            model.ended_at = ended_at
            await session.commit()
            await session.refresh(model)
            return model
        return None
