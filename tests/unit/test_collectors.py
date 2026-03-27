"""Unit tests for collectors package."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
import respx
from httpx import Response

from benchmark_core.models import Request
from collectors.litellm_collector import (
    CollectionDiagnostics,
    IngestWatermark,
    LiteLLMCollector,
)
from collectors.metric_catalog import MetricCatalog


def test_import_collectors_package() -> None:
    """Smoke test: collectors package imports successfully."""
    import collectors

    assert collectors is not None


def test_import_litellm_collector() -> None:
    """Smoke test: LiteLLM collector imports successfully."""
    from collectors.litellm_collector import LiteLLMCollector

    # Verify class can be instantiated (with dummy params)
    collector = LiteLLMCollector(
        base_url="http://localhost:4000",
        api_key="test-key",
        repository=None,  # type: ignore
    )
    assert collector is not None


def test_import_prometheus_collector() -> None:
    """Smoke test: Prometheus collector imports successfully."""
    from collectors.prometheus_collector import PrometheusCollector

    collector = PrometheusCollector(
        base_url="http://localhost:9090",
        session_id=UUID("12345678-1234-1234-1234-123456789abc"),
    )
    assert collector is not None


def test_import_normalization() -> None:
    """Smoke test: normalization job imports successfully."""
    from collectors.normalization import NormalizationJob

    job = NormalizationJob(repository=None)  # type: ignore
    assert job is not None


def test_import_rollup_job() -> None:
    """Smoke test: rollup job imports successfully."""
    from collectors.rollup_job import RollupJob

    job = RollupJob()
    assert job is not None


def test_import_metric_catalog() -> None:
    """Smoke test: metric catalog imports successfully."""
    from collectors.metric_catalog import MetricCatalog

    catalog = MetricCatalog()
    assert catalog is not None


# =============================================================================
# CollectionDiagnostics Tests
# =============================================================================


def test_collection_diagnostics_initial_state() -> None:
    """Test CollectionDiagnostics initializes with zero counts."""
    diag = CollectionDiagnostics()

    assert diag.total_raw_records == 0
    assert diag.normalized_count == 0
    assert diag.skipped_count == 0
    assert diag.missing_fields == {}
    assert diag.errors == []


def test_collection_diagnostics_record_missing_field() -> None:
    """Test recording missing field counts."""
    diag = CollectionDiagnostics()

    diag.record_missing_field("request_id")
    diag.record_missing_field("request_id")
    diag.record_missing_field("timestamp")

    assert diag.missing_fields["request_id"] == 2
    assert diag.missing_fields["timestamp"] == 1


def test_collection_diagnostics_add_error() -> None:
    """Test adding error messages."""
    diag = CollectionDiagnostics()

    diag.add_error("Error 1")
    diag.add_error("Error 2")

    assert len(diag.errors) == 2
    assert diag.errors[0] == "Error 1"
    assert diag.errors[1] == "Error 2"


# =============================================================================
# IngestWatermark Tests
# =============================================================================


def test_ingest_watermark_initial_state() -> None:
    """Test IngestWatermark initializes with None values."""
    watermark = IngestWatermark()

    assert watermark.last_request_id is None
    assert watermark.last_timestamp is None
    assert watermark.record_count == 0


def test_ingest_watermark_to_dict() -> None:
    """Test IngestWatermark serialization."""
    timestamp = datetime(2025, 3, 26, 12, 0, 0, tzinfo=UTC)
    watermark = IngestWatermark(
        last_request_id="req-123",
        last_timestamp=timestamp,
        record_count=42,
    )

    data = watermark.to_dict()

    assert data["last_request_id"] == "req-123"
    assert data["last_timestamp"] == "2025-03-26T12:00:00+00:00"
    assert data["record_count"] == 42


def test_ingest_watermark_to_dict_none_timestamp() -> None:
    """Test serialization with None timestamp."""
    watermark = IngestWatermark(last_request_id="req-123", record_count=10)

    data = watermark.to_dict()

    assert data["last_timestamp"] is None


def test_ingest_watermark_from_dict() -> None:
    """Test IngestWatermark deserialization."""
    data = {
        "last_request_id": "req-456",
        "last_timestamp": "2025-03-26T14:30:00+00:00",
        "record_count": 100,
    }

    watermark = IngestWatermark.from_dict(data)

    assert watermark.last_request_id == "req-456"
    assert watermark.last_timestamp == datetime(2025, 3, 26, 14, 30, 0, tzinfo=UTC)
    assert watermark.record_count == 100


def test_ingest_watermark_from_dict_invalid_timestamp() -> None:
    """Test deserialization with invalid timestamp."""
    data = {
        "last_request_id": "req-789",
        "last_timestamp": "invalid-timestamp",
        "record_count": 5,
    }

    watermark = IngestWatermark.from_dict(data)

    assert watermark.last_timestamp is None
    assert watermark.last_request_id == "req-789"


def test_ingest_watermark_roundtrip() -> None:
    """Test serialization/deserialization roundtrip."""
    original = IngestWatermark(
        last_request_id="req-round",
        last_timestamp=datetime(2025, 3, 26, 10, 0, 0, tzinfo=UTC),
        record_count=999,
    )

    data = original.to_dict()
    restored = IngestWatermark.from_dict(data)

    assert restored.last_request_id == original.last_request_id
    assert restored.last_timestamp == original.last_timestamp
    assert restored.record_count == original.record_count


# =============================================================================
# MetricCatalog Tests
# =============================================================================


class TestMetricCatalog:
    """Tests for the MetricCatalog class."""

    def test_get_latency_queries_returns_dict(self) -> None:
        """MetricCatalog returns latency queries as dictionary."""
        catalog = MetricCatalog()
        queries = catalog.get_latency_queries("test-session-123")

        assert isinstance(queries, dict)
        assert "latency_median_ms" in queries
        assert "latency_p95_ms" in queries
        assert "latency_p99_ms" in queries

    def test_latency_queries_contain_session_filter(self) -> None:
        """Latency queries include session_id filter."""
        catalog = MetricCatalog()
        queries = catalog.get_latency_queries("session-abc")

        for query in queries.values():
            assert 'session_id="session-abc"' in query

    def test_get_throughput_query_returns_string(self) -> None:
        """MetricCatalog returns throughput query string."""
        catalog = MetricCatalog()
        query = catalog.get_throughput_query("session-xyz")

        assert isinstance(query, str)
        assert 'session_id="session-xyz"' in query
        assert "rate" in query

    def test_get_error_queries_returns_dict(self) -> None:
        """MetricCatalog returns error queries as dictionary."""
        catalog = MetricCatalog()
        queries = catalog.get_error_queries("session-123")

        assert isinstance(queries, dict)
        assert "error_rate" in queries
        assert "error_percentage" in queries

    def test_error_queries_contain_session_filter(self) -> None:
        """Error queries include session_id filter."""
        catalog = MetricCatalog()
        queries = catalog.get_error_queries("session-def")

        for query in queries.values():
            assert 'session_id="session-def"' in query

    def test_get_cache_queries_returns_dict(self) -> None:
        """MetricCatalog returns cache queries as dictionary."""
        catalog = MetricCatalog()
        queries = catalog.get_cache_queries("session-cache")

        assert isinstance(queries, dict)
        assert "cache_hit_rate" in queries
        assert "cache_hit_percentage" in queries


# =============================================================================
# LiteLLMCollector normalize_request Tests
# =============================================================================


def test_normalize_request_valid_data() -> None:
    """Test normalization of valid LiteLLM spend log data."""
    collector = LiteLLMCollector(
        base_url="http://localhost:4000",
        api_key="test",
        repository=None,  # type: ignore
    )

    session_id = uuid4()
    raw_request = {
        "request_id": "req-test-001",
        "startTime": "2025-03-26T10:30:00+00:00",
        "model": "gpt-4",
        "user": "test-user",
        "metadata": {
            "user_api_key": "test-key",
            "session_id": "sess-123",
            "experiment_id": "exp-456",
        },
        "cache_hit": False,
        "response": "Test response",
    }

    diag = CollectionDiagnostics()
    request = collector.normalize_request(raw_request, session_id, diag)

    assert request is not None
    assert request.request_id == "req-test-001"
    assert request.provider == "test-user"
    assert request.model == "gpt-4"
    assert request.session_id == session_id
    assert request.metadata.get("session_id") == "sess-123"
    assert request.metadata.get("experiment_id") == "exp-456"


def test_normalize_request_missing_request_id() -> None:
    """Test normalization handles missing request_id gracefully."""
    collector = LiteLLMCollector(
        base_url="http://localhost:4000",
        api_key="test",
        repository=None,  # type: ignore
    )

    session_id = uuid4()
    raw_request = {
        "startTime": "2025-03-26T10:30:00+00:00",
        "model": "gpt-4",
        "user": "test-user",
    }

    diag = CollectionDiagnostics()
    request = collector.normalize_request(raw_request, session_id, diag)

    assert request is None
    assert diag.missing_fields.get("request_id") == 1


def test_normalize_request_missing_timestamp() -> None:
    """Test normalization handles missing startTime gracefully."""
    collector = LiteLLMCollector(
        base_url="http://localhost:4000",
        api_key="test",
        repository=None,  # type: ignore
    )

    session_id = uuid4()
    raw_request = {
        "request_id": "req-test-002",
        "model": "gpt-4",
        "user": "test-user",
    }

    diag = CollectionDiagnostics()
    request = collector.normalize_request(raw_request, session_id, diag)

    assert request is None
    # The code records "timestamp" as the field name (consolidated alias for startTime/timestamp/created_at)
    assert diag.missing_fields.get("timestamp") == 1


def test_normalize_request_timestamp_variants() -> None:
    """Test normalization handles various timestamp formats."""
    collector = LiteLLMCollector(
        base_url="http://localhost:4000",
        api_key="test",
        repository=None,  # type: ignore
    )

    session_id = uuid4()

    # ISO format with timezone
    raw1 = {
        "request_id": "req-001",
        "startTime": "2025-03-26T10:30:00+00:00",
        "model": "gpt-4",
    }
    diag1 = CollectionDiagnostics()
    req1 = collector.normalize_request(raw1, session_id, diag1)
    assert req1 is not None
    assert req1.timestamp.year == 2025

    # ISO format without timezone
    raw2 = {
        "request_id": "req-002",
        "startTime": "2025-03-26T10:30:00",
        "model": "gpt-4",
    }
    diag2 = CollectionDiagnostics()
    req2 = collector.normalize_request(raw2, session_id, diag2)
    assert req2 is not None


def test_normalize_request_correlation_keys_preserved() -> None:
    """Test that all correlation keys are preserved in metadata."""
    collector = LiteLLMCollector(
        base_url="http://localhost:4000",
        api_key="test",
        repository=None,  # type: ignore
    )

    session_id = uuid4()
    raw_request = {
        "request_id": "req-test-003",
        "startTime": "2025-03-26T10:30:00+00:00",
        "model": "claude-3-opus",
        "user": "test-user",
        "metadata": {
            "session_id": "sess-123",
            "experiment_id": "exp-456",
            "variant_id": "var-789",
            "task_card_id": "task-abc",
            "harness_profile": "profile-xyz",
            "trace_id": "trace-123",
            "span_id": "span-456",
            "parent_span_id": "parent-789",
        },
    }

    diag = CollectionDiagnostics()
    request = collector.normalize_request(raw_request, session_id, diag)

    assert request is not None
    metadata = request.metadata

    # All correlation keys should be preserved
    assert metadata.get("session_id") == "sess-123"
    assert metadata.get("experiment_id") == "exp-456"
    assert metadata.get("variant_id") == "var-789"
    assert metadata.get("task_card_id") == "task-abc"
    assert metadata.get("harness_profile") == "profile-xyz"
    assert metadata.get("trace_id") == "trace-123"
    assert metadata.get("span_id") == "span-456"
    assert metadata.get("parent_span_id") == "parent-789"


def test_normalize_request_error_extraction() -> None:
    """Test extraction of error information from response."""
    collector = LiteLLMCollector(
        base_url="http://localhost:4000",
        api_key="test",
        repository=None,  # type: ignore
    )

    session_id = uuid4()

    # Request with error in response
    raw_with_error = {
        "request_id": "req-error-001",
        "startTime": "2025-03-26T10:30:00+00:00",
        "model": "gpt-4",
        "response": {"error": "Rate limit exceeded"},
    }

    diag = CollectionDiagnostics()
    request = collector.normalize_request(raw_with_error, session_id, diag)

    assert request is not None


def test_normalize_request_cache_hit_variants() -> None:
    """Test handling of cache hit indicators."""
    collector = LiteLLMCollector(
        base_url="http://localhost:4000",
        api_key="test",
        repository=None,  # type: ignore
    )

    session_id = uuid4()

    # Explicit False
    raw1 = {
        "request_id": "req-001",
        "startTime": "2025-03-26T10:30:00+00:00",
        "model": "gpt-4",
        "cache_hit": False,
    }
    diag1 = CollectionDiagnostics()
    req1 = collector.normalize_request(raw1, session_id, diag1)
    assert req1 is not None

    # Explicit True
    raw2 = {
        "request_id": "req-002",
        "startTime": "2025-03-26T10:30:00+00:00",
        "model": "gpt-4",
        "cache_hit": True,
    }
    diag2 = CollectionDiagnostics()
    req2 = collector.normalize_request(raw2, session_id, diag2)
    assert req2 is not None

    # Missing (defaults to False)
    raw3 = {
        "request_id": "req-003",
        "startTime": "2025-03-26T10:30:00+00:00",
        "model": "gpt-4",
    }
    diag3 = CollectionDiagnostics()
    req3 = collector.normalize_request(raw3, session_id, diag3)
    assert req3 is not None


def test_normalize_request_invalid_data_type() -> None:
    """Test handling of non-dict raw request data."""
    collector = LiteLLMCollector(
        base_url="http://localhost:4000",
        api_key="test",
        repository=None,  # type: ignore
    )

    session_id = uuid4()
    diag = CollectionDiagnostics()

    # String instead of dict
    request = collector.normalize_request("not-a-dict", session_id, diag)
    assert request is None

    # None instead of dict
    request = collector.normalize_request(None, session_id, diag)
    assert request is None


def test_normalize_request_unknown_provider_model() -> None:
    """Test handling of requests without user/model fields."""
    collector = LiteLLMCollector(
        base_url="http://localhost:4000",
        api_key="test",
        repository=None,  # type: ignore
    )

    session_id = uuid4()
    raw_request = {
        "request_id": "req-004",
        "startTime": "2025-03-26T10:30:00+00:00",
        # Missing user and model
    }

    diag = CollectionDiagnostics()
    request = collector.normalize_request(raw_request, session_id, diag)

    assert request is not None
    # Should use defaults
    assert request.provider == "unknown"
    assert request.model == "unknown"


# =============================================================================
# LiteLLMCollector collect_requests Tests
# =============================================================================


@pytest.mark.asyncio
async def test_collect_requests_idempotent_insert() -> None:
    """Test that collection uses repository for idempotent insert."""
    mock_repo = MagicMock()
    mock_requests = [
        Request(
            request_id="req-1",
            session_id=uuid4(),
            provider="test",
            model="gpt-4",
            timestamp=datetime.now(UTC),
        )
    ]
    mock_repo.create_many = AsyncMock(return_value=mock_requests)

    collector = LiteLLMCollector(
        base_url="http://localhost:4000",
        api_key="test",
        repository=mock_repo,
    )

    session_id = uuid4()
    raw_requests = [
        {"request_id": "req-1", "startTime": "2025-03-26T10:00:00+00:00", "model": "gpt-4"},
    ]
    collector._fetch_raw_requests = AsyncMock(return_value=raw_requests)  # type: ignore

    collected, diagnostics, watermark = await collector.collect_requests(
        session_id=session_id
    )

    # Verify repository.create_many was called
    mock_repo.create_many.assert_called_once()
    assert len(collected) == 1
    assert watermark.last_request_id == "req-1"


@pytest.mark.asyncio
@respx.mock
async def test_fetch_raw_requests_watermark_respects_start_time() -> None:
    """Test that watermark and start_time interact correctly."""
    collector = LiteLLMCollector(
        base_url="http://localhost:4000",
        api_key="test",
        repository=None,  # type: ignore
    )

    session_id = uuid4()

    # Set up mock endpoint
    route = respx.get("http://localhost:4000/spend/logs").mock(
        return_value=Response(200, json={"data": []})
    )

    # Create watermark with timestamp later than start_time
    watermark = IngestWatermark(
        last_request_id="req-001",
        last_timestamp=datetime(2025, 3, 27, 12, 0, 0, tzinfo=UTC),
        record_count=10,
    )

    # start_time is earlier than watermark
    start_time = "2025-03-26T10:00:00+00:00"

    # Call fetch and verify request was made with correct start_time
    await collector._fetch_raw_requests(
        session_id=session_id,
        start_time=start_time,
        end_time=None,
        watermark=watermark,
        diagnostics=CollectionDiagnostics(),
    )

    # Verify request was made and start_time param uses max of both times
    assert route.called
    request = route.calls.last.request
    # The actual start_time used should be max(start_time, watermark.last_timestamp)
    assert "start_time=2025-03-27T12%3A00%3A00" in str(request.url) or "start_time=2025-03-27T12:00:00" in str(request.url)


@pytest.mark.asyncio
@respx.mock
async def test_fetch_raw_requests_uses_start_time_when_no_watermark() -> None:
    """Test that start_time is used when no watermark provided."""
    collector = LiteLLMCollector(
        base_url="http://localhost:4000",
        api_key="test",
        repository=None,  # type: ignore
    )

    session_id = uuid4()

    # Set up mock endpoint
    route = respx.get("http://localhost:4000/spend/logs").mock(
        return_value=Response(200, json={"data": []})
    )

    start_time = "2025-03-26T10:00:00+00:00"

    await collector._fetch_raw_requests(
        session_id=session_id,
        start_time=start_time,
        end_time=None,
        watermark=None,
        diagnostics=CollectionDiagnostics(),
    )

    # Verify request uses the provided start_time
    assert route.called
    request = route.calls.last.request
    assert "start_time=2025-03-26T10%3A00%3A00" in str(request.url) or "start_time=2025-03-26T10:00:00" in str(request.url)


# =============================================================================
# CollectionJobService Tests (via benchmark_core.services)
# =============================================================================


@pytest.mark.asyncio
async def test_collection_job_service_diagnostics_summary() -> None:
    """Test CollectionJobService provides diagnostics summary."""
    from benchmark_core.services import CollectionJobService

    mock_repo = MagicMock()

    service = CollectionJobService(
        litellm_base_url="http://localhost:4000",
        litellm_api_key="test",
        repository=mock_repo,
    )

    # Create mock diagnostics
    mock_diagnostics = MagicMock()
    mock_diagnostics.total_raw_records = 100
    mock_diagnostics.normalized_count = 95
    mock_diagnostics.skipped_count = 5
    mock_diagnostics.missing_fields = {"request_id": 3, "timestamp": 2}
    mock_diagnostics.errors = ["Error 1", "Error 2"]

    summary = service.get_diagnostics_summary(mock_diagnostics)

    assert "100 raw records" in summary or summary.get("total_raw_records") == 100
    assert "95 normalized" in summary or summary.get("normalized_count") == 95
    assert "5 skipped" in summary or summary.get("skipped_count") == 5
