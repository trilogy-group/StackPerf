"""Repository for Experiment entity."""
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from benchmark_core.db.models import ExperimentModel
from benchmark_core.models import Experiment


class ExperimentRepository:
    """Repository for Experiment CRUD operations."""

    async def create(self, session: AsyncSession, experiment: Experiment) -> ExperimentModel:
        """Create a new experiment."""
        model = ExperimentModel(
            experiment_id=str(experiment.experiment_id),
            name=experiment.name,
            description=experiment.description,
            created_at=experiment.created_at,
        )
        session.add(model)
        await session.commit()
        await session.refresh(model)
        return model

    async def get_by_id(self, session: AsyncSession, experiment_id: str) -> Optional[ExperimentModel]:
        """Get experiment by ID."""
        result = await session.execute(
            select(ExperimentModel).where(ExperimentModel.experiment_id == experiment_id)
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, session: AsyncSession, name: str) -> Optional[ExperimentModel]:
        """Get experiment by name."""
        result = await session.execute(
            select(ExperimentModel).where(ExperimentModel.name == name)
        )
        return result.scalar_one_or_none()

    async def get_all(self, session: AsyncSession, limit: int = 100) -> List[ExperimentModel]:
        """Get all experiments."""
        result = await session.execute(select(ExperimentModel).limit(limit))
        return list(result.scalars().all())
