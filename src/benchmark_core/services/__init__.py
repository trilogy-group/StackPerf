"""Services package for benchmark core.

Provides session management, credential issuance, collection job services,
comprehensive benchmark metadata management, and environment rendering.
"""

# Comprehensive SQL-based services (COE-305 implementation)
from benchmark_core.services.benchmark_metadata_service import BenchmarkMetadataService
from benchmark_core.services.experiment_service import ExperimentService
from benchmark_core.services.harness_profile_service import HarnessProfileService
from benchmark_core.services.provider_service import ProviderService
from benchmark_core.services.rendering import (
    EnvRenderingService,
    EnvSnippet,
    ProfileValidationError,
    RenderingError,
    render_env_for_session,
)
from benchmark_core.services.session_service import (
    CollectionJobResult,
    CollectionJobService,
    SessionService,
    SessionValidationError,
)
from benchmark_core.services.task_card_service import TaskCardService
from benchmark_core.services.variant_service import VariantService

# ABC service exports - Note: old services_abc SessionService removed, use services.session_service
from benchmark_core.services_abc import (
    CredentialService,
)

__all__ = [
    # Core SQL-based services
    "SessionService",
    "SessionValidationError",
    "ProviderService",
    "VariantService",
    "ExperimentService",
    "TaskCardService",
    "HarnessProfileService",
    "BenchmarkMetadataService",
    # Collection job services
    "CollectionJobService",
    "CollectionJobResult",
    # Rendering services
    "EnvRenderingService",
    "EnvSnippet",
    "RenderingError",
    "ProfileValidationError",
    "render_env_for_session",
    # ABC services
    "CredentialService",
]
