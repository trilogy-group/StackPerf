"""Tests for SQLAlchemy repository implementations."""

import asyncio
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session as SQLAlchemySession, sessionmaker

from benchmark_core.db.models import (
    Base,
    Experiment as DBExperiment,
    Request as DBRequest,
    Session as DBSession,
    TaskCard as DBTaskCard,
    Variant as DBVariant,
)
from benchmark_core.db.repositories import (
    SQLAlchemyRequestRepository,
    SQLAlchemySessionRepository,
)
from benchmark_core.models import Request, Session


@pytest.fixture
def test_engine():
    """Create an in-memory SQLite engine for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture
def db_session(test_engine):
    """Create a database session for testing."""
    SessionLocal = sessionmaker(bind=test_engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


class TestSQLAlchemySessionRepository:
    """Tests for SQLAlchemySessionRepository."""

    def test_create_session(self, db_session):
        """Test creating a session record."""
        # Create prerequisite records in DB
        experiment = DBExperiment(name="test-exp", description="Test")
        variant = DBVariant(
            name="test-variant",
            provider="test-provider",
            model_alias="test-model",
            harness_profile="test-profile",
        )
        task = DBTaskCard(
            name="test-task",
            goal="Test goal",
            starting_prompt="Test prompt",
            stop_condition="Test condition",
        )
        db_session.add_all([experiment, variant, task])
        db_session.flush()

        # Create session using repository
        repository = SQLAlchemySessionRepository(db_session)
        session = Session(
            experiment_id=str(experiment.id),
            variant_id=str(variant.id),
            task_card_id=str(task.id),
            harness_profile="test-profile",
            repo_path="/test/repo",
            git_branch="main",
            git_commit="abc123",
            git_dirty=False,
        )

        async def run_test():
            created = await repository.create(session)
            db_session.commit()

            assert created.session_id == session.session_id

            # Verify in database
            db_record = db_session.query(DBSession).filter_by(id=session.session_id).first()
            assert db_record is not None
            assert db_record.git_branch == "main"
            assert db_record.git_commit == "abc123"
            assert db_record.status == "active"

        asyncio.run(run_test())

    def test_get_by_id(self, db_session):
        """Test retrieving a session by ID."""
        # Create prerequisite records
        experiment = DBExperiment(name="test-exp", description="Test")
        variant = DBVariant(
            name="test-variant",
            provider="test-provider",
            model_alias="test-model",
            harness_profile="test-profile",
        )
        task = DBTaskCard(
            name="test-task",
            goal="Test goal",
            starting_prompt="Test prompt",
            stop_condition="Test condition",
        )
        db_session.add_all([experiment, variant, task])
        db_session.flush()

        # Create session in DB
        db_session_obj = DBSession(
            experiment_id=experiment.id,
            variant_id=variant.id,
            task_card_id=task.id,
            harness_profile="test-profile",
            repo_path="/test/repo",
            git_branch="main",
            git_commit="abc123",
            status="active",
        )
        db_session.add(db_session_obj)
        db_session.commit()

        # Retrieve using repository
        repository = SQLAlchemySessionRepository(db_session)

        async def run_test():
            retrieved = await repository.get_by_id(db_session_obj.id)

            assert retrieved is not None
            assert retrieved.session_id == db_session_obj.id
            assert retrieved.git_branch == "main"
            assert retrieved.status == "active"

        asyncio.run(run_test())

    def test_get_by_id_not_found(self, db_session):
        """Test retrieving a non-existent session."""
        repository = SQLAlchemySessionRepository(db_session)

        async def run_test():
            retrieved = await repository.get_by_id(uuid4())
            assert retrieved is None

        asyncio.run(run_test())

    def test_update_session(self, db_session):
        """Test updating a session."""
        # Create prerequisite records
        experiment = DBExperiment(name="test-exp", description="Test")
        variant = DBVariant(
            name="test-variant",
            provider="test-provider",
            model_alias="test-model",
            harness_profile="test-profile",
        )
        task = DBTaskCard(
            name="test-task",
            goal="Test goal",
            starting_prompt="Test prompt",
            stop_condition="Test condition",
        )
        db_session.add_all([experiment, variant, task])
        db_session.flush()

        # Create session in DB
        db_session_obj = DBSession(
            experiment_id=experiment.id,
            variant_id=variant.id,
            task_card_id=task.id,
            harness_profile="test-profile",
            repo_path="/test/repo",
            git_branch="main",
            git_commit="abc123",
            status="active",
        )
        db_session.add(db_session_obj)
        db_session.commit()

        # Update using repository
        repository = SQLAlchemySessionRepository(db_session)

        async def run_test():
            # Get the session
            session = await repository.get_by_id(db_session_obj.id)
            assert session is not None

            # Modify and update
            from datetime import UTC, datetime
            session.status = "completed"
            session.ended_at = datetime.now(UTC)

            updated = await repository.update(session)
            db_session.commit()

            assert updated.status == "completed"
            assert updated.ended_at is not None

            # Verify in database
            db_record = db_session.query(DBSession).filter_by(id=db_session_obj.id).first()
            assert db_record.status == "completed"

        asyncio.run(run_test())

    def test_list_by_experiment(self, db_session):
        """Test listing sessions by experiment."""
        # Create prerequisite records
        experiment1 = DBExperiment(name="exp-1", description="Test 1")
        experiment2 = DBExperiment(name="exp-2", description="Test 2")
        variant = DBVariant(
            name="test-variant",
            provider="test-provider",
            model_alias="test-model",
            harness_profile="test-profile",
        )
        task = DBTaskCard(
            name="test-task",
            goal="Test goal",
            starting_prompt="Test prompt",
            stop_condition="Test condition",
        )
        db_session.add_all([experiment1, experiment2, variant, task])
        db_session.flush()

        # Create sessions
        session1 = DBSession(
            experiment_id=experiment1.id,
            variant_id=variant.id,
            task_card_id=task.id,
            harness_profile="profile-1",
            repo_path="/test/repo",
            git_branch="main",
            git_commit="abc123",
            status="active",
        )
        session2 = DBSession(
            experiment_id=experiment1.id,
            variant_id=variant.id,
            task_card_id=task.id,
            harness_profile="profile-2",
            repo_path="/test/repo",
            git_branch="main",
            git_commit="abc123",
            status="active",
        )
        session3 = DBSession(
            experiment_id=experiment2.id,
            variant_id=variant.id,
            task_card_id=task.id,
            harness_profile="profile-3",
            repo_path="/test/repo",
            git_branch="main",
            git_commit="abc123",
            status="active",
        )
        db_session.add_all([session1, session2, session3])
        db_session.commit()

        # List using repository
        repository = SQLAlchemySessionRepository(db_session)

        async def run_test():
            exp1_sessions = await repository.list_by_experiment(str(experiment1.id))
            assert len(exp1_sessions) == 2

            exp2_sessions = await repository.list_by_experiment(str(experiment2.id))
            assert len(exp2_sessions) == 1

        asyncio.run(run_test())


class TestSQLAlchemyRequestRepository:
    """Tests for SQLAlchemyRequestRepository."""

    def test_create_request(self, db_session):
        """Test creating a request record."""
        # Create prerequisite records
        experiment = DBExperiment(name="test-exp", description="Test")
        variant = DBVariant(
            name="test-variant",
            provider="test-provider",
            model_alias="test-model",
            harness_profile="test-profile",
        )
        task = DBTaskCard(
            name="test-task",
            goal="Test goal",
            starting_prompt="Test prompt",
            stop_condition="Test condition",
        )
        db_session.add_all([experiment, variant, task])
        db_session.flush()

        session = DBSession(
            experiment_id=experiment.id,
            variant_id=variant.id,
            task_card_id=task.id,
            harness_profile="test-profile",
            repo_path="/test/repo",
            git_branch="main",
            git_commit="abc123",
            status="active",
        )
        db_session.add(session)
        db_session.commit()

        # Create request using repository
        repository = SQLAlchemyRequestRepository(db_session)
        request = Request(
            request_id="req-123",
            session_id=session.id,
            provider="test-provider",
            model="gpt-4",
            timestamp=datetime.now(UTC),
            latency_ms=100.0,
            tokens_prompt=50,
            tokens_completion=100,
        )

        async def run_test():
            created = await repository.create(request)
            db_session.commit()

            assert created.request_id == "req-123"

            # Verify in database
            db_record = db_session.query(DBRequest).filter_by(request_id="req-123").first()
            assert db_record is not None
            assert db_record.provider == "test-provider"
            assert db_record.latency_ms == 100.0

        asyncio.run(run_test())

    def test_create_many_requests(self, db_session):
        """Test creating multiple request records."""
        # Create prerequisite records
        experiment = DBExperiment(name="test-exp", description="Test")
        variant = DBVariant(
            name="test-variant",
            provider="test-provider",
            model_alias="test-model",
            harness_profile="test-profile",
        )
        task = DBTaskCard(
            name="test-task",
            goal="Test goal",
            starting_prompt="Test prompt",
            stop_condition="Test condition",
        )
        db_session.add_all([experiment, variant, task])
        db_session.flush()

        session = DBSession(
            experiment_id=experiment.id,
            variant_id=variant.id,
            task_card_id=task.id,
            harness_profile="test-profile",
            repo_path="/test/repo",
            git_branch="main",
            git_commit="abc123",
            status="active",
        )
        db_session.add(session)
        db_session.commit()

        # Create requests using repository
        repository = SQLAlchemyRequestRepository(db_session)
        requests = [
            Request(
                request_id=f"req-{i}",
                session_id=session.id,
                provider="test-provider",
                model="gpt-4",
                timestamp=datetime.now(UTC),
                latency_ms=100.0 + i,
            )
            for i in range(3)
        ]

        async def run_test():
            created = await repository.create_many(requests)
            db_session.commit()

            assert len(created) == 3

            # Verify in database
            db_records = db_session.query(DBRequest).filter(
                DBRequest.request_id.in_(["req-0", "req-1", "req-2"])
            ).all()
            assert len(db_records) == 3

        asyncio.run(run_test())

    def test_get_by_session(self, db_session):
        """Test getting requests by session ID."""
        # Create prerequisite records
        experiment = DBExperiment(name="test-exp", description="Test")
        variant = DBVariant(
            name="test-variant",
            provider="test-provider",
            model_alias="test-model",
            harness_profile="test-profile",
        )
        task = DBTaskCard(
            name="test-task",
            goal="Test goal",
            starting_prompt="Test prompt",
            stop_condition="Test condition",
        )
        db_session.add_all([experiment, variant, task])
        db_session.flush()

        session1 = DBSession(
            experiment_id=experiment.id,
            variant_id=variant.id,
            task_card_id=task.id,
            harness_profile="test-profile",
            repo_path="/test/repo",
            git_branch="main",
            git_commit="abc123",
            status="active",
        )
        session2 = DBSession(
            experiment_id=experiment.id,
            variant_id=variant.id,
            task_card_id=task.id,
            harness_profile="test-profile",
            repo_path="/test/repo2",
            git_branch="main",
            git_commit="abc123",
            status="active",
        )
        db_session.add_all([session1, session2])
        db_session.commit()

        # Add requests
        req1 = DBRequest(
            request_id="req-1",
            session_id=session1.id,
            provider="test",
            model="gpt-4",
            timestamp=datetime.now(UTC),
        )
        req2 = DBRequest(
            request_id="req-2",
            session_id=session1.id,
            provider="test",
            model="gpt-4",
            timestamp=datetime.now(UTC),
        )
        req3 = DBRequest(
            request_id="req-3",
            session_id=session2.id,
            provider="test",
            model="gpt-4",
            timestamp=datetime.now(UTC),
        )
        db_session.add_all([req1, req2, req3])
        db_session.commit()

        # Get using repository
        repository = SQLAlchemyRequestRepository(db_session)

        async def run_test():
            session1_requests = await repository.get_by_session(session1.id)
            assert len(session1_requests) == 2

            session2_requests = await repository.get_by_session(session2.id)
            assert len(session2_requests) == 1

        asyncio.run(run_test())

    def test_get_by_request_id(self, db_session):
        """Test getting a request by its LiteLLM request ID."""
        # Create prerequisite records
        experiment = DBExperiment(name="test-exp", description="Test")
        variant = DBVariant(
            name="test-variant",
            provider="test-provider",
            model_alias="test-model",
            harness_profile="test-profile",
        )
        task = DBTaskCard(
            name="test-task",
            goal="Test goal",
            starting_prompt="Test prompt",
            stop_condition="Test condition",
        )
        db_session.add_all([experiment, variant, task])
        db_session.flush()

        session = DBSession(
            experiment_id=experiment.id,
            variant_id=variant.id,
            task_card_id=task.id,
            harness_profile="test-profile",
            repo_path="/test/repo",
            git_branch="main",
            git_commit="abc123",
            status="active",
        )
        db_session.add(session)
        db_session.commit()

        req = DBRequest(
            request_id="litellm-req-123",
            session_id=session.id,
            provider="test",
            model="gpt-4",
            timestamp=datetime.now(UTC),
            latency_ms=150.0,
        )
        db_session.add(req)
        db_session.commit()

        # Get using repository
        repository = SQLAlchemyRequestRepository(db_session)

        async def run_test():
            retrieved = await repository.get_by_request_id("litellm-req-123")

            assert retrieved is not None
            assert retrieved.request_id == "litellm-req-123"
            assert retrieved.latency_ms == 150.0

        asyncio.run(run_test())
