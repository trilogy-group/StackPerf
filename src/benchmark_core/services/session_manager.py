"""Session lifecycle management service."""

from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from benchmark_core.config import Settings
from benchmark_core.models import (
    GitMetadata,
    OutcomeState,
    ProxyCredential,
    Session,
    SessionCreate,
    SessionFinalize,
    SessionNote,
    SessionStatus,
)

from .credentials import CredentialIssuer
from .git_metadata import capture_git_metadata


class SessionError(Exception):
    """Session lifecycle error."""


class SessionNotFoundError(SessionError):
    """Session not found."""


class InvalidTransitionError(SessionError):
    """Invalid status transition."""


VALID_TRANSITIONS: dict[SessionStatus, set[SessionStatus]] = {
    SessionStatus.PENDING: {SessionStatus.ACTIVE, SessionStatus.ABORTED},
    SessionStatus.ACTIVE: {
        SessionStatus.COMPLETED,
        SessionStatus.ABORTED,
        SessionStatus.INVALID,
    },
    SessionStatus.COMPLETED: {SessionStatus.FINALIZED},
    SessionStatus.ABORTED: {SessionStatus.FINALIZED},
    SessionStatus.INVALID: {SessionStatus.FINALIZED},
    SessionStatus.FINALIZED: set(),  # Terminal state
}


class SessionManager:
    """Manages session lifecycle, credentials, and metadata."""

    def __init__(
        self,
        settings: Settings | None = None,
        session_repository: Any = None,  # Avoid circular import
    ):
        self.settings = settings or Settings()
        self.credential_issuer = CredentialIssuer(settings)
        self._repository = session_repository

    async def create_session(
        self,
        create_input: SessionCreate,
        repo_path: Path | str | None = None,
    ) -> Session:
        """Create a new benchmark session.

        This creates the session record BEFORE any harness traffic starts,
        capturing benchmark metadata and git context.

        Args:
            create_input: Session creation parameters
            repo_path: Path to repository for git metadata capture

        Returns:
            Created session with credential

        Raises:
            SessionError: If session creation fails
        """
        # Capture git metadata if requested and in a repo
        git_metadata: GitMetadata | None = None
        if create_input.capture_git:
            try:
                git_metadata = capture_git_metadata(repo_path)
            except Exception:
                # Not in a git repo - that's okay
                pass

        # Create session record
        session = Session(
            operator_label=create_input.operator_label,
            git_metadata=git_metadata,
        )

        # Generate session credential
        credential = self.credential_issuer.generate_session_credential(
            session_id=str(session.session_id),
        )
        session.proxy_credential = credential

        # Transition to pending
        session.status = SessionStatus.PENDING

        # Store session (would persist via repository in full implementation)
        if self._repository:
            await self._repository.save(session)

        return session

    async def activate_session(self, session_id: UUID) -> Session:
        """Activate a pending session.

        Called when the harness is ready to start.

        Args:
            session_id: Session to activate

        Returns:
            Activated session

        Raises:
            SessionNotFoundError: Session doesn't exist
            InvalidTransitionError: Session not in pending state
        """
        session = await self._get_session(session_id)

        if session.status != SessionStatus.PENDING:
            raise InvalidTransitionError(
                f"Cannot activate session in {session.status} state"
            )

        session.status = SessionStatus.ACTIVE
        session.updated_at = datetime.utcnow()

        if self._repository:
            await self._repository.save(session)

        return session

    async def finalize_session(
        self,
        finalize_input: SessionFinalize,
    ) -> Session:
        """Finalize a session with outcome status.

        Args:
            finalize_input: Finalization parameters

        Returns:
            Finalized session

        Raises:
            SessionNotFoundError: Session doesn't exist
            InvalidTransitionError: Invalid transition from current state
        """
        session = await self._get_session(finalize_input.session_id)

        # Validate transition
        if finalize_input.status not in VALID_TRANSITIONS.get(session.status, set()):
            valid = VALID_TRANSITIONS.get(session.status, set())
            raise InvalidTransitionError(
                f"Cannot transition from {session.status} to {finalize_input.status}. "
                f"Valid transitions: {valid}"
            )

        # Apply finalization steps based on target status
        if finalize_input.status == SessionStatus.COMPLETED:
            # Normal completion
            session.status = SessionStatus.COMPLETED
        elif finalize_input.status == SessionStatus.ABORTED:
            session.status = SessionStatus.ABORTED
        elif finalize_input.status == SessionStatus.INVALID:
            session.status = SessionStatus.INVALID

        # Record outcome
        session.outcome = finalize_input.outcome
        session.ended_at = datetime.utcnow()

        # Add notes
        session.notes.extend(finalize_input.notes)

        # Transition to finalized
        session.status = SessionStatus.FINALIZED
        session.updated_at = datetime.utcnow()

        if self._repository:
            await self._repository.save(session)

        return session

    async def add_note(self, note_input: SessionNote) -> Session:
        """Add an operator note to a session.

        Args:
            note_input: Note parameters

        Returns:
            Updated session

        Raises:
            SessionNotFoundError: Session doesn't exist
        """
        session = await self._get_session(note_input.session_id)

        session.notes.append(note_input.note)
        session.updated_at = datetime.utcnow()

        if self._repository:
            await self._repository.save(session)

        return session

    async def get_session(self, session_id: UUID) -> Session:
        """Get a session by ID.

        Args:
            session_id: Session ID

        Returns:
            Session record

        Raises:
            SessionNotFoundError: Session doesn't exist
        """
        return await self._get_session(session_id)

    async def _get_session(self, session_id: UUID) -> Session:
        """Internal method to fetch session."""
        if self._repository:
            session = await self._repository.get(session_id)
            if session is None:
                raise SessionNotFoundError(f"Session {session_id} not found")
            return session
        else:
            # In-memory fallback for testing
            raise SessionNotFoundError(
                f"Session {session_id} not found (no repository configured)"
            )
