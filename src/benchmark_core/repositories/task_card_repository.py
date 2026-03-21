"""Repository for TaskCard entity."""
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from benchmark_core.db.models import TaskCardModel
from benchmark_core.models import TaskCard


class TaskCardRepository:
    """Repository for TaskCard CRUD operations."""

    async def create(self, session: AsyncSession, task_card: TaskCard) -> TaskCardModel:
        """Create a new task card."""
        model = TaskCardModel(
            task_card_id=str(task_card.task_card_id),
            name=task_card.name,
            repo_path=task_card.repo_path,
            goal=task_card.goal,
            stop_condition=task_card.stop_condition,
            session_timebox_minutes=task_card.session_timebox_minutes,
            created_at=task_card.created_at,
        )
        session.add(model)
        await session.commit()
        await session.refresh(model)
        return model

    async def get_by_id(self, session: AsyncSession, task_card_id: str) -> Optional[TaskCardModel]:
        """Get task card by ID."""
        result = await session.execute(
            select(TaskCardModel).where(TaskCardModel.task_card_id == task_card_id)
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, session: AsyncSession, name: str) -> Optional[TaskCardModel]:
        """Get task card by name."""
        result = await session.execute(
            select(TaskCardModel).where(TaskCardModel.name == name)
        )
        return result.scalar_one_or_none()

    async def get_all(self, session: AsyncSession, limit: int = 100) -> List[TaskCardModel]:
        """Get all task cards."""
        result = await session.execute(select(TaskCardModel).limit(limit))
        return list(result.scalars().all())
