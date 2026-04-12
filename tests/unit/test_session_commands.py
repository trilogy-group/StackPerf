"""Tests for session CLI commands."""

from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from typer.testing import CliRunner

from benchmark_core.db.models import (
    Base,
)
from benchmark_core.db.models import (
    Experiment as DBExperiment,
)
from benchmark_core.db.models import (
    HarnessProfile as DBHarnessProfile,
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
    # We need to patch the get_db_session function to use our test engine
    # Since the CLI imports at module level, we patch the function used by session commands
    # ruff: noqa: PLC0415 (imports used for patching must be local)
    from benchmark_core.db import session as db_session_module
    from cli import commands

    # Store original
    original_get_db_session = db_session_module.get_db_session

    def mock_get_db_session(engine=None):
        if engine is None:
            engine = test_engine
        return original_get_db_session(engine)

    # Patch the function used by CLI commands
    monkeypatch.setattr(db_session_module, "get_db_session", mock_get_db_session)
    monkeypatch.setattr(commands.session, "get_db_session", mock_get_db_session)

    return test_engine


class TestSessionCreateCommand:
    """Tests for session create CLI command."""

    def test_create_session_with_names(self, db_session, mock_env_db_url, runner):
        """Test creating a session using experiment/variant/task names."""
        # Create prerequisite records
        experiment = DBExperiment(name="cli-test-exp", description="Test")
        variant = DBVariant(
            name="cli-test-var",
            provider="test-provider",
            model_alias="gpt-4",
            harness_profile="default",
        )
        task = DBTaskCard(
            name="cli-test-task",
            goal="Test goal",
            starting_prompt="Test prompt",
            stop_condition="Test condition",
        )
        db_session.add_all([experiment, variant, task])
        db_session.commit()

        result = runner.invoke(
            app,
            [
                "session",
                "create",
                "--experiment",
                "cli-test-exp",
                "--variant",
                "cli-test-var",
                "--task-card",
                "cli-test-task",
                "--harness",
                "test-harness",
                "--label",
                "test-label",
            ],
        )

        assert result.exit_code == 0, f"Exit code: {result.exit_code}, Output: {result.output}"
        assert "Creating benchmark session" in result.output
        assert "Session created successfully" in result.output

        # Verify session was created in database
        session = db_session.query(DBSession).first()
        assert session is not None
        assert session.harness_profile == "test-harness"
        assert session.operator_label == "test-label"
        assert session.status == "active"
        assert session.git_branch is not None
        assert session.git_commit is not None

    def test_create_session_with_uuids(self, db_session, mock_env_db_url, runner):
        """Test creating a session using UUIDs."""
        # Create prerequisite records
        experiment = DBExperiment(name="uuid-test-exp", description="Test")
        variant = DBVariant(
            name="uuid-test-var",
            provider="test-provider",
            model_alias="gpt-4",
            harness_profile="default",
        )
        task = DBTaskCard(
            name="uuid-test-task",
            goal="Test goal",
            starting_prompt="Test prompt",
            stop_condition="Test condition",
        )
        db_session.add_all([experiment, variant, task])
        db_session.commit()

        result = runner.invoke(
            app,
            [
                "session",
                "create",
                "--experiment",
                str(experiment.id),
                "--variant",
                str(variant.id),
                "--task-card",
                str(task.id),
                "--harness",
                "test-harness",
            ],
        )

        assert result.exit_code == 0, f"Exit code: {result.exit_code}, Output: {result.output}"
        assert "Session created successfully" in result.output

    def test_create_session_experiment_not_found(self, mock_env_db_url, runner):
        """Test error when experiment doesn't exist."""
        result = runner.invoke(
            app,
            [
                "session",
                "create",
                "--experiment",
                "nonexistent-exp",
                "--variant",
                "some-var",
                "--task-card",
                "some-task",
                "--harness",
                "test-harness",
            ],
        )

        assert result.exit_code != 0
        assert "Experiment not found" in result.output or "Invalid value" in result.output


class TestSessionListCommand:
    """Tests for session list CLI command."""

    def test_list_sessions(self, db_session, mock_env_db_url, runner):
        """Test listing sessions."""
        # Create prerequisite records
        experiment = DBExperiment(name="list-test-exp", description="Test")
        variant = DBVariant(
            name="list-test-var",
            provider="test-provider",
            model_alias="gpt-4",
            harness_profile="default",
        )
        task = DBTaskCard(
            name="list-test-task",
            goal="Test goal",
            starting_prompt="Test prompt",
            stop_condition="Test condition",
        )
        db_session.add_all([experiment, variant, task])
        db_session.flush()

        # Create sessions
        session1 = DBSession(
            experiment_id=experiment.id,
            variant_id=variant.id,
            task_card_id=task.id,
            harness_profile="harness-1",
            repo_path="/test/repo",
            git_branch="main",
            git_commit="abc123",
            status="active",
        )
        session2 = DBSession(
            experiment_id=experiment.id,
            variant_id=variant.id,
            task_card_id=task.id,
            harness_profile="harness-2",
            repo_path="/test/repo",
            git_branch="main",
            git_commit="abc123",
            status="completed",
            ended_at=datetime.now(UTC),
        )
        db_session.add_all([session1, session2])
        db_session.commit()

        result = runner.invoke(app, ["session", "list"])

        assert result.exit_code == 0, f"Exit code: {result.exit_code}, Output: {result.output}"
        assert "Sessions" in result.output
        assert "harness-1" in result.output
        assert "harness-2" in result.output

    def test_list_sessions_empty(self, mock_env_db_url, runner):
        """Test listing when no sessions exist."""
        result = runner.invoke(app, ["session", "list"])

        assert result.exit_code == 0
        assert "No sessions found" in result.output

    def test_list_sessions_filter_by_experiment(self, db_session, mock_env_db_url, runner):
        """Test filtering sessions by experiment."""
        # Create prerequisite records
        experiment1 = DBExperiment(name="filter-exp-1", description="Test 1")
        experiment2 = DBExperiment(name="filter-exp-2", description="Test 2")
        variant = DBVariant(
            name="filter-var",
            provider="test",
            model_alias="gpt-4",
            harness_profile="default",
        )
        task = DBTaskCard(
            name="filter-task",
            goal="Test",
            starting_prompt="Test",
            stop_condition="Test",
        )
        db_session.add_all([experiment1, experiment2, variant, task])
        db_session.flush()

        # Create sessions for different experiments
        session1 = DBSession(
            experiment_id=experiment1.id,
            variant_id=variant.id,
            task_card_id=task.id,
            harness_profile="harness-1",
            repo_path="/test/repo",
            git_branch="main",
            git_commit="abc123",
            status="active",
        )
        session2 = DBSession(
            experiment_id=experiment2.id,
            variant_id=variant.id,
            task_card_id=task.id,
            harness_profile="harness-2",
            repo_path="/test/repo",
            git_branch="main",
            git_commit="abc123",
            status="active",
        )
        db_session.add_all([session1, session2])
        db_session.commit()

        result = runner.invoke(app, ["session", "list", "--experiment", "filter-exp-1"])

        assert result.exit_code == 0, f"Exit code: {result.exit_code}, Output: {result.output}"
        assert "harness-1" in result.output
        # harness-2 should not appear when filtering by experiment1


class TestSessionShowCommand:
    """Tests for session show CLI command."""

    def test_show_session(self, db_session, mock_env_db_url, runner):
        """Test showing session details."""
        # Create prerequisite records
        experiment = DBExperiment(name="show-test-exp", description="Test")
        variant = DBVariant(
            name="show-test-var",
            provider="test",
            model_alias="gpt-4",
            harness_profile="default",
        )
        task = DBTaskCard(
            name="show-test-task",
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
            git_commit="abc123def4567890",
            git_dirty=True,
            operator_label="test-label",
            status="active",
        )
        db_session.add(session)
        db_session.commit()

        result = runner.invoke(app, ["session", "show", str(session.id)])

        assert result.exit_code == 0, f"Exit code: {result.exit_code}, Output: {result.output}"
        assert str(session.id) in result.output
        assert "test-harness" in result.output
        assert "main" in result.output
        assert "abc123de" in result.output  # Short commit hash
        assert "test-label" in result.output

    def test_show_session_not_found(self, mock_env_db_url, runner):
        """Test showing non-existent session."""
        result = runner.invoke(app, ["session", "show", "550e8400-e29b-41d4-a716-446655440000"])

        assert result.exit_code != 0
        assert "Session not found" in result.output or "Exit" in result.output


class TestSessionFinalizeCommand:
    """Tests for session finalize CLI command."""

    def test_finalize_session(self, db_session, mock_env_db_url, runner):
        """Test finalizing a session."""
        # Create prerequisite records
        experiment = DBExperiment(name="finalize-test-exp", description="Test")
        variant = DBVariant(
            name="finalize-test-var",
            provider="test",
            model_alias="gpt-4",
            harness_profile="default",
        )
        task = DBTaskCard(
            name="finalize-test-task",
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

        result = runner.invoke(app, ["session", "finalize", str(session.id)])

        assert result.exit_code == 0, f"Exit code: {result.exit_code}, Output: {result.output}"
        assert "Finalizing session" in result.output
        assert "Session finalized successfully" in result.output

        # Verify session was updated in database
        db_session.refresh(session)
        assert session.status == "completed"
        assert session.ended_at is not None

    def test_finalize_session_with_custom_status(self, db_session, mock_env_db_url, runner):
        """Test finalizing a session with custom status."""
        # Create prerequisite records
        experiment = DBExperiment(name="finalize-status-exp", description="Test")
        variant = DBVariant(
            name="finalize-status-var",
            provider="test",
            model_alias="gpt-4",
            harness_profile="default",
        )
        task = DBTaskCard(
            name="finalize-status-task",
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

        result = runner.invoke(
            app, ["session", "finalize", str(session.id), "--outcome", "invalid"]
        )

        assert result.exit_code == 0, f"Exit code: {result.exit_code}, Output: {result.output}"

        # Verify session was updated with outcome_state
        db_session.refresh(session)
        assert session.outcome_state == "invalid"

    def test_finalize_session_not_found(self, mock_env_db_url, runner):
        """Test finalizing non-existent session."""
        result = runner.invoke(app, ["session", "finalize", "550e8400-e29b-41d4-a716-446655440000"])

        assert result.exit_code != 0
        assert "Session not found" in result.output or "Exit" in result.output

    def test_finalize_session_with_status_parameter(self, db_session, mock_env_db_url, runner):
        """Test finalizing a session with --status parameter (backward compatibility)."""
        # Create prerequisite records
        experiment = DBExperiment(name="finalize-status-param-exp", description="Test")
        variant = DBVariant(
            name="finalize-status-param-var",
            provider="test",
            model_alias="gpt-4",
            harness_profile="default",
        )
        task = DBTaskCard(
            name="finalize-status-param-task",
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

        # Test with --status failed (backward compatible)
        result = runner.invoke(app, ["session", "finalize", str(session.id), "--status", "failed"])

        assert result.exit_code == 0, f"Exit code: {result.exit_code}, Output: {result.output}"

        # Verify session was updated with status
        db_session.refresh(session)
        assert session.status == "failed"
        assert session.outcome_state == "valid"  # Default outcome


class TestSessionEnvCommand:
    """Tests for session env CLI command."""

    def test_env_command(self, db_session, mock_env_db_url, runner):
        """Test rendering environment for a session."""
        # Create prerequisite records
        harness = DBHarnessProfile(
            name="test-harness",
            protocol_surface="openai_responses",
            base_url_env="OPENAI_API_BASE",
            api_key_env="OPENAI_API_KEY",
            model_env="OPENAI_MODEL",
            extra_env={},
            render_format="shell",
            launch_checks=[],
        )
        experiment = DBExperiment(name="env-test-exp", description="Test")
        variant = DBVariant(
            name="env-test-var",
            provider="test",
            model_alias="gpt-4",
            harness_profile="test-harness",
            benchmark_tags={"harness": "test-harness", "provider": "test", "model": "gpt-4"},
        )
        task = DBTaskCard(
            name="env-test-task",
            goal="Test",
            starting_prompt="Test",
            stop_condition="Test",
        )
        db_session.add_all([harness, experiment, variant, task])
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

        result = runner.invoke(app, ["session", "env", str(session.id)])

        assert result.exit_code == 0, f"Exit code: {result.exit_code}, Output: {result.output}"
        assert str(session.id) in result.output
        assert "test-harness" in result.output
        assert "OPENAI_API_BASE" in result.output
        assert f"sk-benchmark-{session.id}" in result.output

    def test_env_session_not_found(self, mock_env_db_url, runner):
        """Test env command for non-existent session."""
        result = runner.invoke(app, ["session", "env", "550e8400-e29b-41d4-a716-446655440000"])

        assert result.exit_code != 0
        assert "Session not found" in result.output or "Exit" in result.output


class TestSessionAddNotesCommand:
    """Tests for session add-notes CLI command."""

    def test_add_notes(self, db_session, mock_env_db_url, runner):
        """Test adding notes to a session."""
        # Create prerequisite records
        experiment = DBExperiment(name="notes-test-exp", description="Test")
        variant = DBVariant(
            name="notes-test-var",
            provider="test",
            model_alias="gpt-4",
            harness_profile="default",
        )
        task = DBTaskCard(
            name="notes-test-task",
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

        result = runner.invoke(
            app,
            ["session", "add-notes", str(session.id), "--notes", "Test notes for session"],
        )

        assert result.exit_code == 0, f"Exit code: {result.exit_code}, Output: {result.output}"
        assert "Session notes updated successfully" in result.output

        # Verify notes were updated in database
        db_session.refresh(session)
        assert session.notes == "Test notes for session"

    def test_add_notes_with_append(self, db_session, mock_env_db_url, runner):
        """Test appending notes to existing session notes."""
        # Create prerequisite records
        experiment = DBExperiment(name="notes-append-exp", description="Test")
        variant = DBVariant(
            name="notes-append-var",
            provider="test",
            model_alias="gpt-4",
            harness_profile="default",
        )
        task = DBTaskCard(
            name="notes-append-task",
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
            notes="Initial notes",
        )
        db_session.add(session)
        db_session.commit()

        result = runner.invoke(
            app,
            [
                "session",
                "add-notes",
                str(session.id),
                "--notes",
                "Appended notes",
                "--append",
            ],
        )

        assert result.exit_code == 0, f"Exit code: {result.exit_code}, Output: {result.output}"
        assert "Session notes updated successfully" in result.output
        assert "(appended to existing notes)" in result.output

        # Verify notes were appended
        db_session.refresh(session)
        assert "Initial notes" in session.notes
        assert "Appended notes" in session.notes

    def test_add_notes_session_not_found(self, mock_env_db_url, runner):
        """Test add-notes with non-existent session."""
        result = runner.invoke(
            app,
            [
                "session",
                "add-notes",
                "550e8400-e29b-41d4-a716-446655440000",
                "--notes",
                "Test notes",
            ],
        )

        assert result.exit_code != 0
        assert "Session not found" in result.output or "Exit" in result.output
