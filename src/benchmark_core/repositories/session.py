"""Session repository."""

from typing import Protocol
from uuid import UUID

from benchmark_core.models import Session


class SessionRepository(Protocol):
    """Protocol for session persistence."""

    async def get(self, session_id: UUID) -> Session | None:
        """Get session by ID."""
        ...

    async def save(self, session: Session) -> Session:
        """Save session."""
        ...

    async def delete(self, session_id: UUID) -> bool:
        """Delete session by ID."""
        ...

    async def list_by_status(self, status: str) -> list[Session]:
        """List sessions by status."""
        ...

    async def list_by_experiment(self, experiment_id: UUID) -> list[Session]:
        """List sessions for an experiment."""
        ...


class InMemorySessionRepository:
    """In-memory session repository for testing and development."""

    def __init__(self) -> None:
        self._sessions: dict[UUID, Session] = {}

    async def get(self, session_id: UUID) -> Session | None:
        """Get session by ID."""
        return self._sessions.get(session_id)

    async def save(self, session: Session) -> Session:
        """Save session."""
        self._sessions[session.session_id] = session
        return session

    async def delete(self, session_id: UUID) -> bool:
        """Delete session by ID."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    async def list_by_status(self, status: str) -> list[Session]:
        """List sessions by status."""
        return [
            s for s in self._sessions.values()
            if s.status.value == status
        ]

    async def list_by_experiment(self, experiment_id: UUID) -> list[Session]:
        """List sessions for an experiment."""
        return [
            s for s in self._sessions.values()
            if s.experiment_id == experiment_id
        ]

    async def list_all(self) -> list[Session]:
        """List all sessions."""
        return list(self._sessions.values())
