"""Repository for MetricRollup entity."""
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from benchmark_core.db.models import MetricRollupModel
from benchmark_core.models import MetricRollup, RollupScopeType


class MetricRollupRepository:
    """Repository for MetricRollup CRUD operations."""

    async def create(
        self, session: AsyncSession, rollup: MetricRollup
    ) -> MetricRollupModel:
        """Create a new metric rollup."""
        model = MetricRollupModel(
            rollup_id=str(rollup.rollup_id),
            scope_type=rollup.scope_type,
            scope_id=str(rollup.scope_id),
            metric_name=rollup.metric_name,
            metric_value=rollup.metric_value,
            computed_at=rollup.computed_at,
            window_start=rollup.window_start,
            window_end=rollup.window_end,
        )
        session.add(model)
        await session.commit()
        await session.refresh(model)
        return model

    async def upsert(
        self, session: AsyncSession, rollup: MetricRollup
    ) -> MetricRollupModel:
        """Create or update metric rollup."""
        existing = await self.get_by_scope_and_name(
            session, rollup.scope_type, str(rollup.scope_id), rollup.metric_name
        )
        if existing:
            existing.metric_value = rollup.metric_value
            existing.computed_at = rollup.computed_at
            existing.window_start = rollup.window_start
            existing.window_end = rollup.window_end
            await session.commit()
            await session.refresh(existing)
            return existing
        return await self.create(session, rollup)

    async def get_by_scope_and_name(
        self,
        session: AsyncSession,
        scope_type: RollupScopeType,
        scope_id: str,
        metric_name: str,
    ) -> Optional[MetricRollupModel]:
        """Get rollup by scope and metric name."""
        result = await session.execute(
            select(MetricRollupModel).where(
                MetricRollupModel.scope_type == scope_type,
                MetricRollupModel.scope_id == scope_id,
                MetricRollupModel.metric_name == metric_name,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_scope(
        self,
        session: AsyncSession,
        scope_type: RollupScopeType,
        scope_id: str,
    ) -> List[MetricRollupModel]:
        """Get all rollups for a scope."""
        result = await session.execute(
            select(MetricRollupModel).where(
                MetricRollupModel.scope_type == scope_type,
                MetricRollupModel.scope_id == scope_id,
            )
        )
        return list(result.scalars().all())

    async def get_by_session(
        self, session: AsyncSession, session_id: str
    ) -> List[MetricRollupModel]:
        """Get rollups for a session."""
        return await self.get_by_scope(session, RollupScopeType.SESSION, session_id)

    async def get_by_variant(
        self, session: AsyncSession, variant_id: str
    ) -> List[MetricRollupModel]:
        """Get rollups for a variant."""
        return await self.get_by_scope(session, RollupScopeType.VARIANT, variant_id)

    async def get_by_experiment(
        self, session: AsyncSession, experiment_id: str
    ) -> List[MetricRollupModel]:
        """Get rollups for an experiment."""
        return await self.get_by_scope(
            session, RollupScopeType.EXPERIMENT, experiment_id
        )
