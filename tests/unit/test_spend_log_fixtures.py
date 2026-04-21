"""Smoke tests for LiteLLM spend-log fixture loading."""

import json
from pathlib import Path

import pytest

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "litellm_spend_logs"


@pytest.fixture
def load_fixture():
    """Helper to load a JSON fixture by filename."""

    def _load(name: str) -> dict:
        path = FIXTURE_DIR / name
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    return _load


class TestSpendLogFixtures:
    """Smoke tests that fixtures load and contain expected shape."""

    @pytest.mark.parametrize(
        "filename",
        [
            "successful_request.json",
            "failed_request.json",
            "streaming_request.json",
            "cached_request.json",
            "sparse_request.json",
        ],
    )
    def test_fixture_loads_as_valid_json(self, filename: str) -> None:
        """Each fixture file parses as valid JSON."""
        path = FIXTURE_DIR / filename
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data, dict)

    def test_successful_request_shape(self, load_fixture) -> None:
        """Successful request fixture has required fields."""
        data = load_fixture("successful_request.json")
        assert data["request_id"] == "req-success-001"
        assert data["status"] == "success"
        assert data["error"] is None
        assert data["error_code"] is None
        assert data["stream"] is False
        assert data["cache_hit"] is False
        assert data["spend"] > 0
        assert data["prompt_tokens"] > 0
        assert data["completion_tokens"] > 0
        assert isinstance(data["metadata"], dict)

    def test_failed_request_shape(self, load_fixture) -> None:
        """Failed request fixture reflects error state."""
        data = load_fixture("failed_request.json")
        assert data["request_id"] == "req-failed-001"
        assert data["status"] == "failure"
        assert data["error"] == "Rate limit exceeded"
        assert data["error_code"] == "429"
        assert data["spend"] == 0.0
        assert data["prompt_tokens"] == 0
        assert data["completion_tokens"] == 0
        assert data["ttft"] is None

    def test_streaming_request_shape(self, load_fixture) -> None:
        """Streaming request fixture has stream flag."""
        data = load_fixture("streaming_request.json")
        assert data["request_id"] == "req-stream-001"
        assert data["stream"] is True
        assert data["status"] == "success"
        assert data["ttft"] is not None
        assert data["ttft"] < data["latency"]

    def test_cached_request_shape(self, load_fixture) -> None:
        """Cached request fixture shows cache hit."""
        data = load_fixture("cached_request.json")
        assert data["request_id"] == "req-cached-001"
        assert data["cache_hit"] is True
        assert data["cached_input_tokens"] > 0
        assert data["latency"] < 1.0  # Fast due to cache
        assert data["spend"] < 0.001  # Cheap due to cache
        # Non-streaming: ttft fields should be null
        assert data["ttft"] is None
        assert data["time_to_first_token"] is None
        assert data["completion_start_time"] is None

    def test_sparse_request_absent_best_effort_fields(self, load_fixture) -> None:
        """Sparse fixture omits best-effort fields that LiteLLM may not expose."""
        data = load_fixture("sparse_request.json")
        assert data["request_id"] == "req-sparse-001"
        assert data["status"] == "success"
        assert data["stream"] is False
        # These best-effort fields are *absent*, not just null
        assert "ttft" not in data
        assert "time_to_first_token" not in data
        assert "completion_start_time" not in data
        assert "endTime" not in data
        assert "error" not in data
        assert "error_code" not in data
        assert "cache_write_tokens" not in data
        assert "cached_input_tokens" not in data
        # Stable fields are still present
        assert data["model"] == "gpt-4o-mini"
        assert data["latency"] == 1.2

    def test_no_real_secrets_in_fixtures(self, load_fixture) -> None:
        """Verify fixtures use synthetic/redacted values only."""
        for name in [
            "successful_request.json",
            "failed_request.json",
            "streaming_request.json",
            "cached_request.json",
            "sparse_request.json",
        ]:
            data = load_fixture(name)
            api_key = data.get("api_key", "")
            assert "sk-litellm-hash-" in api_key, f"{name}: expected synthetic key prefix"
            assert "sk-proj" not in api_key, f"{name}: contains possible real key"
            assert "sk-ant" not in api_key, f"{name}: contains possible real key"
            # No prompt/response content
            assert "messages" not in data, f"{name}: contains prompt content"
            assert "choices" not in data, f"{name}: contains response content"

    def test_all_fixtures_have_stable_fields(self, load_fixture) -> None:
        """Every fixture has the stable fields we depend on."""
        stable_fields = [
            "request_id",
            "call_id",
            "api_key",
            "startTime",
            "model",
            "requested_model",
            "provider",
            "total_tokens",
            "prompt_tokens",
            "completion_tokens",
            "stream",
            "latency",
            "total_latency",
            "status",
        ]
        for name in [
            "successful_request.json",
            "failed_request.json",
            "streaming_request.json",
            "cached_request.json",
            "sparse_request.json",
        ]:
            data = load_fixture(name)
            missing = [f for f in stable_fields if f not in data]
            assert not missing, f"{name}: missing stable fields {missing}"

    def test_best_effort_fields_present_in_full_fixtures(self, load_fixture) -> None:
        """Full fixtures carry best-effort fields; sparse fixture may omit them."""
        best_effort_fields = [
            "api_key_alias",
            "cache_hit",
            "spend",
        ]
        full_fixtures = [
            "successful_request.json",
            "failed_request.json",
            "streaming_request.json",
            "cached_request.json",
        ]
        for name in full_fixtures:
            data = load_fixture(name)
            missing = [f for f in best_effort_fields if f not in data]
            assert not missing, f"{name}: missing best-effort fields {missing}"
