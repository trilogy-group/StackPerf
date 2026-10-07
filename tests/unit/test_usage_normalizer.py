"""Fixture-driven tests for sessionless usage normalization and collection."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from benchmark_core.db.models import Base, Experiment, ProxyKey, TaskCard, Variant
from benchmark_core.db.models import Session as SessionORM
from benchmark_core.db.models import UsageRequest as UsageRequestORM
from benchmark_core.repositories.proxy_key_repository import SQLProxyKeyRepository
from benchmark_core.repositories.session_repository import SQLSessionRepository
from benchmark_core.repositories.usage_request_repository import SQLUsageRequestRepository
from collectors import (
    LiteLLMUsageCollector,
    ProxyKeyAttributionResolver,
    UsageReconciliationReport,
    UsageRequestNormalizer,
)
from collectors.extraction import (
    extract_cache_fields,
    extract_error_fields,
    extract_latency_ms,
    extract_ttft_ms,
    parse_timestamp,
)
from collectors.key_attribution import key_fingerprint
from collectors.normalize_requests import SKIP_MISSING_STABLE_ID, apply_key_attribution

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "litellm_spend_logs"


def load_fixture(name: str) -> dict[str, Any]:
    with open(FIXTURES_DIR / f"{name}.json") as handle:
        data: dict[str, Any] = json.load(handle)
    return data


def all_fixtures() -> list[dict[str, Any]]:
    return [json.loads(path.read_text()) for path in sorted(FIXTURES_DIR.glob("*.json"))]


def orm_values(row: UsageRequestORM) -> dict[str, Any]:
    return {column.name: getattr(row, column.name) for column in UsageRequestORM.__table__.columns}


@pytest.fixture
def normalizer() -> UsageRequestNormalizer:
    return UsageRequestNormalizer()


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


class TestFixtureMapping:
    """Normalizer maps key, model, tokens, cost, latency, TTFT, errors, timestamps."""

    def test_successful_request(self, normalizer):
        result = normalizer.normalize(load_fixture("successful_request"), row_index=0)
        row = result.usage_request

        assert row is not None
        assert result.diagnostics.outcome == "mapped"
        assert result.diagnostics.missing_fields == []
        assert row.litellm_call_id == "req-success-001"
        assert row.request_id == "req-success-001"
        assert row.key_alias == "bench-session-alpha"
        assert row.provider == "openai"
        assert row.provider_route == "openai"
        assert row.requested_model == "gpt-4o"
        assert row.resolved_model == "gpt-4o"
        assert row.input_tokens == 50
        assert row.output_tokens == 100
        assert row.cached_input_tokens == 0
        assert row.cache_write_tokens == 0
        assert row.cost_usd == pytest.approx(0.00525)
        assert row.latency_ms == pytest.approx(2500.0)
        assert row.ttft_ms is None
        assert row.started_at == datetime(2025, 4, 21, 10, 0, 0, tzinfo=UTC)
        assert row.finished_at == datetime(2025, 4, 21, 10, 0, 2, 500000, tzinfo=UTC)
        assert row.status == "success"
        assert row.error_code is None
        assert row.error_message is None
        assert row.cache_hit is False
        assert row.request_metadata["stream"] is False

    def test_failed_request(self, normalizer):
        row = normalizer.normalize(load_fixture("failed_request")).usage_request
        assert row is not None
        assert row.status == "failure"
        assert row.error_code == "429"
        assert row.error_message == "Rate limit exceeded"
        assert row.input_tokens == 0
        assert row.cost_usd == 0.0
        assert row.latency_ms == pytest.approx(1200.0)

    def test_streaming_request(self, normalizer):
        result = normalizer.normalize(load_fixture("streaming_request"))
        row = result.usage_request
        assert row is not None
        assert result.diagnostics.outcome == "mapped"
        assert row.ttft_ms == pytest.approx(650.0)
        assert row.latency_ms == pytest.approx(8750.0)
        assert row.output_tokens == 400
        assert row.request_metadata["stream"] is True

    def test_cached_request(self, normalizer):
        row = normalizer.normalize(load_fixture("cached_request")).usage_request
        assert row is not None
        assert row.cache_hit is True
        assert row.cached_input_tokens == 20
        assert row.cache_write_tokens == 0
        assert row.latency_ms == pytest.approx(150.0)

    def test_non_streaming_ttft_derived_from_completion_start(self, normalizer):
        row = normalizer.normalize(
            load_fixture("non_streaming_with_completion_start")
        ).usage_request
        assert row is not None
        assert row.ttft_ms == pytest.approx(1500.0)

    def test_sparse_request_is_partially_mapped(self, normalizer):
        result = normalizer.normalize(load_fixture("sparse_request"), row_index=4)
        row = result.usage_request
        assert row is not None
        assert row.litellm_call_id == "req-sparse-001"
        assert row.key_alias is None
        assert row.finished_at is None
        assert row.cost_usd is None
        assert row.latency_ms == pytest.approx(1200.0)
        assert result.diagnostics.outcome == "partial"
        assert set(result.diagnostics.missing_fields) == {"endTime", "spend", "api_key_alias"}
        assert result.key_reference == "sk-litellm-hash-e5f6g7h8i9j0"

    def test_call_id_fallback_is_stable_id(self, normalizer):
        result = normalizer.normalize(load_fixture("fallback_to_call_id"))
        row = result.usage_request
        assert row is not None
        assert row.litellm_call_id == "call-fallback-001"
        assert row.request_id is None

    @pytest.mark.parametrize("fixture", all_fixtures(), ids=lambda f: str(f.get("call_id")))
    def test_raw_api_key_never_persisted(self, normalizer, fixture):
        row = normalizer.normalize(fixture).usage_request
        assert row is not None
        serialized = json.dumps(orm_values(row), default=str)
        assert fixture["api_key"] not in serialized
        assert row.litellm_key_id is None


class TestStableIdentifiers:
    def test_missing_request_and_call_id_is_skipped_with_diagnostics(self, normalizer):
        raw = load_fixture("successful_request")
        del raw["request_id"]
        del raw["call_id"]

        result = normalizer.normalize(raw, row_index=7)

        assert result.usage_request is None
        assert result.diagnostics.outcome == "skipped"
        assert result.diagnostics.reason == SKIP_MISSING_STABLE_ID
        assert result.diagnostics.missing_fields == ["request_id", "call_id"]
        assert result.diagnostics.row_index == 7
        assert "model" in result.diagnostics.raw_keys

    def test_empty_request_id_falls_back_to_call_id(self, normalizer):
        raw = load_fixture("failed_request")
        raw["request_id"] = ""
        row = normalizer.normalize(raw).usage_request
        assert row is not None
        assert row.litellm_call_id == "call-failed-001"

    def test_non_object_record_is_skipped(self, normalizer):
        result = normalizer.normalize(["not", "a", "row"], row_index=1)
        assert result.usage_request is None
        assert result.diagnostics.reason == "invalid_record_type"


class TestSessionMetadata:
    def test_records_without_session_metadata_are_accepted(self, normalizer):
        result = normalizer.normalize(load_fixture("sparse_request"))
        row = result.usage_request
        assert row is not None
        assert row.benchmark_session_id is None
        assert result.benchmark_session_candidate is None
        for join_field in ("benchmark_session_id", "experiment_id", "variant_id"):
            assert join_field not in row.request_metadata

    def test_fixture_session_metadata_preserves_join_fields(self, normalizer):
        result = normalizer.normalize(load_fixture("successful_request"))
        row = result.usage_request
        assert row is not None
        assert row.request_metadata["benchmark_session_id"] == "session-alpha-001"
        assert row.request_metadata["experiment_id"] == "model-comparison-q2"
        assert row.request_metadata["variant_id"] == "openai-gpt4o"
        assert row.request_metadata["task_card_id"] == "repo-auth-analysis"
        assert row.request_metadata["harness_profile"] == "openhands"
        # Non-UUID session identifiers cannot populate the FK column.
        assert row.benchmark_session_id is None
        assert result.benchmark_session_candidate is None
        assert any("not a UUID" in note for note in result.diagnostics.notes)

    def test_credential_service_tags_in_spend_logs_metadata(self, normalizer):
        session_id = uuid4()
        raw = load_fixture("sparse_request")
        raw["metadata"] = {
            "spend_logs_metadata": {
                "benchmark_session_id": str(session_id),
                "benchmark_experiment_id": "exp-1",
                "benchmark_variant_id": "var-1",
                "benchmark_harness_profile": "claude-code",
                "benchmark_task_card_id": "task-1",
                "trace_id": "trace-abc",
            }
        }
        result = normalizer.normalize(raw)
        row = result.usage_request
        assert row is not None
        assert result.benchmark_session_candidate == session_id
        assert row.request_metadata["benchmark_session_id"] == str(session_id)
        assert row.request_metadata["experiment_id"] == "exp-1"
        assert row.request_metadata["variant_id"] == "var-1"
        assert row.request_metadata["harness_profile"] == "claude-code"
        assert row.request_metadata["task_card_id"] == "task-1"
        assert row.request_metadata["trace_id"] == "trace-abc"

    def test_session_metadata_from_request_tags(self, normalizer):
        session_id = uuid4()
        raw = load_fixture("sparse_request")
        raw["request_tags"] = json.dumps(
            [f"benchmark_session_id:{session_id}", "benchmark_variant_id=v2", "team-a"]
        )
        result = normalizer.normalize(raw)
        row = result.usage_request
        assert row is not None
        assert result.benchmark_session_candidate == session_id
        assert row.request_metadata["variant_id"] == "v2"
        assert "team-a" in row.request_metadata["request_tags"]

    def test_top_level_litellm_session_id_is_not_benchmark_session(self, normalizer):
        raw = load_fixture("sparse_request")
        raw["session_id"] = str(uuid4())
        result = normalizer.normalize(raw)
        row = result.usage_request
        assert row is not None
        assert result.benchmark_session_candidate is None
        assert "benchmark_session_id" not in row.request_metadata
        assert row.request_metadata["litellm_session_id"] == raw["session_id"]


class TestMetadataRedaction:
    def test_content_and_unknown_metadata_are_dropped(self, normalizer):
        raw = load_fixture("successful_request")
        raw["messages"] = [{"role": "user", "content": "secret prompt"}]
        raw["response"] = {"choices": [{"message": {"content": "secret answer"}}]}
        raw["proxy_server_request"] = {"body": {"messages": "secret prompt"}}
        raw["metadata"]["headers"] = {"authorization": "Bearer abc"}
        raw["metadata"]["arbitrary_blob"] = {"nested": "secret prompt"}

        row = normalizer.normalize(raw).usage_request
        assert row is not None
        serialized = json.dumps(row.request_metadata)
        assert "secret prompt" not in serialized
        assert "secret answer" not in serialized
        assert "headers" not in row.request_metadata
        assert "arbitrary_blob" not in row.request_metadata

    def test_secret_values_in_metadata_are_redacted(self, normalizer):
        raw = load_fixture("successful_request")
        raw["metadata"]["experiment"] = "sk-abcdefghijklmnopqrstuvwx1234"
        raw["metadata"]["user_api_key"] = "sk-abcdefghijklmnopqrstuvwx1234"
        row = normalizer.normalize(raw).usage_request
        assert row is not None
        assert row.request_metadata["experiment_id"] == "[REDACTED]"
        assert "sk-abcdefghijklmnopqrstuvwx1234" not in json.dumps(orm_values(row), default=str)

    def test_secret_values_in_error_message_are_redacted(self, normalizer):
        raw = load_fixture("failed_request")
        raw["error"] = "Invalid key sk-abcdefghijklmnopqrstuvwx1234 provided"
        row = normalizer.normalize(raw).usage_request
        assert row is not None
        assert row.error_message is not None
        assert "sk-abcdefghijklmnopqrstuvwx1234" not in row.error_message
        assert "[REDACTED]" in row.error_message


class TestLiteLLMNativeShape:
    """Records shaped like LiteLLM's SpendLogs table rows."""

    def test_json_string_metadata_and_string_cache_hit(self, normalizer):
        raw = {
            "request_id": "chatcmpl-123",
            "api_key": "88dc28d0f030c55ed4ab77ed8faf098196cb1c05df778539800c9f1243fe6b4b",
            "model": "anthropic/claude-sonnet",
            "model_group": "claude-sonnet",
            "custom_llm_provider": "anthropic",
            "call_type": "acompletion",
            "spend": 0.01,
            "prompt_tokens": 100,
            "completion_tokens": 20,
            "startTime": "2025-04-21T10:00:00+00:00",
            "endTime": "2025-04-21T10:00:01+00:00",
            "completionStartTime": "2025-04-21T10:00:00.400000+00:00",
            "cache_hit": "True",
            "session_id": "litellm-trace",
            "messages": [{"role": "user", "content": "hello"}],
            "metadata": json.dumps(
                {
                    "user_api_key_alias": "team-alpha-key",
                    "status": "success",
                    "additional_usage_values": {
                        "cache_read_input_tokens": 80,
                        "cache_creation_input_tokens": 5,
                    },
                }
            ),
        }
        result = normalizer.normalize(raw)
        row = result.usage_request
        assert row is not None
        assert result.diagnostics.outcome == "mapped"
        assert row.key_alias == "team-alpha-key"
        assert row.provider == "anthropic"
        assert row.requested_model == "claude-sonnet"
        assert row.route == "acompletion"
        assert row.latency_ms == pytest.approx(1000.0)
        assert row.ttft_ms == pytest.approx(400.0)
        assert row.cache_hit is True
        assert row.cached_input_tokens == 80
        assert row.cache_write_tokens == 5
        assert "messages" not in row.request_metadata

    def test_failure_from_metadata_error_information(self, normalizer):
        raw = {
            "request_id": "chatcmpl-err",
            "model": "gpt-4o",
            "metadata": {
                "status": "failure",
                "error_information": {"error_code": "500", "error_message": "upstream boom"},
            },
        }
        row = normalizer.normalize(raw).usage_request
        assert row is not None
        assert row.status == "failure"
        assert row.error_code == "500"
        assert row.error_message == "upstream boom"


class TestExtractionHelpers:
    def test_latency_prefers_seconds_then_duration_then_timestamps(self):
        assert extract_latency_ms({"latency": 1.5}) == pytest.approx(1500.0)
        assert extract_latency_ms({"request_duration_ms": 42}) == pytest.approx(42.0)
        assert extract_latency_ms(
            {"startTime": "2025-01-01T00:00:00Z", "endTime": "2025-01-01T00:00:00.250Z"}
        ) == pytest.approx(250.0)
        assert extract_latency_ms({}) is None

    def test_ttft_ignores_negative_derivation(self):
        raw = {"startTime": "2025-01-01T00:00:01Z", "completion_start_time": "2025-01-01T00:00:00Z"}
        assert extract_ttft_ms(raw) is None

    def test_parse_timestamp_variants(self):
        assert parse_timestamp("2025-01-01T00:00:00") == datetime(2025, 1, 1, tzinfo=UTC)
        assert parse_timestamp(0) == datetime(1970, 1, 1, tzinfo=UTC)
        assert parse_timestamp("not-a-date") is None

    def test_cache_and_error_defaults(self):
        assert extract_cache_fields({"cache_hit": "False"}).cache_hit is False
        assert extract_cache_fields({}).cache_hit is None
        assert extract_error_fields({}).status == "success"
        assert extract_error_fields({"error": "boom"}).status == "failure"


class FakeKeyRepo:
    def __init__(self, keys: list[ProxyKey]) -> None:
        self.keys = keys
        self.calls = 0

    async def get_by_litellm_key_id(self, litellm_key_id: str) -> ProxyKey | None:
        self.calls += 1
        return next((k for k in self.keys if k.litellm_key_id == litellm_key_id), None)

    async def get_by_alias(self, key_alias: str) -> ProxyKey | None:
        self.calls += 1
        return next((k for k in self.keys if k.key_alias == key_alias), None)


def make_key(alias: str, litellm_key_id: str | None = None) -> ProxyKey:
    return ProxyKey(id=uuid4(), key_alias=alias, litellm_key_id=litellm_key_id, owner="o", team="t")


class TestKeyAttribution:
    async def test_resolve_by_litellm_key_id(self):
        key = make_key("registry-alias", "sk-litellm-hash-e5f6g7h8i9j0")
        resolver = ProxyKeyAttributionResolver(FakeKeyRepo([key]))
        attribution = await resolver.resolve("sk-litellm-hash-e5f6g7h8i9j0", None)
        assert attribution is not None
        assert attribution.proxy_key_id == key.id
        assert attribution.matched_by == "litellm_key_id"

    async def test_resolve_by_alias(self):
        key = make_key("bench-session-alpha")
        resolver = ProxyKeyAttributionResolver(FakeKeyRepo([key]))
        attribution = await resolver.resolve("unknown-hash", "bench-session-alpha")
        assert attribution is not None
        assert attribution.matched_by == "key_alias"

    async def test_resolve_by_ephemeral_virtual_key_mapping(self):
        key = make_key("mapped-alias")
        resolver = ProxyKeyAttributionResolver(
            FakeKeyRepo([key]), virtual_key_aliases={"hash-1": "mapped-alias"}
        )
        attribution = await resolver.resolve("hash-1", None)
        assert attribution is not None
        assert attribution.matched_by == "virtual_key_mapping"

    async def test_unresolved_and_cached(self):
        repo = FakeKeyRepo([])
        resolver = ProxyKeyAttributionResolver(repo)
        assert await resolver.resolve("hash-x", "alias-x") is None
        calls = repo.calls
        assert await resolver.resolve("hash-x", "alias-x") is None
        assert repo.calls == calls

    def test_apply_unresolved_attribution_marks_partial(self, normalizer):
        result = normalizer.normalize(load_fixture("successful_request"))
        apply_key_attribution(result, None)
        row = result.usage_request
        assert row is not None
        assert row.proxy_key_id is None
        assert row.key_alias is None
        assert row.request_metadata["litellm_key_alias"] == "bench-session-alpha"
        assert row.request_metadata["key_attribution"] == "unresolved"
        assert result.diagnostics.outcome == "partial"
        assert "proxy_key_id" in result.diagnostics.missing_fields

    def test_fingerprint_is_not_reversible_value(self):
        fingerprint = key_fingerprint("sk-secret-value")
        assert fingerprint.startswith("sha256:")
        assert "sk-secret-value" not in fingerprint


def spend_logs_transport(
    records: Any, status_code: int = 200, captured: list[httpx.Request] | None = None
) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        if captured is not None:
            captured.append(request)
        return httpx.Response(status_code, json=records)

    return httpx.MockTransport(handler)


WINDOW_START = datetime(2025, 4, 21, 10, 0, tzinfo=UTC)
WINDOW_END = datetime(2025, 4, 21, 11, 0, tzinfo=UTC)


class TestLiteLLMUsageCollector:
    async def test_fetches_all_keys_without_session(self):
        captured: list[httpx.Request] = []
        collector = LiteLLMUsageCollector(
            "http://litellm:4000/",
            "master-key",
            transport=spend_logs_transport(all_fixtures(), captured=captured),
        )
        result = await collector.collect(WINDOW_START, WINDOW_END, dry_run=True)

        request = captured[0]
        assert request.url.path == "/spend/logs"
        assert request.url.params["summarize"] == "false"
        assert request.url.params["start_date"] == "2025-04-21"
        assert request.url.params["end_date"] == "2025-04-22"
        assert "session_id" not in request.url.params
        assert request.headers["authorization"] == "Bearer master-key"
        assert len(result.usage_requests) == len(all_fixtures())
        assert result.report.dry_run is True
        assert result.report.written_count == 0

    async def test_collects_and_writes_idempotently(self, db_session):
        db_session.add(make_key("bench-session-alpha"))
        db_session.commit()
        repo = SQLUsageRequestRepository(db_session)
        missing_id = load_fixture("successful_request")
        del missing_id["request_id"], missing_id["call_id"]
        records = [*all_fixtures(), missing_id]

        def build() -> LiteLLMUsageCollector:
            return LiteLLMUsageCollector(
                "http://litellm:4000",
                "master-key",
                repository=repo,
                key_resolver=ProxyKeyAttributionResolver(SQLProxyKeyRepository(db_session)),
                transport=spend_logs_transport(records),
            )

        first = await build().collect(WINDOW_START, WINDOW_END)
        report = first.report
        assert report.total_rows == len(records)
        assert report.skipped_count == 1
        assert report.skip_reason_counts == {SKIP_MISSING_STABLE_ID: 1}
        assert report.written_count == len(records) - 1
        assert report.attributed_count == 1
        assert report.unattributed_count == len(records) - 2
        assert report.missing_field_counts["proxy_key_id"] == report.unattributed_count
        assert db_session.query(UsageRequestORM).count() == len(records) - 1

        stored = await repo.get_by_litellm_call_id("req-success-001")
        assert stored is not None
        assert stored.proxy_key_id is not None
        assert stored.request_metadata["key_attribution"] == "key_alias"
        assert stored.request_metadata["owner"] == "o"

        second = await build().collect(WINDOW_START, WINDOW_END)
        assert second.report.written_count == 0
        assert second.report.duplicate_count == len(records) - 1
        assert db_session.query(UsageRequestORM).count() == len(records) - 1

    async def test_out_of_window_rows_are_counted_not_collected(self):
        collector = LiteLLMUsageCollector(
            "http://litellm:4000", "k", transport=spend_logs_transport(all_fixtures())
        )
        result = await collector.collect(
            WINDOW_START, datetime(2025, 4, 21, 10, 10, tzinfo=UTC), dry_run=True
        )
        assert {row.litellm_call_id for row in result.usage_requests} == {
            "req-success-001",
            "req-failed-001",
        }
        assert result.report.out_of_window_count == len(all_fixtures()) - 2

    async def test_links_known_benchmark_session(self, db_session):
        experiment = Experiment(name="exp")
        variant = Variant(
            name="var", provider="openai", model_alias="gpt-4o", harness_profile="default"
        )
        task_card = TaskCard(name="task", goal="g", starting_prompt="s", stop_condition="c")
        db_session.add_all([experiment, variant, task_card])
        db_session.flush()
        session = SessionORM(
            experiment_id=experiment.id,
            variant_id=variant.id,
            task_card_id=task_card.id,
            harness_profile="default",
            repo_path="/tmp/repo",
            git_branch="main",
            git_commit="abc1234",
            status="active",
        )
        db_session.add(session)
        db_session.commit()

        known = load_fixture("sparse_request")
        known["metadata"] = {"benchmark_session_id": str(session.id)}
        unknown = load_fixture("fallback_to_call_id")
        unknown["metadata"] = {"benchmark_session_id": str(uuid4())}

        collector = LiteLLMUsageCollector(
            "http://litellm:4000",
            "k",
            repository=SQLUsageRequestRepository(db_session),
            session_lookup=SQLSessionRepository(db_session),
            transport=spend_logs_transport([known, unknown]),
        )
        result = await collector.collect(WINDOW_START, WINDOW_END)

        by_id = {row.litellm_call_id: row for row in result.usage_requests}
        assert by_id["req-sparse-001"].benchmark_session_id == session.id
        assert by_id["call-fallback-001"].benchmark_session_id is None
        assert isinstance(by_id["call-fallback-001"].request_metadata["benchmark_session_id"], str)
        assert result.report.session_linked_count == 1

    @pytest.mark.parametrize(
        ("status_code", "category"), [(401, "auth_error"), (500, "http_error")]
    )
    async def test_http_errors_are_categorized(self, status_code, category):
        collector = LiteLLMUsageCollector(
            "http://litellm:4000",
            "k",
            transport=spend_logs_transport({"error": "nope"}, status_code=status_code),
        )
        result = await collector.collect(WINDOW_START, WINDOW_END)
        assert result.usage_requests == []
        assert result.report.errors[0]["category"] == category

    async def test_connection_error_is_categorized(self):
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("refused", request=request)

        collector = LiteLLMUsageCollector(
            "http://litellm:4000", "k", transport=httpx.MockTransport(handler)
        )
        result = await collector.collect(WINDOW_START, WINDOW_END)
        assert result.report.errors[0]["category"] == "connection_error"

    async def test_wrapped_and_invalid_payloads(self):
        wrapped = LiteLLMUsageCollector(
            "http://litellm:4000",
            "k",
            transport=spend_logs_transport({"data": [load_fixture("sparse_request")]}),
        )
        assert len((await wrapped.collect(WINDOW_START, WINDOW_END)).usage_requests) == 1

        invalid = LiteLLMUsageCollector(
            "http://litellm:4000", "k", transport=spend_logs_transport({"spend": 1.0})
        )
        result = await invalid.collect(WINDOW_START, WINDOW_END)
        assert result.report.errors[0]["category"] == "invalid_response"

    async def test_rejects_empty_window(self):
        collector = LiteLLMUsageCollector("http://litellm:4000", "k")
        with pytest.raises(ValueError):
            await collector.collect(WINDOW_END, WINDOW_START)


class TestUsageReconciliationReport:
    async def test_report_lists_actionable_field_names(self):
        missing_id = load_fixture("successful_request")
        del missing_id["request_id"], missing_id["call_id"]
        collector = LiteLLMUsageCollector(
            "http://litellm:4000",
            "k",
            key_resolver=ProxyKeyAttributionResolver(FakeKeyRepo([])),
            transport=spend_logs_transport([load_fixture("sparse_request"), missing_id]),
        )
        result = await collector.collect(WINDOW_START, WINDOW_END, dry_run=True)
        report = result.report

        markdown = report.to_markdown()
        assert "missing_stable_request_id" in markdown
        assert "endTime" in markdown
        assert "spend" in markdown
        assert "proxy_key_id" in markdown
        assert "sk-litellm-hash-e5f6g7h8i9j0" not in markdown
        assert key_fingerprint("sk-litellm-hash-e5f6g7h8i9j0") in report.unattributed_keys

        payload = report.to_dict()
        json.dumps(payload)
        assert payload["summary"]["accepted_count"] == 1
        assert payload["summary"]["skipped_count"] == 1
        assert {row["outcome"] for row in payload["rows"]} == {"partial", "skipped"}

    def test_report_caps_row_diagnostics(self):
        report = UsageReconciliationReport()
        normalizer = UsageRequestNormalizer()
        for index in range(150):
            report.record_row(normalizer.normalize({"model": "m"}, row_index=index).diagnostics)
        assert report.skipped_count == 150
        assert len(report.rows) == 100
