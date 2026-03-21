"""Repository for Variant entity."""
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from benchmark_core.db.models import VariantModel
from benchmark_core.models import Variant


class VariantRepository:
    """Repository for Variant CRUD operations."""

    async def create(self, session: AsyncSession, variant: Variant) -> VariantModel:
        """Create a new variant."""
        model = VariantModel(
            variant_id=str(variant.variant_id),
            name=variant.name,
            provider_id=str(variant.provider_id),
            model_alias=variant.model_alias,
            harness_profile_id=str(variant.harness_profile_id),
            config_fingerprint=variant.config_fingerprint,
            created_at=variant.created_at,
        )
        session.add(model)
        await session.commit()
        await session.refresh(model)
        return model

    async def get_by_id(self, session: AsyncSession, variant_id: str) -> Optional[VariantModel]:
        """Get variant by ID."""
        result = await session.execute(
            select(VariantModel).where(VariantModel.variant_id == variant_id)
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, session: AsyncSession, name: str) -> Optional[VariantModel]:
        """Get variant by name."""
        result = await session.execute(
            select(VariantModel).where(VariantModel.name == name)
        )
        return result.scalar_one_or_none()

    async def get_all(self, session: AsyncSession, limit: int = 100) -> List[VariantModel]:
        """Get all variants."""
        result = await session.execute(select(VariantModel).limit(limit))
        return list(result.scalars().all())

    async def get_by_experiment(
        self, session: AsyncSession, experiment_id: str
    ) -> List[VariantModel]:
        """Get variants by experiment ID through sessions."""
        from sqlalchemy import distinct

        result = await session.execute(
            select(VariantModel)
            .join(VariantModel.sessions)
            .where(VariantModel.sessions.any(experiment_id=experiment_id))
            .distinct()
        )
        return list(result.scalars().all())
