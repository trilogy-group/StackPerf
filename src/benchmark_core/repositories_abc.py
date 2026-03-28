"""Repository interfaces for session, request, and artifact storage."""

from abc import ABC, abstractmethod
from uuid import UUID

from benchmark_core.models import Artifact, ProxyCredential, Request, Session


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
    async def get_by_id(self, request_id: UUID) -> Request | None:
        """Retrieve a request by ID."""
        ...
