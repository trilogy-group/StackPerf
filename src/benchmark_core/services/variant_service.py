"""Service for managing Variant entities."""

from uuid import UUID

from sqlalchemy.orm import Session as SQLAlchemySession

from benchmark_core.db.models import Variant as VariantORM
from benchmark_core.repositories.base import (
    DuplicateIdentifierError,
    ReferentialIntegrityError,
    RepositoryError,
)
from benchmark_core.repositories.variant_repository import SQLVariantRepository


class VariantServiceError(Exception):
    """Raised when variant service operation fails."""

    pass


class VariantService:
    """Service for managing benchmark variants.

    Variants define benchmarkable combinations of:
    - Provider route
    - Model alias
    - Harness profile
    - Settings and overrides
    """

    def __init__(
        self,
        db_session: SQLAlchemySession,
        variant_repo: SQLVariantRepository | None = None,
    ) -> None:
        """Initialize the variant service.

        Args:
            db_session: SQLAlchemy session for database operations.
            variant_repo: Optional repository instance. If not provided, one is created.
        """
        self._db_session = db_session
        self._variant_repo = variant_repo or SQLVariantRepository(db_session)

    async def create_variant(
        self,
        name: str,
        provider: str,
        model_alias: str,
        harness_profile: str,
        provider_route: str | None = None,
        harness_env_overrides: dict | None = None,
        benchmark_tags: dict | None = None,
    ) -> VariantORM:
        """Create a new benchmark variant.

        Args:
            name: Unique variant name.
            provider: Provider name.
            model_alias: Model alias to use.
            harness_profile: Harness profile name.
            provider_route: Optional provider route override.
            harness_env_overrides: Optional environment variable overrides.
            benchmark_tags: Optional tags for filtering and grouping.

        Returns:
            The created variant.

        Raises:
            VariantServiceError: If validation fails or variant already exists.
        """
        if not name:
            raise VariantServiceError("name is required")
        if not provider:
            raise VariantServiceError("provider is required")
        if not model_alias:
            raise VariantServiceError("model_alias is required")
        if not harness_profile:
            raise VariantServiceError("harness_profile is required")

        variant = VariantORM(
            name=name,
            provider=provider,
            model_alias=model_alias,
            harness_profile=harness_profile,
            provider_route=provider_route,
            harness_env_overrides=harness_env_overrides or {},
            benchmark_tags=benchmark_tags or {},
        )

        try:
            return await self._variant_repo.create(variant)
        except DuplicateIdentifierError as e:
            raise VariantServiceError(f"Variant already exists: {e}") from e
        except RepositoryError as e:
            raise VariantServiceError(f"Failed to create variant: {e}") from e

    async def get_variant(self, variant_id: UUID) -> VariantORM | None:
        """Retrieve a variant by ID.

        Args:
            variant_id: The variant UUID.

        Returns:
            The variant, or None if not found.
        """
        return await self._variant_repo.get_by_id(variant_id)

    async def get_variant_by_name(self, name: str) -> VariantORM | None:
        """Retrieve a variant by name.

        Args:
            name: The variant name.

        Returns:
            The variant, or None if not found.
        """
        return await self._variant_repo.get_by_name(name)

    async def update_variant(
        self,
        variant_id: UUID,
        **updates: dict,
    ) -> VariantORM | None:
        """Update an existing variant.

        Args:
            variant_id: The variant UUID.
            **updates: Fields to update.

        Returns:
            The updated variant, or None if not found.

        Raises:
            VariantServiceError: If the update would violate constraints.
        """
        variant = await self._variant_repo.get_by_id(variant_id)
        if variant is None:
            return None

        # Apply updates
        allowed_fields = {
            "name",
            "provider",
            "provider_route",
            "model_alias",
            "harness_profile",
            "harness_env_overrides",
            "benchmark_tags",
        }

        for field, value in updates.items():
            if field in allowed_fields and hasattr(variant, field):
                setattr(variant, field, value)

        try:
            return await self._variant_repo.update(variant)
        except DuplicateIdentifierError as e:
            raise VariantServiceError(f"Update would create duplicate: {e}") from e
        except RepositoryError as e:
            raise VariantServiceError(f"Failed to update variant: {e}") from e

    async def delete_variant(self, variant_id: UUID) -> bool:
        """Delete a variant by ID.

        Note: Variants referenced by sessions cannot be deleted.

        Args:
            variant_id: The variant UUID.

        Returns:
            True if deleted, False if not found.

        Raises:
            VariantServiceError: If the variant is referenced by sessions.
        """
        try:
            return await self._variant_repo.delete(variant_id)  # type: ignore[no-any-return]
        except ReferentialIntegrityError as e:
            raise VariantServiceError(
                "Cannot delete variant: referenced by existing sessions"
            ) from e

    async def list_variants(self, limit: int = 100, offset: int = 0) -> list[VariantORM]:
        """List all variants.

        Args:
            limit: Maximum number of variants to return.
            offset: Number of variants to skip.

        Returns:
            List of variants.
        """
        return await self._variant_repo.list_all(limit, offset)  # type: ignore[no-any-return]

    async def list_variants_by_provider(
        self, provider_name: str, limit: int = 100
    ) -> list[VariantORM]:
        """List all variants for a specific provider.

        Args:
            provider_name: The provider name to filter by.
            limit: Maximum number of variants to return.

        Returns:
            List of variants for the provider.
        """
        return await self._variant_repo.list_by_provider(provider_name, limit)  # type: ignore[no-any-return]

    async def list_variants_by_harness_profile(
        self, profile_name: str, limit: int = 100
    ) -> list[VariantORM]:
        """List all variants using a specific harness profile.

        Args:
            profile_name: The harness profile name to filter by.
            limit: Maximum number of variants to return.

        Returns:
            List of variants using the harness profile.
        """
        return await self._variant_repo.list_by_harness_profile(profile_name, limit)  # type: ignore[no-any-return]

    async def get_variant_benchmark_tags(self, variant_id: UUID) -> dict | None:
        """Get the benchmark tags for a variant.

        Args:
            variant_id: The variant UUID.

        Returns:
            The benchmark tags dictionary, or None if variant not found.
        """
        variant = await self._variant_repo.get_by_id(variant_id)
        if variant is None:
            return None
        return variant.benchmark_tags or {}

    async def update_variant_tags(self, variant_id: UUID, tags: dict) -> VariantORM | None:
        """Update the benchmark tags for a variant.

        Args:
            variant_id: The variant UUID.
            tags: New tags dictionary (replaces existing tags).

        Returns:
            The updated variant, or None if not found.
        """
        return await self.update_variant(variant_id, benchmark_tags=tags)
