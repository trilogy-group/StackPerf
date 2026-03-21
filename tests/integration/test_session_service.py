"""Integration tests for session service."""
import pytest
from datetime import datetime
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from benchmark_core.models import Session, SessionStatus
from benchmark_core.services.session_service import SessionService
from benchmark_core.repositories.session_repository import (
    DuplicateSessionError,
    SessionRepository,
)
from benchmark_core.db.models import SessionModel


class TestSessionCreation:
    """Tests for session creation."""

    @pytest.mark.asyncio
    async def test_create_session_success(
        self,
        db_session: AsyncSession,
        sample_experiment,
        sample_variant,
        sample_task_card,
        sample_harness_profile,
    ):
        """Should create session successfully."""
        service = SessionService(db_session)
        
        session_id = uuid4()
        session = await service.create_session(
            session_id=session_id,
            experiment_id=sample_experiment.experiment_id,
            variant_id=sample_variant.variant_id,
            task_card_id=sample_task_card.task_card_id,
            harness_profile_id=sample_harness_profile.harness_profile_id,
            operator_label="test-operator",
        )
        
        assert session.session_id == session_id
        assert session.status == SessionStatus.PENDING
        assert session.operator_label == "test-operator"

    @pytest.mark.asyncio
    async def test_create_session_with_git_metadata(
        self,
        db_session: AsyncSession,
        sample_experiment,
        sample_variant,
        sample_task_card,
        sample_harness_profile,
    ):
        """Should capture git metadata."""
        service = SessionService(db_session)
        
        session = await service.create_session(
            session_id=uuid4(),
            experiment_id=sample_experiment.experiment_id,
            variant_id=sample_variant.variant_id,
            task_card_id=sample_task_card.task_card_id,
            harness_profile_id=sample_harness_profile.harness_profile_id,
            git_branch="feature/test",
            git_commit_sha="abc123def456",
            git_dirty=True,
        )
        
        assert session.git_branch == "feature/test"
        assert session.git_commit_sha == "abc123def456"
        assert session.git_dirty is True

    @pytest.mark.asyncio
    async def test_duplicate_session_id_rejected(
        self,
        db_session: AsyncSession,
        sample_experiment,
        sample_variant,
        sample_task_card,
        sample_harness_profile,
    ):
        """Should reject duplicate session_id."""
        service = SessionService(db_session)
        
        session_id = uuid4()
        
        # Create first session
        await service.create_session(
            session_id=session_id,
            experiment_id=sample_experiment.experiment_id,
            variant_id=sample_variant.variant_id,
            task_card_id=sample_task_card.task_card_id,
            harness_profile_id=sample_harness_profile.harness_profile_id,
        )
        
        # Attempt to create duplicate
        with pytest.raises(DuplicateSessionError):
            await service.create_session(
                session_id=session_id,
                experiment_id=sample_experiment.experiment_id,
                variant_id=sample_variant.variant_id,
                task_card_id=sample_task_card.task_card_id,
                harness_profile_id=sample_harness_profile.harness_profile_id,
            )


class TestSessionFinalization:
    """Tests for session finalization."""

    @pytest.mark.asyncio
    async def test_finalize_session_completed(
        self,
        db_session: AsyncSession,
        sample_session,
    ):
        """Should finalize session as completed."""
        service = SessionService(db_session)
        
        ended_at = datetime.utcnow()
        result = await service.finalize_session(
            session_id=sample_session.session_id,
            status=SessionStatus.COMPLETED,
            ended_at=ended_at,
        )
        
        assert result is not None
        assert result.status == SessionStatus.COMPLETED
        assert result.ended_at == ended_at

    @pytest.mark.asyncio
    async def test_finalize_session_aborted(
        self,
        db_session: AsyncSession,
        sample_session,
    ):
        """Should finalize session as aborted."""
        service = SessionService(db_session)
        
        result = await service.finalize_session(
            session_id=sample_session.session_id,
            status=SessionStatus.ABORTED,
        )
        
        assert result is not None
        assert result.status == SessionStatus.ABORTED
        assert result.ended_at is not None

    @pytest.mark.asyncio
    async def test_finalize_nonexistent_session(
        self,
        db_session: AsyncSession,
    ):
        """Should return None for nonexistent session."""
        service = SessionService(db_session)
        
        result = await service.finalize_session(
            session_id=uuid4(),
            status=SessionStatus.COMPLETED,
        )
        
        assert result is None
