"""Repository interfaces for session and request storage."""

from abc import ABC, abstractmethod
from uuid import UUID

from benchmark_core.models import ProxyCredential, Request, Session


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
