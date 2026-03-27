"""Repository interfaces for session, request, and artifact storage."""

from abc import ABC, abstractmethod
from uuid import UUID

from benchmark_core.models import Artifact, Request, Session


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
    async def create_many(self, requests: list[Request]) -> list[Request]:
        """Create multiple request records (idempotent)."""
        ...

    @abstractmethod
    async def get_by_session(self, session_id: UUID) -> list[Request]:
        """Get all requests for a session."""
        ...

    @abstractmethod
    async def get_by_request_id(self, request_id: str) -> Request | None:
        """Get a request by its LiteLLM request ID."""
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

    @abstractmethod
    async def list_by_experiment(self, experiment_id: UUID) -> list[Artifact]:
        """List all artifacts for an experiment."""
        ...

    @abstractmethod
    async def delete(self, artifact_id: UUID) -> bool:
        """Delete an artifact record. Returns True if deleted."""
        ...
