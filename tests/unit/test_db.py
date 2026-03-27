"""Tests for database models and session utilities."""

from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from benchmark_core.db.models import (
    Artifact,
    Base,
    Experiment,
    ExperimentVariant,
    HarnessProfile,
    MetricRollup,
    Provider,
    ProviderModel,
    Request,
    TaskCard,
    Variant,
)
from benchmark_core.db.models import (
    Session as DBSession,
)
from benchmark_core.db.session import (
    create_database_engine,
    get_database_url,
    get_db_session,
    init_db,
)


@pytest.fixture
def test_engine():
    """Create an in-memory SQLite engine for testing."""

    # Enable foreign key support for cascade delete to work
    def _fk_pragma_on_connect(dbapi_conn, connection_record):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    engine = create_engine("sqlite:///:memory:")
    from sqlalchemy.event import listen

    listen(engine, "connect", _fk_pragma_on_connect)
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture
def test_session(test_engine):
    """Create a database session for testing."""
    session_local = sessionmaker(bind=test_engine)
    session = session_local()
    try:
        yield session
    finally:
        session.close()


class TestDatabaseModels:
    """Test that all database models can be created and queried."""

    def test_provider_model(self, test_session):
        """Test Provider and ProviderModel creation."""
        provider = Provider(
            name="test-provider",
            protocol_surface="anthropic_messages",
            upstream_base_url_env="TEST_URL",
            api_key_env="TEST_KEY",
            routing_defaults={"timeout": 30},
        )
        test_session.add(provider)
        test_session.commit()

        # Add provider model
        model = ProviderModel(
            provider_id=provider.id,
            alias="test-model",
            upstream_model="claude-3-opus",
        )
        test_session.add(model)
        test_session.commit()

        # Verify
        retrieved = test_session.query(Provider).filter_by(name="test-provider").first()
        assert retrieved is not None
        assert retrieved.name == "test-provider"
        assert len(retrieved.models) == 1
        assert retrieved.models[0].alias == "test-model"

    def test_harness_profile(self, test_session):
        """Test HarnessProfile creation."""
        profile = HarnessProfile(
            name="test-profile",
            protocol_surface="anthropic_messages",
            base_url_env="BASE_URL",
            api_key_env="API_KEY",
            model_env="MODEL",
            extra_env={"FOO": "bar"},
            launch_checks=["check1"],
        )
        test_session.add(profile)
        test_session.commit()

        retrieved = test_session.query(HarnessProfile).filter_by(name="test-profile").first()
        assert retrieved is not None
        assert retrieved.protocol_surface == "anthropic_messages"
        assert retrieved.extra_env == {"FOO": "bar"}

    def test_variant(self, test_session):
        """Test Variant creation."""
        variant = Variant(
            name="test-variant",
            provider="test-provider",
            model_alias="test-model",
            harness_profile="test-profile",
            harness_env_overrides={"TIMEOUT": "60"},
            benchmark_tags={"harness": "v1", "provider": "p1", "model": "m1"},
        )
        test_session.add(variant)
        test_session.commit()

        retrieved = test_session.query(Variant).filter_by(name="test-variant").first()
        assert retrieved is not None
        assert retrieved.benchmark_tags["harness"] == "v1"

    def test_experiment(self, test_session):
        """Test Experiment and ExperimentVariant creation with proper FKs."""
        # Create prerequisite variant
        variant = Variant(
            name="exp-test-variant",
            provider="test-provider",
            model_alias="test-model",
            harness_profile="test-profile",
        )
        test_session.add(variant)
        test_session.flush()

        experiment = Experiment(
            name="test-experiment",
            description="Test description",
        )
        test_session.add(experiment)
        test_session.flush()

        # Link variant with proper FK
        exp_variant = ExperimentVariant(
            experiment_id=experiment.id,
            variant_id=variant.id,
        )
        test_session.add(exp_variant)
        test_session.commit()

        retrieved = test_session.query(Experiment).filter_by(name="test-experiment").first()
        assert retrieved is not None
        assert len(retrieved.experiment_variants) == 1
        assert retrieved.experiment_variants[0].variant_id == variant.id

    def test_task_card(self, test_session):
        """Test TaskCard creation."""
        task = TaskCard(
            name="test-task",
            goal="Test goal",
            starting_prompt="Test prompt",
            stop_condition="Test condition",
            session_timebox_minutes=30,
            notes=["Note 1", "Note 2"],
        )
        test_session.add(task)
        test_session.commit()

        retrieved = test_session.query(TaskCard).filter_by(name="test-task").first()
        assert retrieved is not None
        assert retrieved.notes == ["Note 1", "Note 2"]

    def test_session(self, test_session):
        """Test Session (benchmark session) creation with proper FKs."""
        # Create prerequisite records
        experiment = Experiment(name="test-exp", description="Test experiment")
        variant = Variant(
            name="test-variant",
            provider="test-provider",
            model_alias="test-model",
            harness_profile="profile-1",
        )
        task = TaskCard(
            name="test-task",
            goal="Test goal",
            starting_prompt="Test prompt",
            stop_condition="Test condition",
        )
        test_session.add_all([experiment, variant, task])
        test_session.flush()

        # Create session with proper FK references
        session = DBSession(
            experiment_id=experiment.id,
            variant_id=variant.id,
            task_card_id=task.id,
            harness_profile="profile-1",
            repo_path="/test/repo",
            git_branch="main",
            git_commit="abc123",
            git_dirty=False,
            status="active",
        )
        test_session.add(session)
        test_session.commit()

        retrieved = test_session.query(DBSession).first()
        assert retrieved is not None
        assert retrieved.status == "active"
        assert retrieved.experiment_id == experiment.id
        assert retrieved.variant_id == variant.id
        assert retrieved.task_card_id == task.id

    def test_request(self, test_session):
        """Test Request creation with foreign key to Session."""
        # Create prerequisite records first
        experiment = Experiment(name="req-test-exp", description="Test")
        variant = Variant(
            name="req-test-variant",
            provider="test-provider",
            model_alias="test-model",
            harness_profile="profile-1",
        )
        task = TaskCard(
            name="req-test-task",
            goal="Test goal",
            starting_prompt="Test prompt",
            stop_condition="Test condition",
        )
        test_session.add_all([experiment, variant, task])
        test_session.flush()

        # Create session with proper FKs
        session = DBSession(
            experiment_id=experiment.id,
            variant_id=variant.id,
            task_card_id=task.id,
            harness_profile="profile-1",
            repo_path="/test/repo",
            git_branch="main",
            git_commit="abc123",
            git_dirty=False,
            status="active",
        )
        test_session.add(session)
        test_session.flush()

        # Create request linked to session
        request = Request(
            request_id="req-123",
            session_id=session.id,
            provider="test-provider",
            model="test-model",
            timestamp=datetime.now(UTC),
            latency_ms=100.5,
            tokens_prompt=10,
            tokens_completion=20,
            error=False,
            request_metadata={"foo": "bar"},
        )
        test_session.add(request)
        test_session.commit()

        retrieved = test_session.query(Request).filter_by(request_id="req-123").first()
        assert retrieved is not None
        assert retrieved.session_id == session.id

    def test_rollup(self, test_session):
        """Test MetricRollup creation."""
        rollup = MetricRollup(
            dimension_type="session",
            dimension_id="session-1",
            metric_name="avg_latency",
            metric_value=150.5,
            sample_count=10,
        )
        test_session.add(rollup)
        test_session.commit()

        retrieved = test_session.query(MetricRollup).first()
        assert retrieved is not None
        assert retrieved.dimension_type == "session"

    def test_artifact(self, test_session):
        """Test Artifact creation with foreign key to Session."""
        # Create prerequisite records
        experiment = Experiment(name="art-test-exp", description="Test")
        variant = Variant(
            name="art-test-variant",
            provider="test-provider",
            model_alias="test-model",
            harness_profile="profile-1",
        )
        task = TaskCard(
            name="art-test-task",
            goal="Test goal",
            starting_prompt="Test prompt",
            stop_condition="Test condition",
        )
        test_session.add_all([experiment, variant, task])
        test_session.flush()

        # Create session with proper FKs
        session = DBSession(
            experiment_id=experiment.id,
            variant_id=variant.id,
            task_card_id=task.id,
            harness_profile="profile-1",
            repo_path="/test/repo",
            git_branch="main",
            git_commit="abc123",
            status="active",
        )
        test_session.add(session)
        test_session.flush()

        # Create artifact
        artifact = Artifact(
            session_id=session.id,
            artifact_type="log",
            name="test.log",
            content_type="text/plain",
            storage_path="/storage/test.log",
            size_bytes=1024,
            artifact_metadata={"format": "plain"},
        )
        test_session.add(artifact)
        test_session.commit()

        retrieved = test_session.query(Artifact).filter_by(name="test.log").first()
        assert retrieved is not None
        assert retrieved.session_id == session.id

    def test_cascade_delete(self, test_engine):
        """Test that requests and artifacts are deleted when session is deleted."""
        # Create fresh session with proper engine
        session_local = sessionmaker(bind=test_engine)
        test_session = session_local()

        # Create prerequisite records
        experiment = Experiment(name="cascade-test-exp", description="Test")
        variant = Variant(
            name="cascade-test-variant",
            provider="test-provider",
            model_alias="test-model",
            harness_profile="profile-1",
        )
        task = TaskCard(
            name="cascade-test-task",
            goal="Test goal",
            starting_prompt="Test prompt",
            stop_condition="Test condition",
        )
        test_session.add_all([experiment, variant, task])
        test_session.flush()

        # Create session with proper FKs
        session = DBSession(
            experiment_id=experiment.id,
            variant_id=variant.id,
            task_card_id=task.id,
            harness_profile="profile-1",
            repo_path="/test/repo",
            git_branch="main",
            git_commit="abc123",
            status="active",
        )
        test_session.add(session)
        test_session.flush()

        # Create request and artifact
        request = Request(
            request_id="req-1",
            session_id=session.id,
            provider="test",
            model="test",
            timestamp=datetime.now(UTC),
        )
        artifact = Artifact(
            session_id=session.id,
            artifact_type="log",
            name="test.log",
            content_type="text/plain",
            storage_path="/storage/test.log",
        )
        test_session.add(request)
        test_session.add(artifact)
        test_session.commit()

        # Verify they exist
        assert test_session.query(Request).count() == 1
        assert test_session.query(Artifact).count() == 1

        # Delete session
        test_session.delete(session)
        test_session.commit()

        # Verify cascade delete worked
        assert test_session.query(Request).count() == 0
        assert test_session.query(Artifact).count() == 0
        test_session.close()


class TestSessionUtilities:
    """Test database session utilities."""

    def test_get_database_url_default(self, monkeypatch):
        """Test that default database URL is SQLite."""
        # Clear environment
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.delenv("BENCHMARK_DATABASE_URL", raising=False)

        url = get_database_url()
        assert url.startswith("sqlite://")

    def test_get_database_url_from_env(self, monkeypatch):
        """Test that DATABASE_URL environment variable is respected."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/test")
        monkeypatch.delenv("BENCHMARK_DATABASE_URL", raising=False)

        url = get_database_url()
        assert url == "postgresql://localhost/test"

    def test_get_database_url_converts_postgres_dialect(self, monkeypatch):
        """Test that postgres:// is converted to postgresql://."""
        monkeypatch.setenv("DATABASE_URL", "postgres://localhost/test")
        monkeypatch.delenv("BENCHMARK_DATABASE_URL", raising=False)

        url = get_database_url()
        assert url == "postgresql://localhost/test"
        assert not url.startswith("postgres://")

    def test_get_database_url_benchmark_converts_postgres_dialect(self, monkeypatch):
        """Test that BENCHMARK_DATABASE_URL postgres:// is converted to postgresql://."""
        monkeypatch.setenv("BENCHMARK_DATABASE_URL", "postgres://localhost/benchmark")
        monkeypatch.delenv("DATABASE_URL", raising=False)

        url = get_database_url()
        assert url == "postgresql://localhost/benchmark"
        assert not url.startswith("postgres://")

    def test_get_database_url_benchmark_takes_precedence(self, monkeypatch):
        """Test that BENCHMARK_DATABASE_URL takes precedence."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/general")
        monkeypatch.setenv("BENCHMARK_DATABASE_URL", "postgresql://localhost/benchmark")

        url = get_database_url()
        assert url == "postgresql://localhost/benchmark"

    def test_create_database_engine_sqlite(self):
        """Test SQLite engine creation."""
        engine = create_database_engine("sqlite:///:memory:")
        assert engine is not None

    def test_init_db(self):
        """Test that init_db creates all tables."""
        engine = create_engine("sqlite:///:memory:")
        init_db(engine)

        # Verify tables exist by trying to select from them
        from sqlalchemy import inspect

        inspector = inspect(engine)
        tables = inspector.get_table_names()

        expected_tables = [
            "providers",
            "provider_models",
            "harness_profiles",
            "variants",
            "experiments",
            "experiment_variants",
            "task_cards",
            "sessions",
            "requests",
            "rollups",
            "artifacts",
        ]

        for table in expected_tables:
            assert table in tables

    def test_get_db_session(self):
        """Test the get_db_session context manager."""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)

        with get_db_session(engine) as session:
            # Create a provider
            provider = Provider(
                name="ctx-provider",
                protocol_surface="anthropic_messages",
                upstream_base_url_env="URL",
                api_key_env="KEY",
            )
            session.add(provider)

        # Verify it was committed
        verify_session = Session(bind=engine)
        result = verify_session.query(Provider).filter_by(name="ctx-provider").first()
        assert result is not None
        verify_session.close()

    def test_get_db_session_rollback_on_error(self):
        """Test that get_db_session rolls back on error."""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)

        class TestError(Exception):
            pass

        try:
            with get_db_session(engine) as session:
                provider = Provider(
                    name="rollback-provider",
                    protocol_surface="anthropic_messages",
                    upstream_base_url_env="URL",
                    api_key_env="KEY",
                )
                session.add(provider)
                raise TestError("Test exception")
        except TestError:
            pass

        # Verify the provider was not committed
        verify_session = Session(bind=engine)
        result = verify_session.query(Provider).filter_by(name="rollback-provider").first()
        assert result is None
        verify_session.close()
