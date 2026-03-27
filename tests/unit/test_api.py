"""Unit tests for API package."""

import uuid
from datetime import UTC
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.schemas import (
    ExperimentListResponse,
    ExperimentResponse,
    MetricRollupResponse,
    RequestResponse,
    SessionDetailResponse,
    SessionResponse,
    VariantResponse,
)


def test_import_api_package() -> None:
    """Smoke test: API package imports successfully."""
    import api

    assert api is not None


def test_import_main_app() -> None:
    """Smoke test: FastAPI app imports successfully."""
    from api.main import app

    assert app is not None
    assert app.title == "LiteLLM Benchmark API"


def test_import_schemas() -> None:
    """Smoke test: Schema module imports successfully."""
    from api import schemas

    assert schemas is not None


# ============================================================================
# Schema Tests
# ============================================================================


class TestSchemas:
    """Tests for response schema validation."""

    def test_experiment_response_schema(self) -> None:
        """Test ExperimentResponse schema instantiation."""
        from datetime import datetime

        exp = ExperimentResponse(
            id=uuid.uuid4(),
            name="test-experiment",
            description="Test description",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        assert exp.name == "test-experiment"
        assert exp.model_config.get("from_attributes") is True

    def test_variant_response_schema(self) -> None:
        """Test VariantResponse schema instantiation."""
        from datetime import datetime

        variant = VariantResponse(
            id=uuid.uuid4(),
            name="test-variant",
            provider="openai",
            provider_route=None,
            model_alias="gpt-4",
            harness_profile="default",
            harness_env_overrides={},
            benchmark_tags={},
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        assert variant.provider == "openai"
        assert variant.model_alias == "gpt-4"

    def test_session_response_schema(self) -> None:
        """Test SessionResponse schema instantiation."""
        from datetime import datetime

        session = SessionResponse(
            id=uuid.uuid4(),
            experiment_id=uuid.uuid4(),
            variant_id=uuid.uuid4(),
            task_card_id=uuid.uuid4(),
            harness_profile="default",
            repo_path="/tmp/repo",
            git_branch="main",
            git_commit="abc123",
            git_dirty=False,
            operator_label=None,
            proxy_credential_id=None,
            started_at=datetime.now(UTC),
            ended_at=None,
            status="active",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        assert session.status == "active"
        assert session.git_branch == "main"

    def test_request_response_schema(self) -> None:
        """Test RequestResponse schema instantiation."""
        from datetime import datetime

        request = RequestResponse(
            id=uuid.uuid4(),
            request_id="req-123",
            session_id=uuid.uuid4(),
            provider="openai",
            model="gpt-4",
            timestamp=datetime.now(UTC),
            latency_ms=100.5,
            ttft_ms=50.0,
            tokens_prompt=10,
            tokens_completion=20,
            error=False,
            error_message=None,
            cache_hit=None,
            request_metadata={},
            created_at=datetime.now(UTC),
        )
        assert request.provider == "openai"
        assert request.latency_ms == 100.5

    def test_metric_rollup_response_schema(self) -> None:
        """Test MetricRollupResponse schema instantiation."""
        from datetime import datetime

        rollup = MetricRollupResponse(
            id=uuid.uuid4(),
            dimension_type="session",
            dimension_id=str(uuid.uuid4()),
            metric_name="avg_latency_ms",
            metric_value=150.5,
            sample_count=10,
            computed_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
        )
        assert rollup.dimension_type == "session"
        assert rollup.metric_value == 150.5

    def test_paginated_response_schema(self) -> None:
        """Test paginated list responses."""
        exp_list = ExperimentListResponse(
            total=0,
            limit=100,
            offset=0,
            items=[],
        )
        assert exp_list.total == 0
        assert len(exp_list.items) == 0

    def test_session_detail_response(self) -> None:
        """Test SessionDetailResponse with extra fields."""
        from datetime import datetime

        session = SessionDetailResponse(
            id=uuid.uuid4(),
            experiment_id=uuid.uuid4(),
            variant_id=uuid.uuid4(),
            task_card_id=uuid.uuid4(),
            harness_profile="default",
            repo_path="/tmp/repo",
            git_branch="main",
            git_commit="abc123",
            git_dirty=False,
            operator_label=None,
            proxy_credential_id=None,
            started_at=datetime.now(UTC),
            ended_at=None,
            status="active",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            experiment_name="test-exp",
            variant_name="test-var",
            task_card_name=None,
            request_count=5,
        )
        assert session.experiment_name == "test-exp"
        assert session.request_count == 5


# ============================================================================
# API Endpoint Tests
# ============================================================================


class TestAPIEndpoints:
    """Tests for API endpoints using mocked database."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create a test client with mocked database."""
        from api.main import app

        # Patch the database session
        with patch("api.main.SessionLocal") as mock_session_local:
            mock_db = MagicMock()
            mock_session_local.return_value = mock_db
            yield TestClient(app)

    def test_health_check(self, client: TestClient) -> None:
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_list_experiments_empty(self, client: TestClient) -> None:
        """Test listing experiments when empty."""
        with patch("api.main.SessionLocal") as mock_session_local:
            mock_db = MagicMock()
            mock_db.execute.return_value.scalar.return_value = 0
            mock_db.execute.return_value.scalars.return_value.all.return_value = []
            mock_session_local.return_value = mock_db

            response = client.get("/experiments")
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 0
            assert data["items"] == []

    def test_list_experiments_with_data(self, client: TestClient) -> None:
        """Test listing experiments with data."""
        from datetime import datetime

        from benchmark_core.db.models import Experiment

        exp = Experiment(
            id=uuid.uuid4(),
            name="test-exp",
            description="Test",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        with patch("api.main.SessionLocal") as mock_session_local:
            mock_db = MagicMock()
            mock_db.execute.return_value.scalar.return_value = 1
            mock_db.execute.return_value.scalars.return_value.all.return_value = [exp]
            mock_session_local.return_value = mock_db

            response = client.get("/experiments")
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 1
            assert len(data["items"]) == 1
            assert data["items"][0]["name"] == "test-exp"

    def test_get_experiment_not_found(self, client: TestClient) -> None:
        """Test getting a non-existent experiment."""
        exp_id = str(uuid.uuid4())

        with patch("api.main.SessionLocal") as mock_session_local:
            mock_db = MagicMock()
            mock_db.execute.return_value.scalars.return_value.unique.return_value.one_or_none.return_value = None
            mock_session_local.return_value = mock_db

            response = client.get(f"/experiments/{exp_id}")
            assert response.status_code == 404

    def test_list_variants_empty(self, client: TestClient) -> None:
        """Test listing variants when empty."""
        with patch("api.main.SessionLocal") as mock_session_local:
            mock_db = MagicMock()
            mock_db.execute.return_value.scalar.return_value = 0
            mock_db.execute.return_value.scalars.return_value.all.return_value = []
            mock_session_local.return_value = mock_db

            response = client.get("/variants")
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 0

    def test_list_variants_with_filter(self, client: TestClient) -> None:
        """Test listing variants with provider filter."""
        with patch("api.main.SessionLocal") as mock_session_local:
            mock_db = MagicMock()
            mock_db.execute.return_value.scalar.return_value = 0
            mock_db.execute.return_value.scalars.return_value.all.return_value = []
            mock_session_local.return_value = mock_db

            response = client.get("/variants?provider=openai")
            assert response.status_code == 200

    def test_get_variant_not_found(self, client: TestClient) -> None:
        """Test getting a non-existent variant."""
        var_id = str(uuid.uuid4())

        with patch("api.main.SessionLocal") as mock_session_local:
            mock_db = MagicMock()
            mock_db.get.return_value = None
            mock_session_local.return_value = mock_db

            response = client.get(f"/variants/{var_id}")
            assert response.status_code == 404

    def test_list_sessions_empty(self, client: TestClient) -> None:
        """Test listing sessions when empty."""
        with patch("api.main.SessionLocal") as mock_session_local:
            mock_db = MagicMock()
            mock_db.execute.return_value.scalar.return_value = 0
            mock_db.execute.return_value.scalars.return_value.all.return_value = []
            mock_session_local.return_value = mock_db

            response = client.get("/sessions")
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 0

    def test_list_sessions_with_experiment_filter(self, client: TestClient) -> None:
        """Test listing sessions with experiment filter."""
        exp_id = str(uuid.uuid4())

        with patch("api.main.SessionLocal") as mock_session_local:
            mock_db = MagicMock()
            mock_db.execute.return_value.scalar.return_value = 0
            mock_db.execute.return_value.scalars.return_value.all.return_value = []
            mock_session_local.return_value = mock_db

            response = client.get(f"/sessions?experiment_id={exp_id}")
            assert response.status_code == 200

    def test_get_session_not_found(self, client: TestClient) -> None:
        """Test getting a non-existent session."""
        session_id = str(uuid.uuid4())

        with patch("api.main.SessionLocal") as mock_session_local:
            mock_db = MagicMock()
            mock_db.execute.return_value.scalars.return_value.unique.return_value.one_or_none.return_value = None
            mock_session_local.return_value = mock_db

            response = client.get(f"/sessions/{session_id}")
            assert response.status_code == 404

    def test_list_requests_empty(self, client: TestClient) -> None:
        """Test listing requests when empty."""
        with patch("api.main.SessionLocal") as mock_session_local:
            mock_db = MagicMock()
            mock_db.execute.return_value.scalar.return_value = 0
            mock_db.execute.return_value.scalars.return_value.all.return_value = []
            mock_session_local.return_value = mock_db

            response = client.get("/requests")
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 0

    def test_list_requests_with_session_filter(self, client: TestClient) -> None:
        """Test listing requests with session filter."""
        session_id = str(uuid.uuid4())

        with patch("api.main.SessionLocal") as mock_session_local:
            mock_db = MagicMock()
            mock_db.execute.return_value.scalar.return_value = 0
            mock_db.execute.return_value.scalars.return_value.all.return_value = []
            mock_session_local.return_value = mock_db

            response = client.get(f"/requests?session_id={session_id}")
            assert response.status_code == 200

    def test_get_request_not_found(self, client: TestClient) -> None:
        """Test getting a non-existent request."""
        req_id = str(uuid.uuid4())

        with patch("api.main.SessionLocal") as mock_session_local:
            mock_db = MagicMock()
            mock_db.get.return_value = None
            mock_session_local.return_value = mock_db

            response = client.get(f"/requests/{req_id}")
            assert response.status_code == 404

    def test_list_rollups_empty(self, client: TestClient) -> None:
        """Test listing rollups when empty."""
        with patch("api.main.SessionLocal") as mock_session_local:
            mock_db = MagicMock()
            mock_db.execute.return_value.scalar.return_value = 0
            mock_db.execute.return_value.scalars.return_value.all.return_value = []
            mock_session_local.return_value = mock_db

            response = client.get("/rollups")
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 0

    def test_list_rollups_with_filter(self, client: TestClient) -> None:
        """Test listing rollups with dimension_type filter."""
        with patch("api.main.SessionLocal") as mock_session_local:
            mock_db = MagicMock()
            mock_db.execute.return_value.scalar.return_value = 0
            mock_db.execute.return_value.scalars.return_value.all.return_value = []
            mock_session_local.return_value = mock_db

            response = client.get("/rollups?dimension_type=session")
            assert response.status_code == 200

    def test_get_rollup_not_found(self, client: TestClient) -> None:
        """Test getting a non-existent rollup."""
        rollup_id = str(uuid.uuid4())

        with patch("api.main.SessionLocal") as mock_session_local:
            mock_db = MagicMock()
            mock_db.get.return_value = None
            mock_session_local.return_value = mock_db

            response = client.get(f"/rollups/{rollup_id}")
            assert response.status_code == 404

    def test_get_experiment_comparison_not_found(self, client: TestClient) -> None:
        """Test comparison for non-existent experiment."""
        exp_id = str(uuid.uuid4())

        with patch("api.main.SessionLocal") as mock_session_local:
            mock_db = MagicMock()
            mock_db.get.return_value = None
            mock_session_local.return_value = mock_db

            response = client.get(f"/experiments/{exp_id}/comparison")
            assert response.status_code == 404

    def test_legacy_metrics_endpoint(self, client: TestClient) -> None:
        """Test legacy /metrics endpoint."""
        with patch("api.main.SessionLocal") as mock_session_local:
            mock_db = MagicMock()
            mock_db.execute.return_value.scalars.return_value.all.return_value = []
            mock_session_local.return_value = mock_db

            response = client.get("/metrics")
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)


# ============================================================================
# Query Parameter Validation Tests
# ============================================================================


class TestQueryParameters:
    """Tests for query parameter validation."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create a test client."""
        from api.main import app

        return TestClient(app)

    def test_pagination_limit_validation(self, client: TestClient) -> None:
        """Test pagination limit validation."""
        # Limit too high
        response = client.get("/experiments?limit=2000")
        assert response.status_code == 422

        # Limit too low
        response = client.get("/experiments?limit=0")
        assert response.status_code == 422

        # Valid limit
        with patch("api.main.SessionLocal") as mock_session_local:
            mock_db = MagicMock()
            mock_db.execute.return_value.scalar.return_value = 0
            mock_db.execute.return_value.scalars.return_value.all.return_value = []
            mock_session_local.return_value = mock_db

            response = client.get("/experiments?limit=100")
            assert response.status_code == 200

    def test_pagination_offset_validation(self, client: TestClient) -> None:
        """Test pagination offset validation."""
        # Negative offset
        response = client.get("/experiments?offset=-1")
        assert response.status_code == 422

        # Valid offset
        with patch("api.main.SessionLocal") as mock_session_local:
            mock_db = MagicMock()
            mock_db.execute.return_value.scalar.return_value = 0
            mock_db.execute.return_value.scalars.return_value.all.return_value = []
            mock_session_local.return_value = mock_db

            response = client.get("/experiments?offset=10")
            assert response.status_code == 200

    def test_uuid_validation(self, client: TestClient) -> None:
        """Test UUID parameter validation."""
        # Invalid UUID
        response = client.get("/experiments/not-a-uuid")
        assert response.status_code == 422

        # Valid UUID format but not found
        valid_uuid = str(uuid.uuid4())
        with patch("api.main.SessionLocal") as mock_session_local:
            mock_db = MagicMock()
            mock_db.execute.return_value.scalars.return_value.unique.return_value.one_or_none.return_value = None
            mock_session_local.return_value = mock_db

            response = client.get(f"/experiments/{valid_uuid}")
            assert response.status_code == 404  # Not 422 - UUID is valid format
