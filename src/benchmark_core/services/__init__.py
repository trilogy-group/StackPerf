"""Service layer for benchmark metadata management.

This package provides services for managing canonical entities
and session lifecycle with safety guarantees.
"""

# Original ABC-based services (for backward compatibility)
from benchmark_core.services.benchmark_metadata_service import BenchmarkMetadataService
from benchmark_core.services.credential_service import CredentialService
from benchmark_core.services.experiment_service import ExperimentService
from benchmark_core.services.harness_profile_service import HarnessProfileService
from benchmark_core.services.provider_service import ProviderService
from benchmark_core.services.session_service import SessionService, SessionValidationError
from benchmark_core.services.task_card_service import TaskCardService
from benchmark_core.services.variant_service import VariantService
from benchmark_core.services_abc import (
    CredentialService as CredentialServiceABC,
)
from benchmark_core.services_abc import (
    SessionService as SessionServiceABC,
)

__all__ = [
    # Original ABC services (backward compatible)
    "SessionServiceABC",
    "CredentialServiceABC",
    # New SQL-based services
    "SessionService",
    "SessionValidationError",
    "CredentialService",
    "ProviderService",
    "VariantService",
    "ExperimentService",
    "TaskCardService",
    "HarnessProfileService",
    "BenchmarkMetadataService",
]
