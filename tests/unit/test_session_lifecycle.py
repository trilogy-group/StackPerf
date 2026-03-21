"""Unit tests for session lifecycle.

Tests the canonical session lifecycle:
- pending -> active -> completed -> finalized
- pending -> aborted -> finalized
- active -> invalid -> finalized
- invalid transitions should raise errors
"""

import pytest
from uuid import UUID

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
from benchmark_core.services import (
    InvalidTransitionError,
    SessionManager,
    SessionNotFoundError,
)
from benchmark_core.repositories import InMemorySessionRepository


class TestSessionLifecycle:
    """Test session lifecycle transitions."""

    @pytest.fixture
    def repository(self):
        return InMemorySessionRepository()

    @pytest.fixture
    def manager(self, repository):
        from benchmark_core.config import Settings
        return SessionManager(settings=Settings(), session_repository=repository)

    @pytest.mark.asyncio
    async def test_create_session_generates_metadata(self, manager):
        """Session creation writes benchmark metadata before harness launch."""
        create_input = SessionCreate(
            operator_label="test-operator",
            capture_git=False,
        )

        session = await manager.create_session(create_input)

        assert session.session_id is not None
        assert session.status == SessionStatus.PENDING
        assert session.operator_label == "test-operator"
        assert session.started_at is not None
        assert session.proxy_credential is not None

    @pytest.mark.asyncio
    async def test_create_session_captures_git_metadata(self, manager):
        """Git metadata is captured from the active repository."""
        create_input = SessionCreate(
            operator_label="test-operator",
            capture_git=True,
        )

        session = await manager.create_session(create_input)

        # Git metadata may be None if not in a git repo
        # But the attempt should be made
        # In test environment, we're in a git repo
        assert session.git_metadata is not None
        assert session.git_metadata.repo_root is not None
        assert session.git_metadata.branch is not None
        assert session.git_metadata.commit_sha is not None

    @pytest.mark.asyncio
    async def test_session_gets_unique_credential(self, manager, repository):
        """Every created session gets a unique proxy credential."""
        create_input = SessionCreate(capture_git=False)

        session1 = await manager.create_session(create_input.copy())
        session2 = await manager.create_session(create_input.copy())

        cred1 = session1.proxy_credential
        cred2 = session2.proxy_credential

        assert cred1 is not None
        assert cred2 is not None
        assert cred1.key_alias != cred2.key_alias
        assert cred1.virtual_key_id != cred2.virtual_key_id

    @pytest.mark.asyncio
    async def test_credential_metadata_can_join_to_session(self, manager):
        """Key alias and metadata can be joined back to the session."""
        create_input = SessionCreate(
            experiment_name="test-experiment",
            variant_name="test-variant",
            capture_git=False,
        )

        session = await manager.create_session(create_input)
        cred = session.proxy_credential

        assert cred is not None
        assert cred.metadata["session_id"] == str(session.session_id)
        assert "created_at" in cred.metadata

    @pytest.mark.asyncio
    async def test_finalize_completed_session(self, manager, repository):
        """Session finalization records status and end time."""
        create_input = SessionCreate(capture_git=False)
        session = await manager.create_session(create_input)

        # Activate first
        await repository.save(session)
        session = await manager.activate_session(session.session_id)

        # Finalize as completed
        finalize_input = SessionFinalize(
            session_id=session.session_id,
            status=SessionStatus.COMPLETED,
            outcome=OutcomeState.SUCCESS,
            notes=["Task completed successfully"],
        )

        finalized = await manager.finalize_session(finalize_input)

        assert finalized.status == SessionStatus.FINALIZED
        assert finalized.outcome == OutcomeState.SUCCESS
        assert finalized.ended_at is not None
        assert "Task completed successfully" in finalized.notes

    @pytest.mark.asyncio
    async def test_finalize_aborted_session(self, manager, repository):
        """Operators can finalize a session with abort outcome."""
        create_input = SessionCreate(capture_git=False)
        session = await manager.create_session(create_input)
        await repository.save(session)

        finalize_input = SessionFinalize(
            session_id=session.session_id,
            status=SessionStatus.ABORTED,
            outcome=OutcomeState.FAILED,
            notes=["Operator cancelled"],
        )

        finalized = await manager.finalize_session(finalize_input)

        assert finalized.status == SessionStatus.FINALIZED
        assert finalized.outcome == OutcomeState.FAILED

    @pytest.mark.asyncio
    async def test_finalize_invalid_session(self, manager, repository):
        """Invalid sessions remain visible for audit but can be excluded."""
        create_input = SessionCreate(capture_git=False)
        session = await manager.create_session(create_input)
        await repository.save(session)
        session = await manager.activate_session(session.session_id)

        finalize_input = SessionFinalize(
            session_id=session.session_id,
            status=SessionStatus.INVALID,
            outcome=OutcomeState.ERROR,
            notes=["Wrong endpoint configuration"],
        )

        finalized = await manager.finalize_session(finalize_input)

        assert finalized.status == SessionStatus.FINALIZED
        assert finalized.outcome == OutcomeState.ERROR
        assert not finalized.is_comparison_eligible()

    @pytest.mark.asyncio
    async def test_invalid_transition_raises_error(self, manager, repository):
        """Invalid lifecycle transitions raise InvalidTransitionError."""
        create_input = SessionCreate(capture_git=False)
        session = await manager.create_session(create_input)
        await repository.save(session)

        # Try to finalize without going through proper states
        finalize_input = SessionFinalize(
            session_id=session.session_id,
            status=SessionStatus.FINALIZED,
            outcome=OutcomeState.SUCCESS,
        )

        with pytest.raises(InvalidTransitionError) as exc_info:
            await manager.finalize_session(finalize_input)

        assert "Cannot transition" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_add_note_to_session(self, manager, repository):
        """Operators can add notes to sessions."""
        create_input = SessionCreate(capture_git=False)
        session = await manager.create_session(create_input)
        await repository.save(session)

        note_input = SessionNote(
            session_id=session.session_id,
            note="Interesting observation about the task",
        )

        updated = await manager.add_note(note_input)

        assert len(updated.notes) == 1
        assert "Interesting observation" in updated.notes[0]

    @pytest.mark.asyncio
    async def test_session_not_found_raises_error(self, manager):
        """SessionNotFoundError for non-existent session."""
        from uuid import uuid4

        with pytest.raises(SessionNotFoundError):
            await manager.get_session(uuid4())


class TestOutcomeStates:
    """Test outcome state validation and comparison eligibility."""

    def test_success_is_comparison_eligible(self):
        """Successful sessions are eligible for comparisons."""
        session = Session(
            status=SessionStatus.FINALIZED,
            outcome=OutcomeState.SUCCESS,
        )
        assert session.is_comparison_eligible()

    def test_partial_is_comparison_eligible(self):
        """Partial success sessions are eligible for comparisons."""
        session = Session(
            status=SessionStatus.FINALIZED,
            outcome=OutcomeState.PARTIAL,
        )
        assert session.is_comparison_eligible()

    def test_failed_is_comparison_eligible(self):
        """Failed sessions are eligible for comparisons (different from excluded)."""
        session = Session(
            status=SessionStatus.FINALIZED,
            outcome=OutcomeState.FAILED,
        )
        assert session.is_comparison_eligible()

    def test_excluded_not_comparison_eligible(self):
        """Excluded sessions are not comparison eligible."""
        session = Session(
            status=SessionStatus.FINALIZED,
            outcome=OutcomeState.EXCLUDED,
        )
        assert not session.is_comparison_eligible()

    def test_error_not_comparison_eligible(self):
        """Error outcome sessions are not comparison eligible."""
        session = Session(
            status=SessionStatus.FINALIZED,
            outcome=OutcomeState.ERROR,
        )
        assert not session.is_comparison_eligible()

    def test_non_finalized_not_comparison_eligible(self):
        """Non-finalized sessions are not comparison eligible."""
        session = Session(
            status=SessionStatus.COMPLETED,
            outcome=OutcomeState.SUCCESS,
        )
        assert not session.is_comparison_eligible()
