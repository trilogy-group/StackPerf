"""Services package for benchmark core.

Provides session management, credential issuance, collection job services,
and comprehensive benchmark metadata management.
"""

# Comprehensive SQL-based services (COE-305 implementation)
from benchmark_core.services.benchmark_metadata_service import BenchmarkMetadataService
from benchmark_core.services.credential_service import CredentialService
from benchmark_core.services.experiment_service import ExperimentService
from benchmark_core.services.harness_profile_service import HarnessProfileService
from benchmark_core.services.provider_service import ProviderService
from benchmark_core.services.session_service import (
    CollectionJobResult,
    CollectionJobService,
    SessionService,
    SessionValidationError,
)
from benchmark_core.services.task_card_service import TaskCardService
from benchmark_core.services.variant_service import VariantService

# ABC services for interface contracts (backward compatible)
from benchmark_core.services_abc import (
    CredentialService as CredentialServiceABC,
    SessionService as SessionServiceABC,
)

__all__ = [
    # ABC services (backward compatible)
    "SessionServiceABC",
    "CredentialServiceABC",
    # Core SQL-based services
    "SessionService",
    "SessionValidationError",
    "CredentialService",
    "ProviderService",
    "VariantService",
    "ExperimentService",
    "TaskCardService",
    "HarnessProfileService",
    "BenchmarkMetadataService",
    # Collection job services
    "CollectionJobService",
    "CollectionJobResult",
]