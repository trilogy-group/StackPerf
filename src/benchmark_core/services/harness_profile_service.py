"""Service for managing HarnessProfile entities."""

from uuid import UUID

from sqlalchemy.orm import Session as SQLAlchemySession

from benchmark_core.db.models import HarnessProfile as HarnessProfileORM
from benchmark_core.repositories.base import (
    DuplicateIdentifierError,
    RepositoryError,
)
from benchmark_core.repositories.harness_profile_repository import SQLHarnessProfileRepository


class HarnessProfileServiceError(Exception):
    """Raised when harness profile service operation fails."""

    pass


class HarnessProfileService:
    """Service for managing harness profile configurations.

    Harness profiles define how a harness is configured to talk to the proxy:
    - Protocol surface (anthropic_messages or openai_responses)
    - Environment variable configuration
    - Launch checks
    - Rendering format (shell or dotenv)
    """

    def __init__(
        self,
        db_session: SQLAlchemySession,
        harness_profile_repo: SQLHarnessProfileRepository | None = None,
    ) -> None:
        """Initialize the harness profile service.

        Args:
            db_session: SQLAlchemy session for database operations.
            harness_profile_repo: Optional repository instance. If not provided, one is created.
        """
        self._db_session = db_session
        self._harness_profile_repo = harness_profile_repo or SQLHarnessProfileRepository(db_session)

    async def create_harness_profile(
        self,
        name: str,
        protocol_surface: str,
        base_url_env: str,
        api_key_env: str,
        model_env: str,
        extra_env: dict | None = None,
        render_format: str = "shell",
        launch_checks: list[str] | None = None,
    ) -> HarnessProfileORM:
        """Create a new harness profile.

        Args:
            name: Unique profile name.
            protocol_surface: Either 'anthropic_messages' or 'openai_responses'.
            base_url_env: Environment variable name for the base URL.
            api_key_env: Environment variable name for the API key.
            model_env: Environment variable name for the model.
            extra_env: Optional additional environment variables.
            render_format: Either 'shell' or 'dotenv'.
            launch_checks: Optional list of pre-launch check commands.

        Returns:
            The created harness profile.

        Raises:
            HarnessProfileServiceError: If validation fails or profile already exists.
        """
        # Validate protocol surface
        valid_protocols = ["anthropic_messages", "openai_responses"]
        if protocol_surface not in valid_protocols:
            raise HarnessProfileServiceError(
                f"Invalid protocol_surface '{protocol_surface}'. Must be one of: {valid_protocols}"
            )

        # Validate render format
        valid_formats = ["shell", "dotenv"]
        if render_format not in valid_formats:
            raise HarnessProfileServiceError(
                f"Invalid render_format '{render_format}'. Must be one of: {valid_formats}"
            )

        if not name:
            raise HarnessProfileServiceError("name is required")
        if not base_url_env:
            raise HarnessProfileServiceError("base_url_env is required")
        if not api_key_env:
            raise HarnessProfileServiceError("api_key_env is required")
        if not model_env:
            raise HarnessProfileServiceError("model_env is required")

        profile = HarnessProfileORM(
            name=name,
            protocol_surface=protocol_surface,
            base_url_env=base_url_env,
            api_key_env=api_key_env,
            model_env=model_env,
            extra_env=extra_env or {},
            render_format=render_format,
            launch_checks=launch_checks or [],
        )

        try:
            return await self._harness_profile_repo.create(profile)
        except DuplicateIdentifierError as e:
            raise HarnessProfileServiceError(f"HarnessProfile already exists: {e}") from e
        except RepositoryError as e:
            raise HarnessProfileServiceError(f"Failed to create harness profile: {e}") from e

    async def get_harness_profile(self, profile_id: UUID) -> HarnessProfileORM | None:
        """Retrieve a harness profile by ID.

        Args:
            profile_id: The profile UUID.

        Returns:
            The harness profile, or None if not found.
        """
        return await self._harness_profile_repo.get_by_id(profile_id)

    async def get_harness_profile_by_name(self, name: str) -> HarnessProfileORM | None:
        """Retrieve a harness profile by name.

        Args:
            name: The profile name.

        Returns:
            The harness profile, or None if not found.
        """
        return await self._harness_profile_repo.get_by_name(name)

    async def update_harness_profile(
        self,
        profile_id: UUID,
        **updates: dict,
    ) -> HarnessProfileORM | None:
        """Update an existing harness profile.

        Args:
            profile_id: The profile UUID.
            **updates: Fields to update.

        Returns:
            The updated profile, or None if not found.

        Raises:
            HarnessProfileServiceError: If the update would violate constraints.
        """
        profile = await self._harness_profile_repo.get_by_id(profile_id)
        if profile is None:
            return None

        # Validate protocol surface if being updated
        if "protocol_surface" in updates:
            valid_protocols = ["anthropic_messages", "openai_responses"]
            if updates["protocol_surface"] not in valid_protocols:
                raise HarnessProfileServiceError(
                    f"Invalid protocol_surface '{updates['protocol_surface']}'. "
                    f"Must be one of: {valid_protocols}"
                )

        # Validate render format if being updated
        if "render_format" in updates:
            valid_formats = ["shell", "dotenv"]
            if updates["render_format"] not in valid_formats:
                raise HarnessProfileServiceError(
                    f"Invalid render_format '{updates['render_format']}'. "
                    f"Must be one of: {valid_formats}"
                )

        # Apply updates
        allowed_fields = {
            "name",
            "protocol_surface",
            "base_url_env",
            "api_key_env",
            "model_env",
            "extra_env",
            "render_format",
            "launch_checks",
        }

        for field, value in updates.items():
            if field in allowed_fields and hasattr(profile, field):
                setattr(profile, field, value)

        try:
            return await self._harness_profile_repo.update(profile)
        except DuplicateIdentifierError as e:
            raise HarnessProfileServiceError(f"Update would create duplicate: {e}") from e
        except RepositoryError as e:
            raise HarnessProfileServiceError(f"Failed to update harness profile: {e}") from e

    async def delete_harness_profile(self, profile_id: UUID) -> bool:
        """Delete a harness profile by ID.

        Args:
            profile_id: The profile UUID.

        Returns:
            True if deleted, False if not found.
        """
        return await self._harness_profile_repo.delete(profile_id)  # type: ignore[no-any-return]

    async def list_harness_profiles(
        self, limit: int = 100, offset: int = 0
    ) -> list[HarnessProfileORM]:
        """List all harness profiles.

        Args:
            limit: Maximum number of profiles to return.
            offset: Number of profiles to skip.

        Returns:
            List of harness profiles.
        """
        return await self._harness_profile_repo.list_all(limit, offset)  # type: ignore[no-any-return]

    async def list_harness_profiles_by_protocol(
        self, protocol: str, limit: int = 100
    ) -> list[HarnessProfileORM]:
        """List all harness profiles for a specific protocol surface.

        Args:
            protocol: The protocol surface to filter by.
            limit: Maximum number of profiles to return.

        Returns:
            List of harness profiles using the specified protocol.
        """
        return await self._harness_profile_repo.list_by_protocol(protocol, limit)  # type: ignore[no-any-return]

    async def render_env_snippet(
        self,
        profile_id: UUID,
        credential: str,
        proxy_base_url: str,
        model: str,
    ) -> dict[str, str] | None:
        """Render environment variable snippet for a harness profile.

        Args:
            profile_id: The profile UUID.
            credential: The proxy credential to use.
            proxy_base_url: The proxy base URL.
            model: The model identifier.

        Returns:
            Dictionary of environment variables, or None if profile not found.
        """
        profile = await self._harness_profile_repo.get_by_id(profile_id)
        if profile is None:
            return None

        env_vars: dict[str, str] = {
            profile.base_url_env: proxy_base_url,
            profile.api_key_env: credential,
            profile.model_env: model,
        }

        # Add extra environment variables
        if profile.extra_env:
            env_vars.update(profile.extra_env)

        return env_vars

    async def validate_harness_profile_exists(self, profile_id: UUID) -> bool:
        """Check if a harness profile exists.

        Args:
            profile_id: The profile UUID.

        Returns:
            True if the profile exists.
        """
        return await self._harness_profile_repo.exists(profile_id)  # type: ignore[no-any-return]

    async def get_harness_profile_config(self, profile_id: UUID) -> dict | None:
        """Get the full configuration for a harness profile.

        Args:
            profile_id: The profile UUID.

        Returns:
            Dictionary with profile configuration, or None if not found.
        """
        profile = await self._harness_profile_repo.get_by_id(profile_id)
        if profile is None:
            return None

        return {
            "id": str(profile.id),
            "name": profile.name,
            "protocol_surface": profile.protocol_surface,
            "base_url_env": profile.base_url_env,
            "api_key_env": profile.api_key_env,
            "model_env": profile.model_env,
            "extra_env": profile.extra_env or {},
            "render_format": profile.render_format,
            "launch_checks": profile.launch_checks or [],
            "created_at": profile.created_at.isoformat() if profile.created_at else None,
            "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
        }
