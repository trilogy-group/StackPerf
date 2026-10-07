"""Services package for benchmark core.

Provides session management, credential issuance, collection job services,
comprehensive benchmark metadata management, and environment rendering.
"""

# Comprehensive SQL-based services (COE-305 implementation)
from benchmark_core.services.benchmark_metadata_service import BenchmarkMetadataService

# Unified credential service (COE-370)
from benchmark_core.services.credential_service import CredentialService
from benchmark_core.services.experiment_service import ExperimentService
from benchmark_core.services.harness_profile_service import HarnessProfileService
from benchmark_core.services.provider_service import ProviderService

# Sessionless proxy key services
from benchmark_core.services.proxy_key_service import (
    LiteLLMAPIError,
    ProxyKeyService,
    ProxyKeyServiceError,
)
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
    # Sessionless proxy key services
    "ProxyKeyService",
    "ProxyKeyServiceError",
    "LiteLLMAPIError",
    # ABC services
    "CredentialService",
]
