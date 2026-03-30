"""Tests for artifact CLI commands."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from typer.testing import CliRunner

from benchmark_core.db.models import (
    Artifact as DBArtifact,
)
from benchmark_core.db.models import (
    Base,
)
from benchmark_core.db.models import (
    Experiment as DBExperiment,
)
from benchmark_core.db.models import (
    Session as DBSession,
)
from benchmark_core.db.models import (
    TaskCard as DBTaskCard,
)
from benchmark_core.db.models import (
    Variant as DBVariant,
)
from cli.main import app


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
def runner():
    """Create a CLI runner."""
    return CliRunner()


@pytest.fixture
def mock_env_db_url(test_engine, monkeypatch):
    """Mock the database URL to use the test engine."""
    # Patch the session factory used by CLI commands
    from benchmark_core.db import session as db_session_module

    def mock_create_engine(url, **kwargs):
        return test_engine

    monkeypatch.setattr(db_session_module, "create_database_engine", mock_create_engine)

    # Also patch in the artifact module
    from cli.commands import artifact as artifact_module

    monkeypatch.setattr(
        artifact_module, "get_db_session", lambda: db_session_module.get_db_session(test_engine)
    )

    yield test_engine


class TestArtifactRegisterCommand:
    """Tests for artifact register CLI command."""

    def test_register_artifact_with_session(self, db_session, mock_env_db_url, runner, tmp_path):
        """Test registering an artifact linked to a session."""
        # Create prerequisite records
        experiment = DBExperiment(name="artifact-exp", description="Test")
        variant = DBVariant(
            name="artifact-var",
            provider="test",
            model_alias="gpt-4",
            harness_profile="default",
        )
        task = DBTaskCard(
            name="artifact-task",
            goal="Test",
            starting_prompt="Test",
            stop_condition="Test",
        )
        db_session.add_all([experiment, variant, task])
        db_session.flush()

        session = DBSession(
            experiment_id=experiment.id,
            variant_id=variant.id,
            task_card_id=task.id,
            harness_profile="test-harness",
            repo_path="/test/repo",
            git_branch="main",
            git_commit="abc123",
            status="active",
        )
        db_session.add(session)
        db_session.commit()

        # Create a temporary file to use as artifact
        test_file = tmp_path / "test_export.json"
        test_file.write_text('{"data": "test"}')

        result = runner.invoke(
            app,
            [
                "artifact",
                "register",
                "--name",
                "test_export.json",
                "--type",
                "export",
                "--path",
                str(test_file),
                "--session",
                str(session.id),
            ],
        )

        assert result.exit_code == 0, f"Exit code: {result.exit_code}, Output: {result.output}"
        assert "Artifact registered successfully" in result.output
        assert "test_export.json" in result.output

        # Verify artifact was created in database
        artifact = db_session.query(DBArtifact).filter_by(name="test_export.json").first()
        assert artifact is not None
        assert artifact.artifact_type == "export"
        assert artifact.session_id == session.id
        assert artifact.experiment_id is None

    def test_register_artifact_with_experiment(self, db_session, mock_env_db_url, runner, tmp_path):
        """Test registering an artifact linked to an experiment."""
        experiment = DBExperiment(name="artifact-exp2", description="Test")
        db_session.add(experiment)
        db_session.commit()

        test_file = tmp_path / "report.html"
        test_file.write_text("<html>Report</html>")

        result = runner.invoke(
            app,
            [
                "artifact",
                "register",
                "--name",
                "report.html",
                "--type",
                "report",
                "--path",
                str(test_file),
                "--content-type",
                "text/html",
                "--experiment",
                str(experiment.id),
            ],
        )

        assert result.exit_code == 0, f"Exit code: {result.exit_code}, Output: {result.output}"
        assert "Artifact registered successfully" in result.output

        # Verify artifact was created
        artifact = db_session.query(DBArtifact).filter_by(name="report.html").first()
        assert artifact is not None
        assert artifact.experiment_id == experiment.id
        assert artifact.session_id is None

    def test_register_artifact_requires_session_or_experiment(
        self, mock_env_db_url, runner, tmp_path
    ):
        """Test that artifact registration requires session or experiment."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")

        result = runner.invoke(
            app,
            [
                "artifact",
                "register",
                "--name",
                "test.txt",
                "--type",
                "export",
                "--path",
                str(test_file),
            ],
        )

        assert result.exit_code != 0
        assert "Either --session or --experiment must be specified" in result.output


class TestArtifactListCommand:
    """Tests for artifact list CLI command."""

    def test_list_artifacts_by_session(self, db_session, mock_env_db_url, runner):
        """Test listing artifacts filtered by session."""
        # Create prerequisite records
        experiment = DBExperiment(name="list-exp", description="Test")
        variant = DBVariant(
            name="list-var",
            provider="test",
            model_alias="gpt-4",
            harness_profile="default",
        )
        task = DBTaskCard(
            name="list-task",
            goal="Test",
            starting_prompt="Test",
            stop_condition="Test",
        )
        db_session.add_all([experiment, variant, task])
        db_session.flush()

        session = DBSession(
            experiment_id=experiment.id,
            variant_id=variant.id,
            task_card_id=task.id,
            harness_profile="test-harness",
            repo_path="/test/repo",
            git_branch="main",
            git_commit="abc123",
            status="active",
        )
        db_session.add(session)
        db_session.flush()

        # Create some artifacts
        artifact1 = DBArtifact(
            name="export1.json",
            artifact_type="export",
            content_type="application/json",
            storage_path="/storage/export1.json",
            session_id=session.id,
            size_bytes=1024,
        )
        artifact2 = DBArtifact(
            name="export2.json",
            artifact_type="export",
            content_type="application/json",
            storage_path="/storage/export2.json",
            session_id=session.id,
            size_bytes=2048,
        )
        db_session.add_all([artifact1, artifact2])
        db_session.commit()

        result = runner.invoke(app, ["artifact", "list", "--session", str(session.id)])

        assert result.exit_code == 0, f"Exit code: {result.exit_code}, Output: {result.output}"
        assert "export1.json" in result.output
        assert "export2.json" in result.output

    def test_list_artifacts_empty(self, mock_env_db_url, runner):
        """Test listing artifacts when none exist."""
        result = runner.invoke(app, ["artifact", "list"])

        # Should show warning but not fail
        assert "No artifacts found" in result.output or result.exit_code == 0


class TestArtifactShowCommand:
    """Tests for artifact show CLI command."""

    def test_show_artifact(self, db_session, mock_env_db_url, runner):
        """Test showing artifact details."""
        experiment = DBExperiment(name="show-exp", description="Test")
        db_session.add(experiment)
        db_session.commit()

        artifact = DBArtifact(
            name="detailed_report.html",
            artifact_type="report",
            content_type="text/html",
            storage_path="/storage/reports/detailed_report.html",
            experiment_id=experiment.id,
            size_bytes=5120,
        )
        db_session.add(artifact)
        db_session.commit()

        result = runner.invoke(app, ["artifact", "show", str(artifact.id)])

        assert result.exit_code == 0, f"Exit code: {result.exit_code}, Output: {result.output}"
        assert "detailed_report.html" in result.output
        assert "report" in result.output
        assert "text/html" in result.output

    def test_show_artifact_not_found(self, mock_env_db_url, runner):
        """Test showing non-existent artifact."""
        fake_id = "550e8400-e29b-41d4-a716-446655440000"
        result = runner.invoke(app, ["artifact", "show", fake_id])

        assert result.exit_code != 0
        assert "Artifact not found" in result.output or "Exit" in result.output


class TestArtifactRemoveCommand:
    """Tests for artifact remove CLI command."""

    def test_remove_artifact_with_force(self, db_session, mock_env_db_url, runner):
        """Test removing artifact with --force flag."""
        experiment = DBExperiment(name="remove-exp", description="Test")
        db_session.add(experiment)
        db_session.commit()

        artifact = DBArtifact(
            name="old_export.json",
            artifact_type="export",
            content_type="application/json",
            storage_path="/storage/old_export.json",
            experiment_id=experiment.id,
        )
        db_session.add(artifact)
        db_session.commit()

        result = runner.invoke(app, ["artifact", "remove", str(artifact.id), "--force"])

        assert result.exit_code == 0, f"Exit code: {result.exit_code}, Output: {result.output}"
        assert "Artifact removed successfully" in result.output

        # Verify artifact was deleted
        deleted_artifact = db_session.query(DBArtifact).filter_by(id=artifact.id).first()
        assert deleted_artifact is None

    def test_remove_artifact_not_found(self, mock_env_db_url, runner):
        """Test removing non-existent artifact."""
        fake_id = "550e8400-e29b-41d4-a716-446655440000"
        result = runner.invoke(app, ["artifact", "remove", fake_id, "--force"])

        assert result.exit_code != 0
        assert "Artifact not found" in result.output or "Exit" in result.output
