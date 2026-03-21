"""Repository for HarnessProfile entity."""
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from benchmark_core.db.models import HarnessProfileModel
from benchmark_core.models import HarnessProfile


class HarnessProfileRepository:
    """Repository for HarnessProfile CRUD operations."""

    async def create(self, session: AsyncSession, profile: HarnessProfile) -> HarnessProfileModel:
        """Create a new harness profile."""
        model = HarnessProfileModel(
            harness_profile_id=str(profile.harness_profile_id),
            name=profile.name,
            protocol_surface=profile.protocol_surface,
            base_url_env=profile.base_url_env,
            api_key_env=profile.api_key_env,
            model_env=profile.model_env,
            created_at=profile.created_at,
        )
        session.add(model)
        await session.commit()
        await session.refresh(model)
        return model

    async def get_by_id(self, session: AsyncSession, profile_id: str) -> Optional[HarnessProfileModel]:
        """Get harness profile by ID."""
        result = await session.execute(
            select(HarnessProfileModel).where(HarnessProfileModel.harness_profile_id == profile_id)
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, session: AsyncSession, name: str) -> Optional[HarnessProfileModel]:
        """Get harness profile by name."""
        result = await session.execute(
            select(HarnessProfileModel).where(HarnessProfileModel.name == name)
        )
        return result.scalar_one_or_none()

    async def get_all(self, session: AsyncSession, limit: int = 100) -> List[HarnessProfileModel]:
        """Get all harness profiles."""
        result = await session.execute(select(HarnessProfileModel).limit(limit))
        return list(result.scalars().all())
