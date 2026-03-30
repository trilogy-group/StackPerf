"""Tests for export CLI commands."""

import json
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from typer.testing import CliRunner

from benchmark_core.db.models import (
    Artifact,
    Base,
    Experiment,
    Request,
    TaskCard,
    Variant,
)
from benchmark_core.db.models import (
    Session as DBSession,
)
from cli.main import app

runner = CliRunner()


@pytest.fixture
def test_engine():
    """Create an in-memory SQLite engine for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture
def db_session(test_engine):
    """Create a database session for testing."""
    session_local = sessionmaker(bind=test_engine)
    session = session_local()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def mock_env_db_url(test_engine, monkeypatch, db_session):
    """Mock the database URL to use the test engine."""
    from benchmark_core.db import session as db_session_module
    from cli.commands import export as export_module

    def mock_create_engine(url, **kwargs):
        return test_engine

    monkeypatch.setattr(db_session_module, "create_database_engine", mock_create_engine)

    # Create a context manager that returns the same session
    from contextlib import contextmanager

    @contextmanager
    def mock_get_db_session(engine=None):
        try:
            yield db_session
            db_session.commit()
        except Exception:
            db_session.rollback()
            raise

    monkeypatch.setattr(export_module, "get_db_session", mock_get_db_session)

    yield test_engine


@pytest.fixture
def sample_data(db_session):
    """Create sample data for testing."""
    # Create experiment
    experiment = Experiment(
        name="export-test-exp",
        description="Test experiment",
    )
    db_session.add(experiment)
    db_session.flush()

    # Create variant
    variant = Variant(
        name="export-test-variant",
        provider="openai",
        model_alias="gpt-4",
        harness_profile="default",
    )
    db_session.add(variant)
    db_session.flush()

    # Create task card
    task_card = TaskCard(
        name="export-test-task",
        goal="Test",
        starting_prompt="Test",
        stop_condition="Test",
    )
    db_session.add(task_card)
    db_session.flush()

    # Create session
    session = DBSession(
        experiment_id=experiment.id,
        variant_id=variant.id,
        task_card_id=task_card.id,
        harness_profile="test-harness",
        repo_path="/test/repo",
        git_branch="main",
        git_commit="abc123def456",
        git_dirty=False,
        status="completed",
        started_at=datetime.now(UTC) - timedelta(hours=1),
        ended_at=datetime.now(UTC),
    )
    db_session.add(session)
    db_session.flush()

    # Create requests
    for i in range(2):
        request = Request(
            request_id=f"req-{i}",
            session_id=session.id,
            provider="openai",
            model="gpt-4",
            timestamp=datetime.now(UTC) - timedelta(minutes=30 - i * 10),
            latency_ms=100.0 + i * 50,
            tokens_prompt=100,
            tokens_completion=50,
            error=False,
        )
        db_session.add(request)

    db_session.commit()

    return {
        "experiment": experiment,
        "variant": variant,
        "task_card": task_card,
        "session": session,
    }


class TestExportSessionCommand:
    """Tests for export session CLI command."""

    def test_export_session_json(self, mock_env_db_url, db_session, sample_data, tmp_path):
        """Test exporting session to JSON format."""
        output_dir = tmp_path / "exports"

        result = runner.invoke(
            app,
            [
                "export",
                "session",
                str(sample_data["session"].id),
                "--output",
                str(output_dir),
                "--format",
                "json",
                "--no-register",  # Skip artifact registration for simplicity
            ],
        )

        assert result.exit_code == 0, f"Exit code: {result.exit_code}, Output: {result.output}"
        assert "Exported to" in result.output
        assert ".json" in result.output

        # Verify file was created
        json_files = list(output_dir.glob("session_*.json"))
        assert len(json_files) == 1

        # Verify content
        with open(json_files[0]) as f:
            data = json.load(f)
            assert "session" in data
            assert data["session"]["status"] == "completed"

    def test_export_session_csv(self, mock_env_db_url, db_session, sample_data, tmp_path):
        """Test exporting session to CSV format."""
        output_dir = tmp_path / "exports"

        result = runner.invoke(
            app,
            [
                "export",
                "session",
                str(sample_data["session"].id),
                "--output",
                str(output_dir),
                "--format",
                "csv",
                "--no-register",
            ],
        )

        assert result.exit_code == 0, f"Exit code: {result.exit_code}, Output: {result.output}"
        assert ".csv" in result.output

        # Verify file was created
        csv_files = list(output_dir.glob("session_*.csv"))
        assert len(csv_files) == 1

    def test_export_session_with_artifact_registration(
        self, mock_env_db_url, db_session, sample_data, tmp_path
    ):
        """Test that artifact registration works."""
        output_dir = tmp_path / "exports"

        result = runner.invoke(
            app,
            [
                "export",
                "session",
                str(sample_data["session"].id),
                "--output",
                str(output_dir),
                "--format",
                "json",
                "--register",
            ],
        )

        assert result.exit_code == 0, f"Exit code: {result.exit_code}, Output: {result.output}"
        assert "Artifact registered" in result.output

        # Verify artifact was created
        # Need to refresh the session to see the artifact
        db_session.expire_all()
        artifacts = db_session.query(Artifact).filter_by(session_id=sample_data["session"].id).all()
        assert len(artifacts) >= 1
        assert any(a.artifact_type == "export" for a in artifacts)

    def test_export_session_invalid_id(self, mock_env_db_url, tmp_path):
        """Test exporting with invalid session ID."""
        from uuid import uuid4

        result = runner.invoke(
            app,
            [
                "export",
                "session",
                str(uuid4()),
                "--output",
                str(tmp_path),
                "--no-register",
            ],
        )

        assert result.exit_code != 0
        assert "Error" in result.output or "not found" in result.output.lower()

    def test_export_session_no_requests(self, mock_env_db_url, sample_data, tmp_path):
        """Test exporting session without request data."""
        output_dir = tmp_path / "exports"

        result = runner.invoke(
            app,
            [
                "export",
                "session",
                str(sample_data["session"].id),
                "--output",
                str(output_dir),
                "--format",
                "json",
                "--no-requests",
                "--no-register",
            ],
        )

        assert result.exit_code == 0

        # Verify file was created
        json_files = list(output_dir.glob("session_*.json"))
        assert len(json_files) == 1

        with open(json_files[0]) as f:
            data = json.load(f)
            assert "requests" not in data or len(data.get("requests", [])) == 0


class TestExportExperimentCommand:
    """Tests for export experiment CLI command."""

    def test_export_experiment_json(self, mock_env_db_url, sample_data, tmp_path):
        """Test exporting experiment to JSON format."""
        output_dir = tmp_path / "exports"

        result = runner.invoke(
            app,
            [
                "export",
                "experiment",
                str(sample_data["experiment"].id),
                "--output",
                str(output_dir),
                "--format",
                "json",
                "--no-register",
            ],
        )

        assert result.exit_code == 0, f"Exit code: {result.exit_code}, Output: {result.output}"
        assert "Exported to" in result.output

        # Verify file was created
        json_files = list(output_dir.glob("experiment_*.json"))
        assert len(json_files) == 1

        # Verify content
        with open(json_files[0]) as f:
            data = json.load(f)
            assert "experiment" in data
            assert data["experiment"]["name"] == "export-test-exp"
            assert "sessions" in data

    def test_export_experiment_csv(self, mock_env_db_url, sample_data, tmp_path):
        """Test exporting experiment to CSV format."""
        output_dir = tmp_path / "exports"

        result = runner.invoke(
            app,
            [
                "export",
                "experiment",
                str(sample_data["experiment"].id),
                "--output",
                str(output_dir),
                "--format",
                "csv",
                "--no-register",
            ],
        )

        assert result.exit_code == 0
        assert ".csv" in result.output

        # Verify file was created
        csv_files = list(output_dir.glob("experiment_*.csv"))
        assert len(csv_files) == 1

    def test_export_experiment_with_requests(self, mock_env_db_url, sample_data, tmp_path):
        """Test exporting experiment with request data."""
        output_dir = tmp_path / "exports"

        result = runner.invoke(
            app,
            [
                "export",
                "experiment",
                str(sample_data["experiment"].id),
                "--output",
                str(output_dir),
                "--format",
                "json",
                "--requests",
                "--no-register",
            ],
        )

        assert result.exit_code == 0

        # Verify content includes requests
        json_files = list(output_dir.glob("experiment_*.json"))
        with open(json_files[0]) as f:
            data = json.load(f)
            assert "sessions" in data
            assert len(data["sessions"]) > 0
            assert "requests" in data["sessions"][0]

    def test_export_experiment_with_artifact_registration(
        self, mock_env_db_url, db_session, sample_data, tmp_path
    ):
        """Test that artifact registration works for experiments."""
        output_dir = tmp_path / "exports"

        result = runner.invoke(
            app,
            [
                "export",
                "experiment",
                str(sample_data["experiment"].id),
                "--output",
                str(output_dir),
                "--format",
                "json",
                "--register",
            ],
        )

        assert result.exit_code == 0, f"Exit code: {result.exit_code}, Output: {result.output}"
        assert "Artifact registered" in result.output

        # Verify artifact was created
        db_session.expire_all()
        artifacts = (
            db_session.query(Artifact).filter_by(experiment_id=sample_data["experiment"].id).all()
        )
        assert len(artifacts) >= 1


class TestExportComparisonCommand:
    """Tests for export comparison CLI command (alias for experiment)."""

    def test_comparison_alias(self, mock_env_db_url, sample_data, tmp_path):
        """Test that comparison command delegates to experiment."""
        output_dir = tmp_path / "exports"

        result = runner.invoke(
            app,
            [
                "export",
                "comparison",
                "--experiment",
                str(sample_data["experiment"].id),
                "--output",
                str(output_dir),
                "--format",
                "json",
            ],
        )

        assert result.exit_code == 0, f"Exit code: {result.exit_code}, Output: {result.output}"
        assert "Exported to" in result.output

        # Verify file was created
        json_files = list(output_dir.glob("experiment_*.json"))
        assert len(json_files) == 1
