"""Unit tests for the request normalization module."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from collectors.normalize_requests import (
    ReconciliationReport,
    RequestNormalizer,
    RequestNormalizerJob,
    UnmappedRowDiagnostics,
)

# =============================================================================
# UnmappedRowDiagnostics Tests
# =============================================================================


class TestUnmappedRowDiagnostics:
    """Tests for UnmappedRowDiagnostics dataclass."""

    def test_initial_state(self) -> None:
        """Test initial state of UnmappedRowDiagnostics."""
        diag = UnmappedRowDiagnostics(raw_data={"key": "value"})

        assert diag.raw_data == {"key": "value"}
        assert diag.reason == ""
        assert diag.missing_fields == []
        assert diag.error_message == ""
        assert diag.row_index is None

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        diag = UnmappedRowDiagnostics(
            raw_data={"id": "123", "name": "test"},
            reason="Missing required fields",
            missing_fields=["timestamp"],
            error_message="Parse error",
            row_index=5,
        )

        result = diag.to_dict()

        assert result["reason"] == "Missing required fields"
        assert result["missing_fields"] == ["timestamp"]
        assert result["error_message"] == "Parse error"
        assert result["row_index"] == 5
        assert result["raw_keys"] == ["id", "name"]

    def test_to_dict_with_none_raw_data(self) -> None:
        """Test to_dict with None raw_data."""
        diag = UnmappedRowDiagnostics(raw_data=None)  # type: ignore

        result = diag.to_dict()

        assert result["raw_keys"] == []


# =============================================================================
# ReconciliationReport Tests
# =============================================================================


class TestReconciliationReport:
    """Tests for ReconciliationReport dataclass."""

    def test_initial_state(self) -> None:
        """Test initial state of ReconciliationReport."""
        report = ReconciliationReport()

        assert report.total_rows == 0
        assert report.mapped_count == 0
        assert report.unmapped_count == 0
        assert report.missing_field_counts == {}
        assert report.error_counts == {}
        assert report.unmapped_diagnostics == []

    def test_add_mapped(self) -> None:
        """Test adding a mapped row."""
        report = ReconciliationReport()

        report.add_mapped()
        report.add_mapped()

        assert report.total_rows == 2
        assert report.mapped_count == 2
        assert report.unmapped_count == 0

    def test_add_unmapped(self) -> None:
        """Test adding an unmapped row."""
        report = ReconciliationReport()
        raw = {"request_id": "123"}

        report.add_unmapped(
            raw_data=raw,
            reason="Missing timestamp",
            missing_fields=["timestamp"],
            error_message="Parse failed",
            row_index=0,
        )

        assert report.total_rows == 1
        assert report.mapped_count == 0
        assert report.unmapped_count == 1
        assert report.missing_field_counts["timestamp"] == 1
        assert report.error_counts["parse_error"] == 1
        assert len(report.unmapped_diagnostics) == 1

    def test_add_unmapped_without_fields(self) -> None:
        """Test adding unmapped row without missing fields."""
        report = ReconciliationReport()

        report.add_unmapped(
            raw_data={},
            reason="Invalid type",
        )

        assert report.total_rows == 1
        assert report.unmapped_count == 1
        assert report.missing_field_counts == {}

    def test_success_rate_calculation(self) -> None:
        """Test success rate calculation."""
        report = ReconciliationReport()

        assert report.success_rate == 0.0

        report.add_mapped()
        report.add_mapped()
        report.add_unmapped(raw_data={}, reason="test")

        # Allow for floating point precision differences
        assert abs(report.success_rate - 66.67) < 0.1

    def test_success_rate_zero_rows(self) -> None:
        """Test success rate with zero rows."""
        report = ReconciliationReport()

        assert report.success_rate == 0.0

    def test_to_markdown(self) -> None:
        """Test markdown report generation."""
        report = ReconciliationReport()
        report.add_mapped()
        report.add_mapped()
        report.add_unmapped(
            raw_data={"id": "1"},
            reason="Missing request_id",
            missing_fields=["request_id"],
            row_index=2,
        )

        markdown = report.to_markdown()

        assert "# Request Normalization Reconciliation Report" in markdown
        assert "**Total Rows**: 3" in markdown
        assert "**Mapped**: 2" in markdown
        assert "**Unmapped**: 1" in markdown
        assert "## Missing Field Counts" in markdown
        assert "request_id" in markdown

    def test_to_markdown_without_unmapped(self) -> None:
        """Test markdown report with no unmapped rows."""
        report = ReconciliationReport()
        report.add_mapped()

        markdown = report.to_markdown()

        assert "# Request Normalization Reconciliation Report" in markdown
        assert "**Unmapped**: 0" in markdown
        assert "## Missing Field Counts" not in markdown

    def test_to_dict(self) -> None:
        """Test dictionary report generation."""
        report = ReconciliationReport()
        report.add_mapped()
        report.add_unmapped(
            raw_data={"id": "1"},
            reason="Missing field",
            missing_fields=["timestamp"],
            row_index=0,
        )

        result = report.to_dict()

        assert result["summary"]["total_rows"] == 2
        assert result["summary"]["mapped_count"] == 1
        assert result["summary"]["unmapped_count"] == 1
        assert result["summary"]["success_rate_percent"] == 50.0
        assert result["missing_field_counts"]["timestamp"] == 1
        assert len(result["unmapped_rows"]) == 1

    def test_diagnostics_limit(self) -> None:
        """Test that diagnostics are limited to 100 entries."""
        report = ReconciliationReport()

        for i in range(150):
            report.add_unmapped(
                raw_data={"index": i},
                reason="Test",
                row_index=i,
            )

        assert len(report.unmapped_diagnostics) == 100
        assert report.unmapped_count == 150


# =============================================================================
# RequestNormalizer Tests
# =============================================================================


class TestRequestNormalizer:
    """Tests for RequestNormalizer class."""

    def test_normalize_valid_data(self) -> None:
        """Test normalizing valid LiteLLM request data."""
        session_id = uuid4()
        normalizer = RequestNormalizer(session_id)

        raw = {
            "request_id": "req-123",
            "startTime": "2025-03-26T10:30:00+00:00",
            "model": "gpt-4",
            "user": "test-user",
            "latency": 1.5,
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
            },
        }

        result, diag = normalizer.normalize(raw)

        assert result is not None
        assert diag is None
        assert result.request_id == "req-123"
        assert result.session_id == session_id
        assert result.provider == "test-user"
        assert result.model == "gpt-4"
        assert result.latency_ms == 1500.0  # Converted from seconds
        assert result.tokens_prompt == 100
        assert result.tokens_completion == 50

    def test_normalize_missing_request_id(self) -> None:
        """Test normalizing data missing request_id."""
        session_id = uuid4()
        normalizer = RequestNormalizer(session_id)

        raw = {
            "startTime": "2025-03-26T10:30:00+00:00",
            "model": "gpt-4",
        }

        result, diag = normalizer.normalize(raw, row_index=5)

        assert result is None
        assert diag is not None
        assert diag.reason == "Missing required fields"
        assert "request_id" in diag.missing_fields
        assert diag.row_index == 5

    def test_normalize_missing_timestamp(self) -> None:
        """Test normalizing data missing timestamp."""
        session_id = uuid4()
        normalizer = RequestNormalizer(session_id)

        raw = {
            "request_id": "req-123",
            "model": "gpt-4",
        }

        result, diag = normalizer.normalize(raw)

        assert result is None
        assert diag is not None
        assert "timestamp" in diag.missing_fields

    def test_normalize_invalid_timestamp(self) -> None:
        """Test normalizing data with invalid timestamp."""
        session_id = uuid4()
        normalizer = RequestNormalizer(session_id)

        raw = {
            "request_id": "req-123",
            "startTime": "invalid-timestamp",
            "model": "gpt-4",
        }

        result, diag = normalizer.normalize(raw)

        assert result is None
        assert diag is not None
        assert diag.reason == "Failed to parse timestamp"
        assert "timestamp" in diag.missing_fields

    def test_normalize_timestamp_variants(self) -> None:
        """Test normalizing with various timestamp formats."""
        session_id = uuid4()
        normalizer = RequestNormalizer(session_id)

        # ISO format with Z
        raw1 = {
            "request_id": "req-1",
            "startTime": "2025-03-26T10:30:00Z",
            "model": "gpt-4",
        }
        result1, _ = normalizer.normalize(raw1)
        assert result1 is not None
        assert result1.timestamp == datetime(2025, 3, 26, 10, 30, 0, tzinfo=UTC)

        # Unix timestamp
        raw2 = {
            "request_id": "req-2",
            "timestamp": 1711441800.0,
            "model": "gpt-4",
        }
        result2, _ = normalizer.normalize(raw2)
        assert result2 is not None

        # created_at field
        raw3 = {
            "request_id": "req-3",
            "created_at": "2025-03-26T10:30:00+00:00",
            "model": "gpt-4",
        }
        result3, _ = normalizer.normalize(raw3)
        assert result3 is not None

    def test_normalize_non_dict_data(self) -> None:
        """Test normalizing non-dictionary data."""
        session_id = uuid4()
        normalizer = RequestNormalizer(session_id)

        result, diag = normalizer.normalize("not-a-dict")  # type: ignore

        assert result is None
        assert diag is not None
        assert diag.reason == "Invalid data type - expected dict"

    def test_normalize_unknown_provider_model(self) -> None:
        """Test normalizing data without provider/model."""
        session_id = uuid4()
        normalizer = RequestNormalizer(session_id)

        raw = {
            "request_id": "req-123",
            "startTime": "2025-03-26T10:30:00+00:00",
        }

        result, _ = normalizer.normalize(raw)

        assert result is not None
        assert result.provider == "unknown"
        assert result.model == "unknown"

    def test_normalize_correlation_keys_in_metadata(self) -> None:
        """Test that correlation keys are preserved in metadata."""
        session_id = uuid4()
        normalizer = RequestNormalizer(session_id)

        raw = {
            "request_id": "req-123",
            "startTime": "2025-03-26T10:30:00+00:00",
            "model": "gpt-4",
            "experiment_id": "exp-1",
            "variant_id": "var-1",
            "task_card_id": "task-1",
        }

        result, _ = normalizer.normalize(raw)

        assert result is not None
        assert result.request_metadata.get("experiment_id") == "exp-1"
        assert result.request_metadata.get("variant_id") == "var-1"
        assert result.request_metadata.get("task_card_id") == "task-1"

    def test_normalize_correlation_keys_in_nested_metadata(self) -> None:
        """Test that correlation keys are found in nested metadata."""
        session_id = uuid4()
        normalizer = RequestNormalizer(session_id)

        raw = {
            "request_id": "req-123",
            "startTime": "2025-03-26T10:30:00+00:00",
            "model": "gpt-4",
            "metadata": {
                "session_id": "sess-1",
                "trace_id": "trace-1",
            },
        }

        result, _ = normalizer.normalize(raw)

        assert result is not None
        assert result.request_metadata.get("session_id") == "sess-1"
        assert result.request_metadata.get("trace_id") == "trace-1"

    def test_normalize_error_extraction(self) -> None:
        """Test error extraction from various formats."""
        session_id = uuid4()
        normalizer = RequestNormalizer(session_id)

        # Error as string
        raw1 = {
            "request_id": "req-1",
            "startTime": "2025-03-26T10:30:00+00:00",
            "model": "gpt-4",
            "error": "Rate limit exceeded",
        }
        result1, _ = normalizer.normalize(raw1)
        assert result1 is not None
        assert result1.error is True
        assert result1.error_message == "Rate limit exceeded"

        # Error as dict
        raw2 = {
            "request_id": "req-2",
            "startTime": "2025-03-26T10:30:00+00:00",
            "model": "gpt-4",
            "error": {"message": "Invalid API key"},
        }
        result2, _ = normalizer.normalize(raw2)
        assert result2 is not None
        assert result2.error is True
        assert result2.error_message == "Invalid API key"

        # Error in response
        raw3 = {
            "request_id": "req-3",
            "startTime": "2025-03-26T10:30:00+00:00",
            "model": "gpt-4",
            "response": {"error": "Timeout"},
        }
        result3, _ = normalizer.normalize(raw3)
        assert result3 is not None
        assert result3.error is True
        assert result3.error_message == "Timeout"

    def test_normalize_cache_hit_variants(self) -> None:
        """Test cache hit extraction variants."""
        session_id = uuid4()
        normalizer = RequestNormalizer(session_id)

        # cache_hit field
        raw1 = {
            "request_id": "req-1",
            "startTime": "2025-03-26T10:30:00+00:00",
            "model": "gpt-4",
            "cache_hit": True,
        }
        result1, _ = normalizer.normalize(raw1)
        assert result1 is not None
        assert result1.cache_hit is True

        # cached field
        raw2 = {
            "request_id": "req-2",
            "startTime": "2025-03-26T10:30:00+00:00",
            "model": "gpt-4",
            "cached": False,
        }
        result2, _ = normalizer.normalize(raw2)
        assert result2 is not None
        assert result2.cache_hit is False

        # Missing (should be None)
        raw3 = {
            "request_id": "req-3",
            "startTime": "2025-03-26T10:30:00+00:00",
            "model": "gpt-4",
        }
        result3, _ = normalizer.normalize(raw3)
        assert result3 is not None
        assert result3.cache_hit is None


# =============================================================================
# RequestNormalizerJob Tests
# =============================================================================


class TestRequestNormalizerJob:
    """Tests for RequestNormalizerJob class."""

    @pytest.mark.asyncio
    async def test_run_empty_list(self) -> None:
        """Test running job with empty raw requests list."""
        mock_repo = MagicMock()
        session_id = uuid4()
        job = RequestNormalizerJob(repository=mock_repo, session_id=session_id)

        written, report = await job.run([])

        assert written == []
        assert report.total_rows == 0
        assert report.mapped_count == 0

    @pytest.mark.asyncio
    async def test_run_successful_normalization(self) -> None:
        """Test successful normalization and writing."""
        mock_repo = MagicMock()
        mock_repo.create_many = AsyncMock(return_value=[])

        session_id = uuid4()
        job = RequestNormalizerJob(repository=mock_repo, session_id=session_id)

        raw_requests = [
            {
                "request_id": "req-1",
                "startTime": "2025-03-26T10:30:00+00:00",
                "model": "gpt-4",
            },
            {
                "request_id": "req-2",
                "startTime": "2025-03-26T10:31:00+00:00",
                "model": "gpt-3.5",
            },
        ]

        written, report = await job.run(raw_requests)

        assert report.total_rows == 2
        assert report.mapped_count == 2
        assert report.unmapped_count == 0
        mock_repo.create_many.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_with_unmapped_rows(self) -> None:
        """Test normalization with some unmapped rows."""
        mock_repo = MagicMock()
        mock_repo.create_many = AsyncMock(return_value=[])

        session_id = uuid4()
        job = RequestNormalizerJob(repository=mock_repo, session_id=session_id)

        raw_requests = [
            {
                "request_id": "req-1",
                "startTime": "2025-03-26T10:30:00+00:00",
                "model": "gpt-4",
            },
            {
                # Missing request_id
                "startTime": "2025-03-26T10:31:00+00:00",
                "model": "gpt-3.5",
            },
            {
                # Missing timestamp
                "request_id": "req-3",
                "model": "gpt-4",
            },
        ]

        written, report = await job.run(raw_requests)

        assert report.total_rows == 3
        assert report.mapped_count == 1
        assert report.unmapped_count == 2
        assert report.missing_field_counts.get("request_id") == 1
        assert report.missing_field_counts.get("timestamp") == 1

    @pytest.mark.asyncio
    async def test_run_repository_failure(self) -> None:
        """Test handling of repository failure."""
        mock_repo = MagicMock()
        mock_repo.create_many = AsyncMock(side_effect=Exception("DB Error"))

        session_id = uuid4()
        job = RequestNormalizerJob(repository=mock_repo, session_id=session_id)

        raw_requests = [
            {
                "request_id": "req-1",
                "startTime": "2025-03-26T10:30:00+00:00",
                "model": "gpt-4",
            },
        ]

        written, report = await job.run(raw_requests)

        assert written == []
        assert report.total_rows == 2  # 1 mapped + 1 failed insert
        assert report.unmapped_count == 1  # The failed insert

    @pytest.mark.asyncio
    async def test_run_all_invalid_data(self) -> None:
        """Test running with all invalid data."""
        mock_repo = MagicMock()

        session_id = uuid4()
        job = RequestNormalizerJob(repository=mock_repo, session_id=session_id)

        raw_requests = [
            "not-a-dict",
            None,
            [],
        ]

        written, report = await job.run(raw_requests)

        assert written == []
        assert report.total_rows == 3
        assert report.mapped_count == 0
        assert report.unmapped_count == 3
        mock_repo.create_many.assert_not_called()

    @pytest.mark.asyncio
    async def test_run_with_validation(self) -> None:
        """Test run_with_validation method."""
        mock_repo = MagicMock()
        mock_repo.create_many = AsyncMock(return_value=[])

        session_id = uuid4()
        job = RequestNormalizerJob(repository=mock_repo, session_id=session_id)

        raw_requests = [
            {
                "request_id": "req-1",
                "startTime": "2025-03-26T10:30:00+00:00",
                "model": "gpt-4",
            },
        ]

        written, report = await job.run_with_validation(raw_requests)

        assert report.total_rows == 1
        assert report.mapped_count == 1
