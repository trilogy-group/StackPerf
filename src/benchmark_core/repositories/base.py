"""Base repository with common database operations."""
from typing import AsyncGenerator, Generic, List, Optional, Type, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from benchmark_core.db.connection import async_session_factory

ModelType = TypeVar("ModelType")


class BaseRepository(Generic[ModelType]):
    """Base repository with common CRUD operations."""

    def __init__(self, model: Type[ModelType]) -> None:
        self.model = model

    async def _get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get database session."""
        if async_session_factory is None:
            raise RuntimeError("Database not initialized. Call init_db() first.")
        async with async_session_factory() as session:
            yield session

    async def create(self, session: AsyncSession, obj: ModelType) -> ModelType:
        """Create a new record."""
        session.add(obj)
        await session.commit()
        await session.refresh(obj)
        return obj

    async def get_by_id(self, session: AsyncSession, id: str) -> Optional[ModelType]:
        """Get record by ID."""
        result = await session.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()

    async def get_all(self, session: AsyncSession, limit: int = 100) -> List[ModelType]:
        """Get all records with limit."""
        result = await session.execute(select(self.model).limit(limit))
        return list(result.scalars().all())

    async def delete(self, session: AsyncSession, id: str) -> bool:
        """Delete record by ID."""
        obj = await self.get_by_id(session, id)
        if obj:
            await session.delete(obj)
            await session.commit()
            return True
        return False
