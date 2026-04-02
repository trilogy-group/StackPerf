"""Service for managing Provider entities."""

from uuid import UUID

from sqlalchemy.orm import Session as SQLAlchemySession

from benchmark_core.db.models import Provider as ProviderORM
from benchmark_core.db.models import ProviderModel as ProviderModelORM
from benchmark_core.repositories.base import (
    DuplicateIdentifierError,
    RepositoryError,
)
from benchmark_core.repositories.provider_repository import SQLProviderRepository


class ProviderServiceError(Exception):
    """Raised when provider service operation fails."""

    pass


class ProviderService:
    """Service for managing provider configurations.

    Providers define upstream inference provider definitions including:
    - Name and route
    - Protocol surface (anthropic_messages or openai_responses)
    - Environment variable configuration
    - Model aliases
    """

    def __init__(
        self,
        db_session: SQLAlchemySession,
        provider_repo: SQLProviderRepository | None = None,
    ) -> None:
        """Initialize the provider service.

        Args:
            db_session: SQLAlchemy session for database operations.
            provider_repo: Optional repository instance. If not provided, one is created.
        """
        self._db_session = db_session
        self._provider_repo = provider_repo or SQLProviderRepository(db_session)

    async def create_provider(
        self,
        name: str,
        protocol_surface: str,
        upstream_base_url_env: str,
        api_key_env: str,
        route_name: str | None = None,
        routing_defaults: dict | None = None,
        models: list[dict] | None = None,
    ) -> ProviderORM:
        """Create a new provider configuration.

        Args:
            name: Unique provider name.
            protocol_surface: Either 'anthropic_messages' or 'openai_responses'.
            upstream_base_url_env: Environment variable name for the base URL.
            api_key_env: Environment variable name for the API key.
            route_name: Optional route name override.
            routing_defaults: Optional default routing parameters.
            models: Optional list of model definitions [{'alias': str, 'upstream_model': str}].

        Returns:
            The created provider with models populated.

        Raises:
            ProviderServiceError: If validation fails or provider already exists.
        """
        # Validate protocol surface
        valid_protocols = ["anthropic_messages", "openai_responses"]
        if protocol_surface not in valid_protocols:
            raise ProviderServiceError(
                f"Invalid protocol_surface '{protocol_surface}'. Must be one of: {valid_protocols}"
            )

        # Create provider entity
        provider = ProviderORM(
            name=name,
            protocol_surface=protocol_surface,
            upstream_base_url_env=upstream_base_url_env,
            api_key_env=api_key_env,
            route_name=route_name,
            routing_defaults=routing_defaults or {},
        )

        # Create model entities if provided
        model_entities: list[ProviderModelORM] = []
        if models:
            for model_def in models:
                model = ProviderModelORM(
                    alias=model_def["alias"],
                    upstream_model=model_def["upstream_model"],
                )
                model_entities.append(model)

        try:
            if model_entities:
                return await self._provider_repo.create_with_models(provider, model_entities)
            return await self._provider_repo.create(provider)
        except DuplicateIdentifierError as e:
            raise ProviderServiceError(f"Provider already exists: {e}") from e
        except RepositoryError as e:
            raise ProviderServiceError(f"Failed to create provider: {e}") from e

    async def get_provider(self, provider_id: UUID) -> ProviderORM | None:
        """Retrieve a provider by ID.

        Args:
            provider_id: The provider UUID.

        Returns:
            The provider with models loaded, or None if not found.
        """
        return await self._provider_repo.get_by_id(provider_id)

    async def get_provider_by_name(self, name: str) -> ProviderORM | None:
        """Retrieve a provider by name.

        Args:
            name: The provider name.

        Returns:
            The provider with models loaded, or None if not found.
        """
        return await self._provider_repo.get_by_name(name)

    async def update_provider(
        self,
        provider_id: UUID,
        **updates: dict,
    ) -> ProviderORM | None:
        """Update an existing provider.

        Args:
            provider_id: The provider UUID.
            **updates: Fields to update (name, protocol_surface, upstream_base_url_env, etc.).

        Returns:
            The updated provider, or None if not found.

        Raises:
            ProviderServiceError: If the update would violate constraints.
        """
        provider = await self._provider_repo.get_by_id(provider_id)
        if provider is None:
            return None

        # Apply updates
        allowed_fields = {
            "name",
            "protocol_surface",
            "upstream_base_url_env",
            "api_key_env",
            "route_name",
            "routing_defaults",
        }

        for field, value in updates.items():
            if field in allowed_fields and hasattr(provider, field):
                setattr(provider, field, value)

        try:
            return await self._provider_repo.update(provider)
        except DuplicateIdentifierError as e:
            raise ProviderServiceError(f"Update would create duplicate: {e}") from e
        except RepositoryError as e:
            raise ProviderServiceError(f"Failed to update provider: {e}") from e

    async def delete_provider(self, provider_id: UUID) -> bool:
        """Delete a provider by ID.

        Note: This will cascade to delete associated models.
        Variants referencing this provider will be prevented from deletion
        by referential integrity constraints.

        Args:
            provider_id: The provider UUID.

        Returns:
            True if deleted, False if not found.

        Raises:
            ProviderServiceError: If the provider is referenced by variants.
        """
        from benchmark_core.repositories.base import ReferentialIntegrityError

        try:
            return await self._provider_repo.delete(provider_id)  # type: ignore[no-any-return]
        except ReferentialIntegrityError as e:
            raise ProviderServiceError(
                "Cannot delete provider: referenced by existing variants"
            ) from e

    async def list_providers(self, limit: int = 100, offset: int = 0) -> list[ProviderORM]:
        """List all providers with their models.

        Args:
            limit: Maximum number of providers to return.
            offset: Number of providers to skip.

        Returns:
            List of providers with models populated.
        """
        return await self._provider_repo.list_all(limit, offset)  # type: ignore[no-any-return]

    async def add_model_to_provider(
        self, provider_id: UUID, alias: str, upstream_model: str
    ) -> ProviderORM | None:
        """Add a model to an existing provider.

        Args:
            provider_id: The provider UUID.
            alias: The model alias to add.
            upstream_model: The upstream model identifier.

        Returns:
            The updated provider, or None if provider not found.

        Raises:
            ProviderServiceError: If the model alias already exists.
        """
        provider = await self._provider_repo.get_by_id(provider_id)
        if provider is None:
            return None

        # Check for duplicate alias
        for model in provider.models:
            if model.alias == alias:
                raise ProviderServiceError(
                    f"Model alias '{alias}' already exists for provider '{provider.name}'"
                )

        model = ProviderModelORM(
            provider_id=provider_id,
            alias=alias,
            upstream_model=upstream_model,
        )
        provider.models.append(model)

        try:
            return await self._provider_repo.update(provider)
        except DuplicateIdentifierError as e:
            raise ProviderServiceError(f"Model already exists: {e}") from e

    async def get_model_upstream(self, provider_name: str, model_alias: str) -> str | None:
        """Get the upstream model identifier for a provider alias.

        Args:
            provider_name: The provider name.
            model_alias: The model alias.

        Returns:
            The upstream model identifier, or None if not found.
        """
        provider = await self._provider_repo.get_by_name(provider_name)
        if provider is None:
            return None

        for model in provider.models:
            if model.alias == model_alias:
                return model.upstream_model  # type: ignore[no-any-return]

        return None
