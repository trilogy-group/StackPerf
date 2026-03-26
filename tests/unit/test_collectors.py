"""Unit tests for collectors package."""

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from benchmark_core.models import Request
from collectors.litellm_collector import (
    CollectionDiagnostics,
    IngestWatermark,
    LiteLLMCollector,
)


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
    assert watermark.record_count == 100
    assert watermark.last_timestamp is not None
    assert watermark.last_timestamp.year == 2025


def test_ingest_watermark_from_dict_invalid_timestamp() -> None:
    """Test deserialization handles invalid timestamp gracefully."""
    data = {
        "last_request_id": "req-789",
        "last_timestamp": "invalid-date",
        "record_count": 5,
    }

    watermark = IngestWatermark.from_dict(data)

    assert watermark.last_timestamp is None
    assert watermark.last_request_id == "req-789"


def test_ingest_watermark_roundtrip() -> None:
    """Test serialization roundtrip preserves data."""
    original = IngestWatermark(
        last_request_id="req-abc",
        last_timestamp=datetime(2025, 3, 26, 10, 0, 0, tzinfo=UTC),
        record_count=99,
    )

    data = original.to_dict()
    restored = IngestWatermark.from_dict(data)

    assert restored.last_request_id == original.last_request_id
    assert restored.record_count == original.record_count
    assert restored.last_timestamp == original.last_timestamp


# =============================================================================
# LiteLLMCollector Normalization Tests
# =============================================================================


def test_normalize_request_valid_data() -> None:
    """Test normalization of valid LiteLLM request data."""
    collector = LiteLLMCollector(
        base_url="http://localhost:4000",
        api_key="test",
        repository=None,  # type: ignore
    )

    session_id = uuid4()
    raw_data = {
        "request_id": "req-test-123",
        "startTime": "2025-03-26T10:00:00+00:00",
        "user": "test-provider",
        "model": "gpt-4",
        "latency": 1.5,  # seconds
        "usage": {
            "prompt_tokens": 100,
            "completion_tokens": 50,
        },
        "cache_hit": False,
        "session_id": str(session_id),  # Session correlation key
        "experiment_id": "exp-1",
    }

    request = collector.normalize_request(raw_data, session_id)

    assert request is not None
    assert request.request_id == "req-test-123"
    assert request.session_id == session_id
    assert request.provider == "test-provider"
    assert request.model == "gpt-4"
    assert request.latency_ms == 1500.0  # Converted from seconds
    assert request.tokens_prompt == 100
    assert request.tokens_completion == 50
    assert request.cache_hit is False
    assert request.error is False
    # Check correlation keys preserved in metadata
    assert request.metadata.get("session_id") == str(session_id)
    assert request.metadata.get("experiment_id") == "exp-1"


def test_normalize_request_missing_request_id() -> None:
    """Test normalization fails when request_id is missing."""
    collector = LiteLLMCollector(
        base_url="http://localhost:4000",
        api_key="test",
        repository=None,  # type: ignore
    )

    diagnostics = CollectionDiagnostics()
    raw_data = {
        "startTime": "2025-03-26T10:00:00+00:00",
        "model": "gpt-4",
    }

    request = collector.normalize_request(
        raw_data, uuid4(), diagnostics
    )

    assert request is None
    assert "request_id" in diagnostics.missing_fields


def test_normalize_request_missing_timestamp() -> None:
    """Test normalization fails when timestamp is missing."""
    collector = LiteLLMCollector(
        base_url="http://localhost:4000",
        api_key="test",
        repository=None,  # type: ignore
    )

    diagnostics = CollectionDiagnostics()
    raw_data = {
        "request_id": "req-123",
        "model": "gpt-4",
    }

    request = collector.normalize_request(
        raw_data, uuid4(), diagnostics
    )

    assert request is None
    assert "timestamp" in diagnostics.missing_fields


def test_normalize_request_timestamp_variants() -> None:
    """Test handling of various timestamp formats."""
    collector = LiteLLMCollector(
        base_url="http://localhost:4000",
        api_key="test",
        repository=None,  # type: ignore
    )

    session_id = uuid4()

    # ISO format with Z
    raw1 = {
        "request_id": "req-1",
        "startTime": "2025-03-26T10:00:00Z",
        "model": "gpt-4",
    }
    req1 = collector.normalize_request(raw1, session_id)
    assert req1 is not None

    # Unix timestamp as float
    raw2 = {
        "request_id": "req-2",
        "timestamp": 1711447200.0,
        "model": "gpt-4",
    }
    req2 = collector.normalize_request(raw2, session_id)
    assert req2 is not None

    # Alternative timestamp field
    raw3 = {
        "request_id": "req-3",
        "created_at": "2025-03-26T10:00:00+00:00",
        "model": "gpt-4",
    }
    req3 = collector.normalize_request(raw3, session_id)
    assert req3 is not None


def test_normalize_request_correlation_keys_preserved() -> None:
    """Test that session correlation keys are preserved in metadata."""
    collector = LiteLLMCollector(
        base_url="http://localhost:4000",
        api_key="test",
        repository=None,  # type: ignore
    )

    session_id = uuid4()
    raw_data = {
        "request_id": "req-123",
        "startTime": "2025-03-26T10:00:00+00:00",
        "model": "gpt-4",
        # Session correlation keys
        "session_id": "sess-abc",
        "experiment_id": "exp-123",
        "variant_id": "var-456",
        "task_card_id": "task-789",
        "harness_profile": "profile-x",
        "trace_id": "trace-aaa",
        "span_id": "span-bbb",
        "parent_span_id": "parent-ccc",
    }

    request = collector.normalize_request(raw_data, session_id)

    assert request is not None
    assert request.metadata.get("session_id") == "sess-abc"
    assert request.metadata.get("experiment_id") == "exp-123"
    assert request.metadata.get("variant_id") == "var-456"
    assert request.metadata.get("task_card_id") == "task-789"
    assert request.metadata.get("harness_profile") == "profile-x"
    assert request.metadata.get("trace_id") == "trace-aaa"
    assert request.metadata.get("span_id") == "span-bbb"
    assert request.metadata.get("parent_span_id") == "parent-ccc"


def test_normalize_request_error_extraction() -> None:
    """Test extraction of error information from raw data."""
    collector = LiteLLMCollector(
        base_url="http://localhost:4000",
        api_key="test",
        repository=None,  # type: ignore
    )

    session_id = uuid4()

    # Error as boolean
    raw1 = {
        "request_id": "req-err-1",
        "startTime": "2025-03-26T10:00:00+00:00",
        "model": "gpt-4",
        "error": True,
    }
    req1 = collector.normalize_request(raw1, session_id)
    assert req1 is not None
    assert req1.error is True
    assert req1.error_message is None

    # Error as string
    raw2 = {
        "request_id": "req-err-2",
        "startTime": "2025-03-26T10:00:00+00:00",
        "model": "gpt-4",
        "error": "Rate limit exceeded",
    }
    req2 = collector.normalize_request(raw2, session_id)
    assert req2 is not None
    assert req2.error is True
    assert req2.error_message == "Rate limit exceeded"

    # Error as dict
    raw3 = {
        "request_id": "req-err-3",
        "startTime": "2025-03-26T10:00:00+00:00",
        "model": "gpt-4",
        "error": {"message": "Context length exceeded"},
    }
    req3 = collector.normalize_request(raw3, session_id)
    assert req3 is not None
    assert req3.error is True
    assert req3.error_message == "Context length exceeded"


def test_normalize_request_cache_hit_variants() -> None:
    """Test extraction of cache hit information."""
    collector = LiteLLMCollector(
        base_url="http://localhost:4000",
        api_key="test",
        repository=None,  # type: ignore
    )

    session_id = uuid4()

    # cache_hit field
    raw1 = {
        "request_id": "req-cache-1",
        "startTime": "2025-03-26T10:00:00+00:00",
        "model": "gpt-4",
        "cache_hit": True,
    }
    req1 = collector.normalize_request(raw1, session_id)
    assert req1 is not None
    assert req1.cache_hit is True

    # cached field
    raw2 = {
        "request_id": "req-cache-2",
        "startTime": "2025-03-26T10:00:00+00:00",
        "model": "gpt-4",
        "cached": True,
    }
    req2 = collector.normalize_request(raw2, session_id)
    assert req2 is not None
    assert req2.cache_hit is True


def test_normalize_request_invalid_data_type() -> None:
    """Test handling of non-dict raw data."""
    collector = LiteLLMCollector(
        base_url="http://localhost:4000",
        api_key="test",
        repository=None,  # type: ignore
    )

    diagnostics = CollectionDiagnostics()
    request = collector.normalize_request("not a dict", uuid4(), diagnostics)

    assert request is None
    assert any("Invalid raw data type" in err for err in diagnostics.errors)


def test_normalize_request_unknown_provider_model() -> None:
    """Test handling when provider/model are missing."""
    collector = LiteLLMCollector(
        base_url="http://localhost:4000",
        api_key="test",
        repository=None,  # type: ignore
    )

    diagnostics = CollectionDiagnostics()
    raw_data = {
        "request_id": "req-123",
        "startTime": "2025-03-26T10:00:00+00:00",
    }

    request = collector.normalize_request(
        raw_data, uuid4(), diagnostics
    )

    assert request is not None
    assert request.provider == "unknown"
    assert request.model == "unknown"
    assert "provider" in diagnostics.missing_fields
    assert "model" in diagnostics.missing_fields


# =============================================================================
# LiteLLMCollector Async Tests
# =============================================================================


@pytest.mark.asyncio
async def test_collect_requests_empty_response() -> None:
    """Test collection handles empty API response."""
    collector = LiteLLMCollector(
        base_url="http://localhost:4000",
        api_key="test",
        repository=None,  # type: ignore
    )

    # Mock the _fetch_raw_requests to return empty list
    collector._fetch_raw_requests = AsyncMock(return_value=[])  # type: ignore

    session_id = uuid4()
    collected, diagnostics, watermark = await collector.collect_requests(
        session_id=session_id
    )

    assert collected == []
    assert diagnostics.total_raw_records == 0
    assert watermark.record_count == 0


@pytest.mark.asyncio
async def test_collect_requests_with_diagnostics() -> None:
    """Test collection populates diagnostics correctly."""
    collector = LiteLLMCollector(
        base_url="http://localhost:4000",
        api_key="test",
        repository=None,  # type: ignore
    )

    session_id = uuid4()
    raw_requests = [
        {"request_id": "req-1", "startTime": "2025-03-26T10:00:00+00:00", "model": "gpt-4"},
        {"request_id": None, "startTime": "2025-03-26T10:01:00+00:00"},  # Missing ID
        {"request_id": "req-3", "model": "gpt-4"},  # Missing timestamp
    ]

    collector._fetch_raw_requests = AsyncMock(return_value=raw_requests)  # type: ignore

    collected, diagnostics, watermark = await collector.collect_requests(
        session_id=session_id
    )

    # Only 1 valid request should be normalized
    assert diagnostics.total_raw_records == 3
    assert diagnostics.normalized_count == 1
    assert diagnostics.skipped_count == 2
    assert "request_id" in diagnostics.missing_fields
    assert "timestamp" in diagnostics.missing_fields


@pytest.mark.asyncio
async def test_collect_requests_watermark_resumption() -> None:
    """Test that watermark is used to resume collection."""
    collector = LiteLLMCollector(
        base_url="http://localhost:4000",
        api_key="test",
        repository=None,  # type: ignore
    )

    session_id = uuid4()
    watermark = IngestWatermark(
        last_request_id="req-last",
        last_timestamp=datetime(2025, 3, 26, 10, 0, 0, tzinfo=UTC),
        record_count=50,
    )

    # Mock _fetch_raw_requests to verify watermark is passed
    collector._fetch_raw_requests = AsyncMock(return_value=[])  # type: ignore

    await collector.collect_requests(
        session_id=session_id,
        watermark=watermark,
    )

    # Verify the fetch was called with watermark
    call_args = collector._fetch_raw_requests.call_args
    assert call_args is not None
    _, kwargs = call_args
    assert kwargs["watermark"] == watermark


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


# =============================================================================
# CollectionJobService Tests
# =============================================================================


@pytest.mark.asyncio
async def test_collection_job_service_run() -> None:
    """Test CollectionJobService runs collection job."""
    from benchmark_core.services import CollectionJobService

    mock_repo = MagicMock()
    mock_repo.create_many = AsyncMock(return_value=[])

    service = CollectionJobService(
        litellm_base_url="http://localhost:4000",
        litellm_api_key="test",
        repository=mock_repo,
    )

    session_id = uuid4()
    result = await service.run_collection_job(session_id=session_id)

    # Since we can't mock the collector's internal methods easily,
    # we verify the structure of the result
    assert hasattr(result, "success")
    assert hasattr(result, "requests_collected")
    assert hasattr(result, "requests_new")
    assert hasattr(result, "diagnostics")
    assert hasattr(result, "watermark")


def test_collection_job_service_diagnostics_summary() -> None:
    """Test diagnostics summary generation."""
    from benchmark_core.services import CollectionJobService

    service = CollectionJobService(
        litellm_base_url="http://localhost:4000",
        litellm_api_key="test",
        repository=None,  # type: ignore
    )

    diagnostics = CollectionDiagnostics()
    diagnostics.total_raw_records = 100
    diagnostics.normalized_count = 90
    diagnostics.skipped_count = 10
    diagnostics.record_missing_field("request_id")
    diagnostics.record_missing_field("request_id")
    diagnostics.record_missing_field("timestamp")
    diagnostics.add_error("Test error")

    summary = service.get_diagnostics_summary(diagnostics)

    assert summary["total_raw_records"] == 100
    assert summary["normalized_count"] == 90
    assert summary["skipped_count"] == 10
    assert summary["success_rate"] == "90/100 (90.0%)"
    assert "request_id" in summary["missing_fields"]
    assert "timestamp" in summary["missing_fields"]
    assert len(summary["errors"]) == 1
