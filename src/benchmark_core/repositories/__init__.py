"""Repository layer for benchmark data access.

This package provides both abstract interfaces and SQLAlchemy-based
repository implementations for all canonical entities defined in
the benchmark schema.
"""

# Abstract interfaces (from original repositories module at package level)
from benchmark_core.repositories.artifact_repository import SQLArtifactRepository
from benchmark_core.repositories.base import (
    AbstractRepository,
    DuplicateIdentifierError,
    EntityNotFoundError,
    ReferentialIntegrityError,
    RepositoryError,
    SQLAlchemyRepository,
)
from benchmark_core.repositories.experiment_repository import SQLExperimentRepository
from benchmark_core.repositories.harness_profile_repository import SQLHarnessProfileRepository
from benchmark_core.repositories.provider_repository import SQLProviderRepository
from benchmark_core.repositories.request_repository import SQLRequestRepository
from benchmark_core.repositories.session_repository import SQLSessionRepository
from benchmark_core.repositories.task_card_repository import SQLTaskCardRepository
from benchmark_core.repositories.variant_repository import SQLVariantRepository
from benchmark_core.repositories_abc import (
    ArtifactRepository,
    RequestRepository,
    SessionRepository,
)

__all__ = [
    # Abstract interfaces
    "SessionRepository",
    "RequestRepository",
    "ArtifactRepository",
    # Base classes and exceptions
    "AbstractRepository",
    "SQLAlchemyRepository",
    "RepositoryError",
    "DuplicateIdentifierError",
    "EntityNotFoundError",
    "ReferentialIntegrityError",
    # SQL implementations
    "SQLSessionRepository",
    "SQLRequestRepository",
    "SQLProviderRepository",
    "SQLVariantRepository",
    "SQLExperimentRepository",
    "SQLTaskCardRepository",
    "SQLHarnessProfileRepository",
    "SQLArtifactRepository",
]
