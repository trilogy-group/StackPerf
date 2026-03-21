"""Integration tests for request repository."""
import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from benchmark_core.models import Request, RequestStatus
from benchmark_core.repositories.request_repository import RequestRepository
from benchmark_core.db.models import RequestModel


class TestRequestCreation:
    """Tests for request creation."""

    @pytest.mark.asyncio
    async def test_create_request(
        self,
        db_session: AsyncSession,
        sample_session,
    ):
        """Should create request successfully."""
        repo = RequestRepository()
        
        request = Request(
            session_id=sample_session.session_id,
            litellm_call_id="call-test-001",
            model="gpt-4",
            started_at=datetime.utcnow(),
            latency_ms=1234.5,
            input_tokens=100,
            output_tokens=200,
        )
        
        model = await repo.create(db_session, request)
        
        assert model.request_id is not None
        assert model.litellm_call_id == "call-test-001"
        assert model.latency_ms == 1234.5

    @pytest.mark.asyncio
    async def test_get_by_litellm_call_id(
        self,
        db_session: AsyncSession,
        sample_session,
    ):
        """Should find request by litellm_call_id."""
        repo = RequestRepository()
        
        # Create request
        request = Request(
            session_id=sample_session.session_id,
            litellm_call_id="call-unique-001",
            model="gpt-4",
        )
        await repo.create(db_session, request)
        
        # Find by call ID
        found = await repo.get_by_litellm_call_id(db_session, "call-unique-001")
        
        assert found is not None
        assert found.litellm_call_id == "call-unique-001"

    @pytest.mark.asyncio
    async def test_exists_by_litellm_call_id(
        self,
        db_session: AsyncSession,
        sample_session,
    ):
        """Should check existence correctly."""
        repo = RequestRepository()
        
        # Create request
        request = Request(
            session_id=sample_session.session_id,
            litellm_call_id="call-exists-001",
            model="gpt-4",
        )
        await repo.create(db_session, request)
        
        # Check exists
        exists = await repo.exists_by_litellm_call_id(db_session, "call-exists-001")
        assert exists is True
        
        # Check non-exists
        not_exists = await repo.exists_by_litellm_call_id(db_session, "call-nonexistent")
        assert not_exists is False


class TestRequestQueries:
    """Tests for request queries."""

    @pytest.mark.asyncio
    async def test_get_by_session(
        self,
        db_session: AsyncSession,
        sample_session,
    ):
        """Should get all requests for a session."""
        repo = RequestRepository()
        
        # Create multiple requests
        for i in range(3):
            request = Request(
                session_id=sample_session.session_id,
                litellm_call_id=f"call-session-{i}",
                model="gpt-4",
            )
            await repo.create(db_session, request)
        
        # Query by session
        requests = await repo.get_by_session(db_session, sample_session.session_id)
        
        assert len(requests) == 3

    @pytest.mark.asyncio
    async def test_get_by_time_window(
        self,
        db_session: AsyncSession,
        sample_session,
    ):
        """Should get requests within time window."""
        repo = RequestRepository()
        
        now = datetime.utcnow()
        
        # Create request in window
        request_in = Request(
            session_id=sample_session.session_id,
            litellm_call_id="call-in-window",
            model="gpt-4",
            started_at=now,
        )
        await repo.create(db_session, request_in)
        
        # Query window
        requests = await repo.get_by_time_window(
            db_session,
            start_time=now - timedelta(hours=1),
            end_time=now + timedelta(hours=1),
        )
        
        assert len(requests) >= 1
        assert any(r.litellm_call_id == "call-in-window" for r in requests)
