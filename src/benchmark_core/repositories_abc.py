"""Repository interfaces for session, request, and artifact storage."""

from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from benchmark_core.models import Artifact, ProxyCredential, Request, Session, UsageRequest


class ProxyCredentialRepository(ABC):
    """Abstract repository for proxy credential metadata persistence.

    Note: This repository stores credential metadata (alias, tags, references)
    but NOT the actual API key secrets. Secrets are managed by LiteLLM.
    """

    @abstractmethod
    async def create(self, credential: ProxyCredential) -> ProxyCredential:
        """Persist credential metadata (without the secret key).

        Stores the key alias, metadata tags, and references for correlation.
        The actual API key is NOT stored in the benchmark database.
        """
        ...

    @abstractmethod
    async def get_by_session(self, session_id: UUID) -> ProxyCredential | None:
        """Retrieve credential metadata by session ID."""
        ...

    @abstractmethod
    async def get_by_alias(self, key_alias: str) -> ProxyCredential | None:
        """Retrieve credential metadata by key alias."""
        ...

    @abstractmethod
    async def update(self, credential: ProxyCredential) -> ProxyCredential:
        """Update credential metadata (e.g., revocation status)."""
        ...

    @abstractmethod
    async def revoke(self, session_id: UUID) -> ProxyCredential | None:
        """Mark a credential as revoked in the metadata store."""
        ...


class ArtifactRepository(ABC):
    """Abstract repository for artifact persistence."""

    @abstractmethod
    async def create(self, artifact: Artifact) -> Artifact:
        """Create a new artifact record."""
        ...

    @abstractmethod
    async def get_by_id(self, artifact_id: UUID) -> Artifact | None:
        """Retrieve an artifact by ID."""
        ...

    @abstractmethod
    async def list_by_session(self, session_id: UUID) -> list[Artifact]:
        """List all artifacts for a session."""
        ...


class SessionRepository(ABC):
    """Abstract repository for session persistence."""

    @abstractmethod
    async def create(self, session: Session) -> Session:
        """Create a new session record."""
        ...

    @abstractmethod
    async def get_by_id(self, session_id: UUID) -> Session | None:
        """Retrieve a session by ID."""
        ...

    @abstractmethod
    async def update(self, session: Session) -> Session:
        """Update an existing session."""
        ...

    @abstractmethod
    async def list_by_experiment(self, experiment_id: str) -> list[Session]:
        """List all sessions for an experiment."""
        ...


class RequestRepository(ABC):
    """Abstract repository for request persistence."""

    @abstractmethod
    async def create(self, request: Request) -> Request:
        """Create a new request record."""
        ...

    @abstractmethod
    async def get_by_request_id(self, request_id: str) -> Request | None:
        """Retrieve a request by its LiteLLM request ID."""
        ...


class UsageRequestRepository(ABC):
    """Abstract repository for usage request persistence."""

    @abstractmethod
    async def get_by_litellm_call_id(self, litellm_call_id: str) -> UsageRequest | None:
        """Retrieve a usage request by its LiteLLM call ID."""
        ...

    @abstractmethod
    async def get_by_request_id(self, request_id: str) -> UsageRequest | None:
        """Retrieve a usage request by its alternate request ID."""
        ...

    @abstractmethod
    async def create_many(self, requests: list[UsageRequest]) -> tuple[list[UsageRequest], int]:
        """Create multiple usage request records (idempotent)."""
        ...

    @abstractmethod
    async def list_by_key_alias(
        self,
        key_alias: str,
        limit: int = 1000,
        offset: int = 0,
    ) -> list[UsageRequest]:
        """List usage requests by key alias."""
        ...

    @abstractmethod
    async def list_by_litellm_key_id(
        self,
        litellm_key_id: str,
        limit: int = 1000,
        offset: int = 0,
    ) -> list[UsageRequest]:
        """List usage requests by LiteLLM key ID."""
        ...

    @abstractmethod
    async def list_by_model(
        self,
        model: str,
        limit: int = 1000,
        offset: int = 0,
    ) -> list[UsageRequest]:
        """List usage requests by resolved model."""
        ...

    @abstractmethod
    async def list_by_provider(
        self,
        provider: str,
        limit: int = 1000,
        offset: int = 0,
    ) -> list[UsageRequest]:
        """List usage requests by provider."""
        ...

    @abstractmethod
    async def list_by_benchmark_session(
        self,
        benchmark_session_id: UUID,
        limit: int = 1000,
        offset: int = 0,
    ) -> list[UsageRequest]:
        """List usage requests linked to a benchmark session."""
        ...

    @abstractmethod
    async def list_by_time_range(
        self,
        start: datetime,
        end: datetime,
        limit: int = 1000,
        offset: int = 0,
    ) -> list[UsageRequest]:
        """List usage requests within a time range."""
        ...

    @abstractmethod
    async def list_by_status(
        self,
        status: str,
        limit: int = 1000,
        offset: int = 0,
    ) -> list[UsageRequest]:
        """List usage requests by status."""
        ...

    @abstractmethod
    async def list_by_error_code(
        self,
        error_code: str,
        limit: int = 1000,
        offset: int = 0,
    ) -> list[UsageRequest]:
        """List usage requests by error code."""
        ...

    @abstractmethod
    async def count_by_key_alias(self, key_alias: str) -> int:
        """Count total usage requests for a key alias."""
        ...

    @abstractmethod
    async def count_by_model(self, model: str) -> int:
        """Count total usage requests for a model."""
        ...

    @abstractmethod
    async def delete(self, id: UUID) -> bool:
        """Delete a usage request by its ID."""
        ...

    @abstractmethod
    async def delete_by_benchmark_session(self, benchmark_session_id: UUID) -> int:
        """Delete all usage requests linked to a benchmark session."""
        ...
