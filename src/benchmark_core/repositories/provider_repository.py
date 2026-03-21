"""Repository for Provider entity."""
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from benchmark_core.db.models import ProviderModel
from benchmark_core.models import Provider


class ProviderRepository:
    """Repository for Provider CRUD operations."""

    async def create(self, session: AsyncSession, provider: Provider) -> ProviderModel:
        """Create a new provider."""
        model = ProviderModel(
            provider_id=str(provider.provider_id),
            name=provider.name,
            route_name=provider.route_name,
            protocol_surface=provider.protocol_surface,
            upstream_base_url=provider.upstream_base_url,
            created_at=provider.created_at,
        )
        session.add(model)
        await session.commit()
        await session.refresh(model)
        return model

    async def get_by_id(self, session: AsyncSession, provider_id: str) -> Optional[ProviderModel]:
        """Get provider by ID."""
        result = await session.execute(
            select(ProviderModel).where(ProviderModel.provider_id == provider_id)
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, session: AsyncSession, name: str) -> Optional[ProviderModel]:
        """Get provider by name."""
        result = await session.execute(
            select(ProviderModel).where(ProviderModel.name == name)
        )
        return result.scalar_one_or_none()

    async def get_all(self, session: AsyncSession, limit: int = 100) -> List[ProviderModel]:
        """Get all providers."""
        result = await session.execute(select(ProviderModel).limit(limit))
        return list(result.scalars().all())

    async def delete(self, session: AsyncSession, provider_id: str) -> bool:
        """Delete provider by ID."""
        model = await self.get_by_id(session, provider_id)
        if model:
            await session.delete(model)
            await session.commit()
            return True
        return False
