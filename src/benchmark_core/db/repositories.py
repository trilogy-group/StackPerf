"""SQLAlchemy repository implementations for session and request storage."""

from uuid import UUID

from sqlalchemy.orm import Session as SQLAlchemySession

from benchmark_core.db.models import (
    Request as DBRequest,
)
from benchmark_core.db.models import (
    Session as DBSession,
)
from benchmark_core.models import Request, Session
from benchmark_core.repositories import RequestRepository, SessionRepository


class SQLAlchemySessionRepository(SessionRepository):
    """SQLAlchemy implementation of SessionRepository."""

    def __init__(self, db_session: SQLAlchemySession) -> None:
        self._session = db_session

    async def create(self, session: Session) -> Session:
        """Create a new session record in the database."""
        db_session = DBSession(
            id=session.session_id,
            experiment_id=UUID(session.experiment_id)
            if isinstance(session.experiment_id, str)
            else session.experiment_id,
            variant_id=UUID(session.variant_id)
            if isinstance(session.variant_id, str)
            else session.variant_id,
            task_card_id=UUID(session.task_card_id)
            if isinstance(session.task_card_id, str)
            else session.task_card_id,
            harness_profile=session.harness_profile,
            repo_path=session.repo_path,
            git_branch=session.git_branch,
            git_commit=session.git_commit,
            git_dirty=session.git_dirty,
            operator_label=session.operator_label,
            proxy_credential_id=session.proxy_credential_id,
            started_at=session.started_at,
            ended_at=session.ended_at,
            status=session.status,
        )
        self._session.add(db_session)
        self._session.flush()
        return session

    async def get_by_id(self, session_id: UUID) -> Session | None:
        """Retrieve a session by ID from the database."""
        db_session = self._session.query(DBSession).filter_by(id=session_id).first()
        if db_session is None:
            return None

        return Session(
            session_id=db_session.id,
            experiment_id=str(db_session.experiment_id),
            variant_id=str(db_session.variant_id),
            task_card_id=str(db_session.task_card_id),
            harness_profile=db_session.harness_profile,
            repo_path=db_session.repo_path,
            git_branch=db_session.git_branch,
            git_commit=db_session.git_commit,
            git_dirty=db_session.git_dirty,
            operator_label=db_session.operator_label,
            proxy_credential_id=db_session.proxy_credential_id,
            started_at=db_session.started_at,
            ended_at=db_session.ended_at,
            status=db_session.status,
        )

    async def update(self, session: Session) -> Session:
        """Update an existing session in the database."""
        db_session = self._session.query(DBSession).filter_by(id=session.session_id).first()
        if db_session is None:
            raise ValueError(f"Session {session.session_id} not found")

        db_session.experiment_id = (
            UUID(session.experiment_id)
            if isinstance(session.experiment_id, str)
            else session.experiment_id
        )
        db_session.variant_id = (
            UUID(session.variant_id) if isinstance(session.variant_id, str) else session.variant_id
        )
        db_session.task_card_id = (
            UUID(session.task_card_id)
            if isinstance(session.task_card_id, str)
            else session.task_card_id
        )
        db_session.harness_profile = session.harness_profile
        db_session.repo_path = session.repo_path
        db_session.git_branch = session.git_branch
        db_session.git_commit = session.git_commit
        db_session.git_dirty = session.git_dirty
        db_session.operator_label = session.operator_label
        db_session.proxy_credential_id = session.proxy_credential_id
        db_session.started_at = session.started_at
        db_session.ended_at = session.ended_at
        db_session.status = session.status

        self._session.flush()
        return session

    async def list_by_experiment(self, experiment_id: str) -> list[Session]:
        """List all sessions for an experiment from the database."""
        exp_uuid = UUID(experiment_id) if isinstance(experiment_id, str) else experiment_id
        db_sessions = self._session.query(DBSession).filter_by(experiment_id=exp_uuid).all()

        return [
            Session(
                session_id=s.id,
                experiment_id=str(s.experiment_id),
                variant_id=str(s.variant_id),
                task_card_id=str(s.task_card_id),
                harness_profile=s.harness_profile,
                repo_path=s.repo_path,
                git_branch=s.git_branch,
                git_commit=s.git_commit,
                git_dirty=s.git_dirty,
                operator_label=s.operator_label,
                proxy_credential_id=s.proxy_credential_id,
                started_at=s.started_at,
                ended_at=s.ended_at,
                status=s.status,
            )
            for s in db_sessions
        ]


class SQLAlchemyRequestRepository(RequestRepository):
    """SQLAlchemy implementation of RequestRepository."""

    def __init__(self, db_session: SQLAlchemySession) -> None:
        self._session = db_session

    async def create(self, request: Request) -> Request:
        """Create a new request record in the database."""
        db_request = DBRequest(
            request_id=request.request_id,
            session_id=request.session_id,
            provider=request.provider,
            model=request.model,
            timestamp=request.timestamp,
            latency_ms=request.latency_ms,
            ttft_ms=request.ttft_ms,
            tokens_prompt=request.tokens_prompt,
            tokens_completion=request.tokens_completion,
            error=request.error,
            error_message=request.error_message,
            cache_hit=request.cache_hit,
            request_metadata=request.metadata,
        )
        self._session.add(db_request)
        self._session.flush()
        return request

    async def create_many(self, requests: list[Request]) -> list[Request]:
        """Create multiple request records in the database."""
        db_requests = [
            DBRequest(
                request_id=r.request_id,
                session_id=r.session_id,
                provider=r.provider,
                model=r.model,
                timestamp=r.timestamp,
                latency_ms=r.latency_ms,
                ttft_ms=r.ttft_ms,
                tokens_prompt=r.tokens_prompt,
                tokens_completion=r.tokens_completion,
                error=r.error,
                error_message=r.error_message,
                cache_hit=r.cache_hit,
                request_metadata=r.metadata,
            )
            for r in requests
        ]
        self._session.add_all(db_requests)
        self._session.flush()
        return requests

    async def get_by_session(self, session_id: UUID) -> list[Request]:
        """Get all requests for a session from the database."""
        db_requests = self._session.query(DBRequest).filter_by(session_id=session_id).all()

        return [
            Request(
                request_id=r.request_id,
                session_id=r.session_id,
                provider=r.provider,
                model=r.model,
                timestamp=r.timestamp,
                latency_ms=r.latency_ms,
                ttft_ms=r.ttft_ms,
                tokens_prompt=r.tokens_prompt,
                tokens_completion=r.tokens_completion,
                error=r.error,
                error_message=r.error_message,
                cache_hit=r.cache_hit,
                metadata=r.request_metadata,
            )
            for r in db_requests
        ]

    async def get_by_request_id(self, request_id: str) -> Request | None:
        """Get a request by its LiteLLM request ID from the database."""
        db_request = self._session.query(DBRequest).filter_by(request_id=request_id).first()
        if db_request is None:
            return None

        return Request(
            request_id=db_request.request_id,
            session_id=db_request.session_id,
            provider=db_request.provider,
            model=db_request.model,
            timestamp=db_request.timestamp,
            latency_ms=db_request.latency_ms,
            ttft_ms=db_request.ttft_ms,
            tokens_prompt=db_request.tokens_prompt,
            tokens_completion=db_request.tokens_completion,
            error=db_request.error,
            error_message=db_request.error_message,
            cache_hit=db_request.cache_hit,
            metadata=db_request.request_metadata,
        )
