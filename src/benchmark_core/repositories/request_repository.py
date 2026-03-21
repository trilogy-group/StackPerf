"""Repository for Request entity."""
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from benchmark_core.db.models import RequestModel
from benchmark_core.models import Request, RequestStatus


class RequestRepository:
    """Repository for Request CRUD operations."""

    async def create(self, session: AsyncSession, req: Request) -> RequestModel:
        """Create a new request."""
        model = RequestModel(
            request_id=str(req.request_id),
            session_id=str(req.session_id) if req.session_id else None,
            experiment_id=str(req.experiment_id) if req.experiment_id else None,
            variant_id=str(req.variant_id) if req.variant_id else None,
            provider_id=str(req.provider_id) if req.provider_id else None,
            provider_route=req.provider_route,
            model=req.model,
            harness_profile_id=str(req.harness_profile_id) if req.harness_profile_id else None,
            litellm_call_id=req.litellm_call_id,
            provider_request_id=req.provider_request_id,
            started_at=req.started_at,
            finished_at=req.finished_at,
            latency_ms=req.latency_ms,
            ttft_ms=req.ttft_ms,
            proxy_overhead_ms=req.proxy_overhead_ms,
            provider_latency_ms=req.provider_latency_ms,
            input_tokens=req.input_tokens,
            output_tokens=req.output_tokens,
            cached_input_tokens=req.cached_input_tokens,
            cache_write_tokens=req.cache_write_tokens,
            status=req.status,
            error_code=req.error_code,
        )
        session.add(model)
        await session.commit()
        await session.refresh(model)
        return model

    async def get_by_id(self, session: AsyncSession, request_id: str) -> Optional[RequestModel]:
        """Get request by ID."""
        result = await session.execute(
            select(RequestModel).where(RequestModel.request_id == request_id)
        )
        return result.scalar_one_or_none()

    async def get_by_litellm_call_id(
        self, session: AsyncSession, litellm_call_id: str
    ) -> Optional[RequestModel]:
        """Get request by LiteLLM call ID."""
        result = await session.execute(
            select(RequestModel).where(RequestModel.litellm_call_id == litellm_call_id)
        )
        return result.scalar_one_or_none()

    async def get_by_session(
        self, session: AsyncSession, session_id: str
    ) -> List[RequestModel]:
        """Get all requests for a session."""
        result = await session.execute(
            select(RequestModel).where(RequestModel.session_id == session_id)
        )
        return list(result.scalars().all())

    async def get_by_time_window(
        self,
        session: AsyncSession,
        start_time: datetime,
        end_time: datetime,
        limit: int = 1000,
    ) -> List[RequestModel]:
        """Get requests within a time window."""
        result = await session.execute(
            select(RequestModel)
            .where(RequestModel.started_at >= start_time)
            .where(RequestModel.started_at <= end_time)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def exists_by_litellm_call_id(
        self, session: AsyncSession, litellm_call_id: str
    ) -> bool:
        """Check if request with LiteLLM call ID exists."""
        result = await session.execute(
            select(RequestModel.request_id).where(
                RequestModel.litellm_call_id == litellm_call_id
            )
        )
        return result.scalar_one_or_none() is not None
