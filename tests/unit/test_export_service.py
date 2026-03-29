"""Tests for export service."""

import json
import tempfile
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from benchmark_core.db.models import (
    Base,
    Experiment,
    Request,
    TaskCard,
    Variant,
)
from benchmark_core.db.models import (
    Session as DBSession,
)
from reporting.export_service import ExportSerializer, ExportService


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
def sample_experiment(db_session):
    """Create a sample experiment with sessions and requests."""
    # Create experiment
    experiment = Experiment(
        name="test-experiment",
        description="Test experiment for export",
    )
    db_session.add(experiment)
    db_session.flush()

    # Create variant
    variant = Variant(
        name="test-variant",
        provider="openai",
        model_alias="gpt-4",
        harness_profile="default",
    )
    db_session.add(variant)
    db_session.flush()

    # Create task card
    task_card = TaskCard(
        name="test-task",
        goal="Test goal",
        starting_prompt="Test prompt",
        stop_condition="Test condition",
    )
    db_session.add(task_card)
    db_session.flush()

    # Create session
    from datetime import UTC, datetime, timedelta

    session = DBSession(
        experiment_id=experiment.id,
        variant_id=variant.id,
        task_card_id=task_card.id,
        harness_profile="test-harness",
        repo_path="/test/repo",
        git_branch="main",
        git_commit="abc123def456",
        git_dirty=False,
        operator_label="test-session-1",
        status="completed",
        outcome_state="success",
        started_at=datetime.now(UTC) - timedelta(hours=1),
        ended_at=datetime.now(UTC),
        notes="Test session notes",
    )
    db_session.add(session)
    db_session.flush()

    # Create requests
    for i in range(3):
        request = Request(
            request_id=f"req-{i}",
            session_id=session.id,
            provider="openai",
            model="gpt-4",
            timestamp=datetime.now(UTC) - timedelta(minutes=30 - i * 10),
            latency_ms=100.0 + i * 50,
            ttft_ms=50.0 + i * 25,
            tokens_prompt=100 + i * 10,
            tokens_completion=50 + i * 5,
            error=False,
            cache_hit=(i == 2),
        )
        db_session.add(request)

    db_session.commit()

    return {
        "experiment": experiment,
        "variant": variant,
        "task_card": task_card,
        "session": session,
    }


class TestExportService:
    """Tests for ExportService."""

    def test_export_session_basic(self, db_session, sample_experiment):
        """Test basic session export."""
        service = ExportService(db_session)
        export = service.export_session(
            session_id=sample_experiment["session"].id,
            include_requests=False,
            redact_secrets=True,
        )

        assert "session" in export
        assert export["session"]["id"] == str(sample_experiment["session"].id)
        assert export["session"]["status"] == "completed"
        assert export["session"]["git_branch"] == "main"
        assert export["session"]["git_commit"] == "abc123def456"

        # Verify sensitive fields are redacted
        assert "proxy_credential_alias" not in export["session"]
        assert "proxy_credential_id" not in export["session"]

    def test_export_session_with_requests(self, db_session, sample_experiment):
        """Test session export with request data."""
        service = ExportService(db_session)
        export = service.export_session(
            session_id=sample_experiment["session"].id,
            include_requests=True,
            redact_secrets=True,
        )

        assert "requests" in export
        assert len(export["requests"]) == 3
        assert export["requests"][0]["provider"] == "openai"
        assert export["requests"][0]["model"] == "gpt-4"

        # Verify summary
        assert "summary" in export
        assert export["summary"]["total_requests"] == 3
        assert export["summary"]["error_count"] == 0
        assert export["summary"]["cache_hit_count"] == 1

    def test_export_session_with_secrets(self, db_session, sample_experiment):
        """Test session export without redaction."""
        service = ExportService(db_session)
        export = service.export_session(
            session_id=sample_experiment["session"].id,
            include_requests=False,
            redact_secrets=False,
        )

        # Verify sensitive fields are included
        assert "proxy_credential_alias" in export["session"]
        assert "proxy_credential_id" in export["session"]

    def test_export_session_not_found(self, db_session):
        """Test session export with invalid ID."""
        service = ExportService(db_session)
        with pytest.raises(ValueError, match="Session not found"):
            service.export_session(session_id=uuid4())

    def test_export_experiment_basic(self, db_session, sample_experiment):
        """Test basic experiment export."""
        service = ExportService(db_session)
        export = service.export_experiment(
            experiment_id=sample_experiment["experiment"].id,
            include_sessions=False,
            redact_secrets=True,
        )

        assert "experiment" in export
        assert export["experiment"]["name"] == "test-experiment"
        assert export["experiment"]["description"] == "Test experiment for export"

    def test_export_experiment_with_sessions(self, db_session, sample_experiment):
        """Test experiment export with session data."""
        service = ExportService(db_session)
        export = service.export_experiment(
            experiment_id=sample_experiment["experiment"].id,
            include_sessions=True,
            include_requests=False,
            redact_secrets=True,
        )

        assert "sessions" in export
        assert len(export["sessions"]) == 1
        assert export["sessions"][0]["status"] == "completed"

        # Verify summary
        assert "summary" in export
        assert export["summary"]["total_sessions"] == 1
        assert export["summary"]["completed_sessions"] == 1

    def test_export_experiment_with_requests(self, db_session, sample_experiment):
        """Test experiment export with request data."""
        service = ExportService(db_session)
        export = service.export_experiment(
            experiment_id=sample_experiment["experiment"].id,
            include_sessions=True,
            include_requests=True,
            redact_secrets=True,
        )

        assert "sessions" in export
        assert len(export["sessions"]) == 1
        assert "requests" in export["sessions"][0]
        assert len(export["sessions"][0]["requests"]) == 3

    def test_export_experiment_not_found(self, db_session):
        """Test experiment export with invalid ID."""
        service = ExportService(db_session)
        with pytest.raises(ValueError, match="Experiment not found"):
            service.export_experiment(experiment_id=uuid4())


class TestExportSerializer:
    """Tests for ExportSerializer."""

    def test_to_json(self, sample_experiment):
        """Test JSON serialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_export.json"

            export_data = {
                "session": {
                    "id": str(sample_experiment["session"].id),
                    "status": "completed",
                },
                "requests": [
                    {"id": "req-1", "provider": "openai"},
                    {"id": "req-2", "provider": "openai"},
                ],
            }

            ExportSerializer.to_json(export_data, output_path)

            assert output_path.exists()
            with open(output_path) as f:
                loaded = json.load(f)
                assert loaded["session"]["status"] == "completed"
                assert len(loaded["requests"]) == 2

    def test_to_csv(self, sample_experiment):
        """Test CSV serialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_export.csv"

            export_data = {
                "requests": [
                    {
                        "id": "req-1",
                        "provider": "openai",
                        "model": "gpt-4",
                        "latency_ms": 100.0,
                    },
                    {
                        "id": "req-2",
                        "provider": "openai",
                        "model": "gpt-4",
                        "latency_ms": 150.0,
                    },
                ]
            }

            ExportSerializer.to_csv(export_data, output_path, record_type="requests")

            assert output_path.exists()
            with open(output_path) as f:
                lines = f.readlines()
                # Header + 2 data rows
                assert len(lines) == 3
                assert "id" in lines[0]
                assert "provider" in lines[0]

    def test_to_csv_empty(self):
        """Test CSV serialization with no data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_export.csv"

            export_data = {"session": {"id": "test"}}

            ExportSerializer.to_csv(export_data, output_path, record_type="requests")

            assert output_path.exists()
            # Should create file with just headers

    def test_to_parquet_without_pyarrow(self, monkeypatch):
        """Test Parquet export raises error without pyarrow."""
        # Mock pyarrow import to raise ImportError
        import builtins

        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "pyarrow":
                raise ImportError("No module named 'pyarrow'")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_export.parquet"

            export_data = {"requests": [{"id": "req-1"}]}

            with pytest.raises(ImportError, match="Parquet export requires pyarrow"):
                ExportSerializer.to_parquet(export_data, output_path)
