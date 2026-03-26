"""Service for managing all benchmark metadata entities.

This service provides a unified interface for creating and managing
canonical entities (providers, variants, experiments, task cards,
harness profiles) and their relationships.
"""

from uuid import UUID

from sqlalchemy.orm import Session as SQLAlchemySession

from benchmark_core.db.models import (
    Experiment as ExperimentORM,
)
from benchmark_core.db.models import (
    HarnessProfile as HarnessProfileORM,
)
from benchmark_core.db.models import (
    Provider as ProviderORM,
)
from benchmark_core.db.models import (
    TaskCard as TaskCardORM,
)
from benchmark_core.db.models import (
    Variant as VariantORM,
)
from benchmark_core.repositories.experiment_repository import SQLExperimentRepository
from benchmark_core.repositories.harness_profile_repository import SQLHarnessProfileRepository
from benchmark_core.repositories.provider_repository import SQLProviderRepository
from benchmark_core.repositories.task_card_repository import SQLTaskCardRepository
from benchmark_core.repositories.variant_repository import SQLVariantRepository
from benchmark_core.services.experiment_service import ExperimentService
from benchmark_core.services.harness_profile_service import HarnessProfileService
from benchmark_core.services.provider_service import ProviderService
from benchmark_core.services.task_card_service import TaskCardService
from benchmark_core.services.variant_service import VariantService


class BenchmarkMetadataService:
    """Unified service for managing benchmark metadata entities.

    This service orchestrates all metadata services and provides:
    - Atomic creation of related entities
    - Validation of entity relationships
    - Cross-entity queries and summaries
    - Safe deletion with dependency checking

    Example usage:
        service = BenchmarkMetadataService(db_session)

        # Create a complete benchmark setup
        provider = await service.create_provider_with_models(...)
        harness = await service.create_harness_profile(...)
        variant = await service.create_variant(...)
        task_card = await service.create_task_card(...)
        experiment = await service.create_experiment_with_variants(
            name="comparison",
            variant_ids=[variant.id]
        )
    """

    def __init__(
        self,
        db_session: SQLAlchemySession,
        provider_service: ProviderService | None = None,
        variant_service: VariantService | None = None,
        experiment_service: ExperimentService | None = None,
        task_card_service: TaskCardService | None = None,
        harness_profile_service: HarnessProfileService | None = None,
    ) -> None:
        """Initialize the metadata service with all sub-services.

        Args:
            db_session: SQLAlchemy session for database operations.
            provider_service: Optional provider service instance.
            variant_service: Optional variant service instance.
            experiment_service: Optional experiment service instance.
            task_card_service: Optional task card service instance.
            harness_profile_service: Optional harness profile service instance.
        """
        self._db_session = db_session
        self._provider_service = provider_service or ProviderService(
            db_session, SQLProviderRepository(db_session)
        )
        self._variant_service = variant_service or VariantService(
            db_session, SQLVariantRepository(db_session)
        )
        self._experiment_service = experiment_service or ExperimentService(
            db_session, SQLExperimentRepository(db_session)
        )
        self._task_card_service = task_card_service or TaskCardService(
            db_session, SQLTaskCardRepository(db_session)
        )
        self._harness_profile_service = harness_profile_service or HarnessProfileService(
            db_session, SQLHarnessProfileRepository(db_session)
        )

    # Provider operations
    async def create_provider_with_models(
        self,
        name: str,
        protocol_surface: str,
        upstream_base_url_env: str,
        api_key_env: str,
        models: list[dict],
        route_name: str | None = None,
        routing_defaults: dict | None = None,
    ) -> ProviderORM:
        """Create a provider with its model aliases atomically.

        Args:
            name: Unique provider name.
            protocol_surface: Protocol surface type.
            upstream_base_url_env: Base URL environment variable.
            api_key_env: API key environment variable.
            models: List of model definitions [{'alias': str, 'upstream_model': str}].
            route_name: Optional route name.
            routing_defaults: Optional routing defaults.

        Returns:
            The created provider with models.
        """
        return await self._provider_service.create_provider(
            name=name,
            protocol_surface=protocol_surface,
            upstream_base_url_env=upstream_base_url_env,
            api_key_env=api_key_env,
            route_name=route_name,
            routing_defaults=routing_defaults,
            models=models,
        )

    async def get_provider(self, provider_id: UUID) -> ProviderORM | None:
        """Get a provider by ID."""
        return await self._provider_service.get_provider(provider_id)

    async def get_provider_by_name(self, name: str) -> ProviderORM | None:
        """Get a provider by name."""
        return await self._provider_service.get_provider_by_name(name)

    # Harness Profile operations
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
        """Create a harness profile.

        Args:
            name: Unique profile name.
            protocol_surface: Protocol surface type.
            base_url_env: Base URL environment variable.
            api_key_env: API key environment variable.
            model_env: Model environment variable.
            extra_env: Optional extra environment variables.
            render_format: 'shell' or 'dotenv'.
            launch_checks: Optional launch check commands.

        Returns:
            The created harness profile.
        """
        return await self._harness_profile_service.create_harness_profile(
            name=name,
            protocol_surface=protocol_surface,
            base_url_env=base_url_env,
            api_key_env=api_key_env,
            model_env=model_env,
            extra_env=extra_env,
            render_format=render_format,
            launch_checks=launch_checks,
        )

    async def get_harness_profile(self, profile_id: UUID) -> HarnessProfileORM | None:
        """Get a harness profile by ID."""
        return await self._harness_profile_service.get_harness_profile(profile_id)

    async def get_harness_profile_by_name(self, name: str) -> HarnessProfileORM | None:
        """Get a harness profile by name."""
        return await self._harness_profile_service.get_harness_profile_by_name(name)

    # Variant operations
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
        """Create a variant configuration.

        Args:
            name: Unique variant name.
            provider: Provider name.
            model_alias: Model alias.
            harness_profile: Harness profile name.
            provider_route: Optional provider route override.
            harness_env_overrides: Optional environment overrides.
            benchmark_tags: Optional benchmark tags.

        Returns:
            The created variant.
        """
        return await self._variant_service.create_variant(
            name=name,
            provider=provider,
            model_alias=model_alias,
            harness_profile=harness_profile,
            provider_route=provider_route,
            harness_env_overrides=harness_env_overrides,
            benchmark_tags=benchmark_tags,
        )

    async def get_variant(self, variant_id: UUID) -> VariantORM | None:
        """Get a variant by ID."""
        return await self._variant_service.get_variant(variant_id)

    async def get_variant_by_name(self, name: str) -> VariantORM | None:
        """Get a variant by name."""
        return await self._variant_service.get_variant_by_name(name)

    # Task Card operations
    async def create_task_card(
        self,
        name: str,
        goal: str,
        starting_prompt: str,
        stop_condition: str,
        repo_path: str | None = None,
        session_timebox_minutes: int | None = None,
        notes: list[str] | None = None,
    ) -> TaskCardORM:
        """Create a task card definition.

        Args:
            name: Unique task card name.
            goal: Task goal description.
            starting_prompt: Starting prompt.
            stop_condition: Stop condition.
            repo_path: Optional repo path.
            session_timebox_minutes: Optional time limit.
            notes: Optional notes.

        Returns:
            The created task card.
        """
        return await self._task_card_service.create_task_card(
            name=name,
            goal=goal,
            starting_prompt=starting_prompt,
            stop_condition=stop_condition,
            repo_path=repo_path,
            session_timebox_minutes=session_timebox_minutes,
            notes=notes,
        )

    async def get_task_card(self, task_card_id: UUID) -> TaskCardORM | None:
        """Get a task card by ID."""
        return await self._task_card_service.get_task_card(task_card_id)

    async def get_task_card_by_name(self, name: str) -> TaskCardORM | None:
        """Get a task card by name."""
        return await self._task_card_service.get_task_card_by_name(name)

    # Experiment operations
    async def create_experiment(
        self,
        name: str,
        description: str = "",
        variant_ids: list[UUID] | None = None,
    ) -> ExperimentORM:
        """Create an experiment with optional variant associations.

        Args:
            name: Unique experiment name.
            description: Optional description.
            variant_ids: Optional list of variant UUIDs.

        Returns:
            The created experiment.
        """
        return await self._experiment_service.create_experiment(
            name=name,
            description=description,
            variant_ids=variant_ids,
        )

    async def get_experiment(self, experiment_id: UUID) -> ExperimentORM | None:
        """Get an experiment by ID."""
        return await self._experiment_service.get_experiment(experiment_id)

    async def get_experiment_by_name(self, name: str) -> ExperimentORM | None:
        """Get an experiment by name."""
        return await self._experiment_service.get_experiment_by_name(name)

    async def add_variant_to_experiment(self, experiment_id: UUID, variant_id: UUID) -> None:
        """Add a variant to an experiment."""
        await self._experiment_service.add_variant_to_experiment(experiment_id, variant_id)

    # Cross-entity operations
    async def validate_benchmark_configuration(
        self, experiment_id: UUID, variant_id: UUID, task_card_id: UUID
    ) -> dict:
        """Validate a complete benchmark configuration.

        Checks that all referenced entities exist and form a valid configuration.

        Args:
            experiment_id: The experiment UUID.
            variant_id: The variant UUID.
            task_card_id: The task card UUID.

        Returns:
            Validation result with 'valid' boolean and 'errors' list.
        """
        errors: list[str] = []

        experiment = await self._experiment_service.get_experiment(experiment_id)
        if experiment is None:
            errors.append(f"Experiment '{experiment_id}' does not exist")

        variant = await self._variant_service.get_variant(variant_id)
        if variant is None:
            errors.append(f"Variant '{variant_id}' does not exist")

        task_card = await self._task_card_service.get_task_card(task_card_id)
        if task_card is None:
            errors.append(f"TaskCard '{task_card_id}' does not exist")

        # Check variant is in experiment if both exist
        if experiment and variant:
            variant_ids = await self._experiment_service.get_experiment_variant_ids(experiment_id)
            if variant_ids and variant_id not in variant_ids:
                errors.append(
                    f"Variant '{variant_id}' is not associated with experiment '{experiment_id}'"
                )

        # Check provider and harness profile exist
        if variant:
            provider = await self._provider_service.get_provider_by_name(variant.provider)
            if provider is None:
                errors.append(f"Provider '{variant.provider}' for variant does not exist")

            harness = await self._harness_profile_service.get_harness_profile_by_name(
                variant.harness_profile
            )
            if harness is None:
                errors.append(
                    f"HarnessProfile '{variant.harness_profile}' for variant does not exist"
                )

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "experiment": experiment,
            "variant": variant,
            "task_card": task_card,
        }

    async def get_benchmark_summary(self, experiment_id: UUID) -> dict | None:
        """Get a summary of an experiment and its configuration.

        Args:
            experiment_id: The experiment UUID.

        Returns:
            Dictionary with experiment summary, or None if not found.
        """
        experiment = await self._experiment_service.get_experiment_with_variants(experiment_id)
        if experiment is None:
            return None

        variants: list[dict] = []
        for assoc in experiment.experiment_variants:
            variant = await self._variant_service.get_variant(assoc.variant_id)
            if variant:
                variants.append(
                    {
                        "id": str(variant.id),
                        "name": variant.name,
                        "provider": variant.provider,
                        "model_alias": variant.model_alias,
                        "harness_profile": variant.harness_profile,
                        "benchmark_tags": variant.benchmark_tags,
                    }
                )

        return {
            "id": str(experiment.id),
            "name": experiment.name,
            "description": experiment.description,
            "created_at": experiment.created_at.isoformat() if experiment.created_at else None,
            "variant_count": len(variants),
            "variants": variants,
        }

    async def list_all_configurations(self) -> dict:
        """List all benchmark metadata configurations.

        Returns:
            Dictionary with lists of all entity types.
        """
        providers = await self._provider_service.list_providers(limit=1000)
        harness_profiles = await self._harness_profile_service.list_harness_profiles(limit=1000)
        variants = await self._variant_service.list_variants(limit=1000)
        experiments = await self._experiment_service.list_experiments(limit=1000)
        task_cards = await self._task_card_service.list_task_cards(limit=1000)

        return {
            "providers": [{"id": str(p.id), "name": p.name} for p in providers],
            "harness_profiles": [{"id": str(h.id), "name": h.name} for h in harness_profiles],
            "variants": [{"id": str(v.id), "name": v.name} for v in variants],
            "experiments": [{"id": str(e.id), "name": e.name} for e in experiments],
            "task_cards": [{"id": str(t.id), "name": t.name} for t in task_cards],
        }

    async def delete_variant_safe(self, variant_id: UUID) -> dict:
        """Delete a variant with dependency checking.

        Args:
            variant_id: The variant UUID to delete.

        Returns:
            Dictionary with 'success' boolean and 'message'.
        """
        from benchmark_core.repositories.base import ReferentialIntegrityError

        try:
            deleted = await self._variant_service.delete_variant(variant_id)
            if deleted:
                return {"success": True, "message": f"Variant {variant_id} deleted"}
            return {"success": False, "message": f"Variant {variant_id} not found"}
        except ReferentialIntegrityError:
            return {
                "success": False,
                "message": f"Cannot delete variant {variant_id}: referenced by existing sessions or experiments",
            }
