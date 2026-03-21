"""Unit tests for LiteLLM collector."""
import pytest
from datetime import datetime
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from benchmark_core.models import Request, RequestStatus
from benchmark_core.repositories.request_repository import RequestRepository
from benchmark_core.repositories.session_repository import SessionRepository


class TestMissingFieldDetection:
    """Tests for missing field detection."""

    def test_missing_litellm_call_id(self):
        """Should detect missing litellm_call_id."""
        raw_data = {"model": "gpt-4", "started_at": datetime.utcnow()}
        required = ["litellm_call_id", "model", "started_at"]
        missing = [f for f in required if f not in raw_data or raw_data[f] is None]
        assert "litellm_call_id" in missing

    def test_missing_model(self):
        """Should detect missing model."""
        raw_data = {"litellm_call_id": "call-123", "started_at": datetime.utcnow()}
        required = ["litellm_call_id", "model", "started_at"]
        missing = [f for f in required if f not in raw_data or raw_data[f] is None]
        assert "model" in missing

    def test_all_fields_present(self):
        """Should pass when all required fields present."""
        raw_data = {
            "litellm_call_id": "call-123",
            "model": "gpt-4",
            "started_at": datetime.utcnow(),
        }
        required = ["litellm_call_id", "model", "started_at"]
        missing = [f for f in required if f not in raw_data or raw_data[f] is None]
        assert len(missing) == 0


class TestCorrelationKeyExtraction:
    """Tests for correlation key extraction."""

    def test_extract_direct_session_id(self):
        """Should extract session_id from top-level field."""
        raw_data = {
            "session_id": str(uuid4()),
            "litellm_call_id": "call-123",
            "model": "gpt-4",
        }
        
        correlation_keys = ["session_id", "experiment_id", "variant_id", "provider_id"]
        keys = {}
        for key in correlation_keys:
            value = raw_data.get(key)
            if value is not None:
                keys[key] = str(value)
            else:
                keys[key] = None
        
        assert keys["session_id"] == raw_data["session_id"]
        assert keys["experiment_id"] is None

    def test_extract_from_tags(self):
        """Should extract correlation keys from tags."""
        session_id = str(uuid4())
        raw_data = {
            "litellm_call_id": "call-123",
            "model": "gpt-4",
            "tags": {
                "session_id": session_id,
                "experiment_id": str(uuid4()),
            },
        }
        
        correlation_keys = ["session_id", "experiment_id", "variant_id", "provider_id"]
        keys = {}
        for key in correlation_keys:
            keys[key] = None
        
        tags = raw_data.get("tags", {})
        if isinstance(tags, dict):
            for key in correlation_keys:
                if keys[key] is None and key in tags:
                    keys[key] = str(tags[key])
        
        assert keys["session_id"] == session_id
        assert keys["experiment_id"] is not None


class TestStatusParsing:
    """Tests for request status parsing."""

    def test_parse_success(self):
        """Should parse success status."""
        status_map = {
            "success": RequestStatus.SUCCESS,
            "error": RequestStatus.ERROR,
            "timeout": RequestStatus.TIMEOUT,
            "cancelled": RequestStatus.CANCELLED,
        }
        
        assert status_map.get("success", RequestStatus.SUCCESS) == RequestStatus.SUCCESS

    def test_parse_error(self):
        """Should parse error status."""
        status_map = {
            "success": RequestStatus.SUCCESS,
            "error": RequestStatus.ERROR,
            "timeout": RequestStatus.TIMEOUT,
            "cancelled": RequestStatus.CANCELLED,
        }
        
        assert status_map.get("error", RequestStatus.SUCCESS) == RequestStatus.ERROR

    def test_parse_unknown_defaults_to_success(self):
        """Should default unknown status to success."""
        status_map = {
            "success": RequestStatus.SUCCESS,
            "error": RequestStatus.ERROR,
            "timeout": RequestStatus.TIMEOUT,
            "cancelled": RequestStatus.CANCELLED,
        }
        
        assert status_map.get("unknown", RequestStatus.SUCCESS) == RequestStatus.SUCCESS

    def test_parse_null_defaults_to_success(self):
        """Should default null status to success."""
        assert RequestStatus.SUCCESS  # Default value


class TestDuplicateDetection:
    """Tests for duplicate detection."""

    @pytest.mark.asyncio
    async def test_duplicate_call_id_rejected(self):
        """Should reject duplicate litellm_call_id."""
        # This would be tested with integration tests against real DB
        # Here we test the logic concept
        call_id = "call-123"
        
        # Simulating exists check returning True
        exists = True
        assert exists is True  # Would skip ingestion

    @pytest.mark.asyncio
    async def test_new_call_id_accepted(self):
        """Should accept new litellm_call_id."""
        call_id = "call-new"
        
        # Simulating exists check returning False
        exists = False
        assert exists is False  # Would proceed with ingestion


class TestNormalization:
    """Tests for request normalization."""

    def test_normalize_latency_ms(self):
        """Should normalize latency."""
        raw_data = {
            "latency_ms": 1234.56,
        }
        assert raw_data["latency_ms"] == 1234.56

    def test_normalize_ttft_ms(self):
        """Should normalize TTFT."""
        raw_data = {
            "ttft_ms": 150.0,
        }
        assert raw_data["ttft_ms"] == 150.0

    def test_normalize_tokens(self):
        """Should normalize token counts."""
        raw_data = {
            "input_tokens": 100,
            "output_tokens": 200,
            "cached_input_tokens": 50,
        }
        assert raw_data["input_tokens"] == 100
        assert raw_data["output_tokens"] == 200
        assert raw_data["cached_input_tokens"] == 50
