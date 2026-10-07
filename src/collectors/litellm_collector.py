"""LiteLLM request collection and normalization."""

import contextlib
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol
from uuid import UUID

import httpx

from benchmark_core.db.models import UsageRequest as UsageRequestORM
from benchmark_core.models import Request
from benchmark_core.repositories import RequestRepository
from benchmark_core.security import get_redaction_filter
from collectors.key_attribution import ProxyKeyAttributionResolver, key_fingerprint
from collectors.normalize_requests import (
    UsageNormalizationResult,
    UsageReconciliationReport,
    UsageRequestNormalizer,
    apply_key_attribution,
)


@dataclass
class CollectionDiagnostics:
    """Diagnostics for a collection run."""

    total_raw_records: int = 0
    normalized_count: int = 0
    skipped_count: int = 0
    missing_fields: dict[str, int] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    def record_missing_field(self, field_name: str) -> None:
        """Record a missing field occurrence."""
        self.missing_fields[field_name] = self.missing_fields.get(field_name, 0) + 1

    def add_error(self, message: str) -> None:
        """Add an error message."""
        self.errors.append(message)


@dataclass
class IngestWatermark:
    """Watermark for tracking ingest cursor position."""

    last_request_id: str | None = None
    last_timestamp: datetime | None = None
    record_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Serialize watermark to dictionary."""
        return {
            "last_request_id": self.last_request_id,
            "last_timestamp": self.last_timestamp.isoformat() if self.last_timestamp else None,
            "record_count": self.record_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "IngestWatermark":
        """Deserialize watermark from dictionary."""
        timestamp = None
        if data.get("last_timestamp"):
            with contextlib.suppress(ValueError):
                timestamp = datetime.fromisoformat(data["last_timestamp"])
        return cls(
            last_request_id=data.get("last_request_id"),
            last_timestamp=timestamp,
            record_count=data.get("record_count", 0),
        )


class LiteLLMCollector:
    """Collector for LiteLLM request data with idempotent ingest and watermark tracking."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        repository: RequestRepository,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._repository = repository

    async def collect_requests(
        self,
        session_id: UUID,
        start_time: str | None = None,
        end_time: str | None = None,
        watermark: IngestWatermark | None = None,
    ) -> tuple[list[Request], CollectionDiagnostics, IngestWatermark]:
        """Collect LiteLLM requests for a session.

        This method is idempotent - duplicate requests are handled
        by the repository layer using request_id uniqueness.

        Args:
            session_id: The benchmark session ID for correlation
            start_time: ISO format start time filter (optional)
            end_time: ISO format end time filter (optional)
            watermark: Optional watermark to resume from last position

        Returns:
            Tuple of (collected requests, diagnostics, new watermark)
        """
        diagnostics = CollectionDiagnostics()
        new_watermark = IngestWatermark()

        # Fetch raw requests from LiteLLM API
        raw_requests = await self._fetch_raw_requests(
            session_id=session_id,
            start_time=start_time,
            end_time=end_time,
            watermark=watermark,
            diagnostics=diagnostics,
        )

        diagnostics.total_raw_records = len(raw_requests)

        if not raw_requests:
            return [], diagnostics, new_watermark

        # Normalize and filter requests
        requests_to_ingest: list[Request] = []
        for raw in raw_requests:
            request = self.normalize_request(raw, session_id, diagnostics)
            if request:
                requests_to_ingest.append(request)
            else:
                diagnostics.skipped_count += 1

        diagnostics.normalized_count = len(requests_to_ingest)

        if not requests_to_ingest:
            return [], diagnostics, new_watermark

        # Idempotent bulk insert - repository handles duplicates
        try:
            ingested = await self._repository.create_many(requests_to_ingest)  # type: ignore[attr-defined]
        except Exception as e:
            diagnostics.add_error(f"Repository bulk insert failed: {e}")
            return [], diagnostics, new_watermark

        # Update watermark from last ingested record
        if ingested:
            last_record = ingested[-1]
            new_watermark = IngestWatermark(
                last_request_id=last_record.request_id,
                last_timestamp=last_record.timestamp,
                record_count=len(ingested),
            )

        return ingested, diagnostics, new_watermark

    async def _fetch_raw_requests(
        self,
        session_id: UUID,
        start_time: str | None,
        end_time: str | None,
        watermark: IngestWatermark | None,
        diagnostics: CollectionDiagnostics,
    ) -> list[dict[str, Any]]:
        """Fetch raw request records from LiteLLM API.

        Uses watermark to resume from last position for idempotent collection.
        """
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        # Build query parameters
        params: dict[str, str] = {}
        if start_time:
            params["start_time"] = start_time
        if end_time:
            params["end_time"] = end_time

        # Use watermark to avoid re-fetching already processed records
        # If both start_time and watermark are provided, use the later one
        if watermark and watermark.last_timestamp:
            watermark_start = watermark.last_timestamp.isoformat()
            if "start_time" not in params or watermark_start > params["start_time"]:
                params["start_time"] = watermark_start

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(
                    f"{self._base_url}/spend/logs",
                    headers=headers,
                    params=params,
                )
                response.raise_for_status()
                data = response.json()

                # LiteLLM spend logs endpoint returns list of log entries
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict) and "logs" in data:
                    return data["logs"]  # type: ignore[no-any-return]
                else:
                    diagnostics.add_error(f"Unexpected API response format: {type(data)}")
                    return []

        except httpx.HTTPStatusError as e:
            diagnostics.add_error(
                f"HTTP error fetching logs: {e.response.status_code} - {e.response.text}"
            )
            return []
        except httpx.RequestError as e:
            diagnostics.add_error(f"Request error fetching logs: {e}")
            return []
        except Exception as e:
            diagnostics.add_error(f"Unexpected error fetching logs: {e}")
            return []

    def normalize_request(
        self,
        raw_data: dict[str, Any],
        session_id: UUID,
        diagnostics: CollectionDiagnostics | None = None,
    ) -> Request | None:
        """Normalize raw LiteLLM request data into canonical Request model.

        Preserves session correlation keys when present in raw data.

        Args:
            raw_data: Raw request data from LiteLLM API
            session_id: Benchmark session ID for correlation
            diagnostics: Optional diagnostics collector for tracking missing fields

        Returns:
            Normalized Request model or None if normalization fails
        """
        if not isinstance(raw_data, dict):
            if diagnostics:
                diagnostics.add_error(f"Invalid raw data type: {type(raw_data)}")
            return None

        # Extract request_id (required)
        request_id = raw_data.get("request_id") or raw_data.get("id")
        if not request_id:
            if diagnostics:
                diagnostics.record_missing_field("request_id")
            return None

        # Extract timestamp (required)
        timestamp_str = (
            raw_data.get("startTime") or raw_data.get("timestamp") or raw_data.get("created_at")
        )
        if not timestamp_str:
            if diagnostics:
                diagnostics.record_missing_field("timestamp")
            return None

        try:
            # Handle various timestamp formats
            if isinstance(timestamp_str, (int, float)):
                timestamp = datetime.fromtimestamp(timestamp_str, tz=UTC)
            elif isinstance(timestamp_str, str):
                # Try ISO format
                timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            else:
                if diagnostics:
                    diagnostics.add_error(f"Unexpected timestamp type for request {request_id}")
                return None
        except (ValueError, TypeError) as e:
            if diagnostics:
                diagnostics.add_error(f"Failed to parse timestamp for request {request_id}: {e}")
            return None

        # Extract provider and model
        provider = raw_data.get("user") or raw_data.get("customer_identifier") or "unknown"
        model = raw_data.get("model") or raw_data.get("model_id") or "unknown"

        if provider == "unknown" and diagnostics:
            diagnostics.record_missing_field("provider")
        if model == "unknown" and diagnostics:
            diagnostics.record_missing_field("model")

        # Extract latency metrics
        latency_ms = None
        if "latency" in raw_data:
            latency_ms = float(raw_data["latency"]) * 1000  # Convert seconds to ms
        elif "total_latency" in raw_data:
            latency_ms = float(raw_data["total_latency"])
        elif "duration" in raw_data:
            latency_ms = float(raw_data["duration"])

        ttft_ms = None
        if "ttft" in raw_data:
            ttft_ms = float(raw_data["ttft"])
        elif "time_to_first_token" in raw_data:
            ttft_ms = float(raw_data["time_to_first_token"])

        # Extract token counts
        tokens_prompt = None
        tokens_completion = None

        if "usage" in raw_data and isinstance(raw_data["usage"], dict):
            usage = raw_data["usage"]
            tokens_prompt = usage.get("prompt_tokens") or usage.get("input_tokens")
            tokens_completion = usage.get("completion_tokens") or usage.get("output_tokens")
        else:
            tokens_prompt = raw_data.get("prompt_tokens") or raw_data.get("input_tokens")
            tokens_completion = raw_data.get("completion_tokens") or raw_data.get("output_tokens")

        # Check for error status
        error = False
        error_message = None
        if "error" in raw_data:
            error = bool(raw_data["error"])
            if isinstance(raw_data["error"], str):
                error_message = raw_data["error"]
            elif isinstance(raw_data["error"], dict):
                error_message = raw_data["error"].get("message", "Unknown error")

        # Check cache hit
        cache_hit = None
        if "cache_hit" in raw_data:
            cache_hit = bool(raw_data["cache_hit"])
        elif "cached" in raw_data:
            cache_hit = bool(raw_data["cached"])

        # Collect metadata including session correlation keys
        metadata: dict[str, Any] = {}

        # Preserve session correlation keys from raw data or nested metadata
        correlation_keys = [
            "session_id",
            "experiment_id",
            "variant_id",
            "task_card_id",
            "harness_profile",
            "trace_id",
            "span_id",
            "parent_span_id",
        ]
        # Check both top-level and nested metadata for correlation keys
        raw_metadata = raw_data.get("metadata", {})
        for key in correlation_keys:
            if key in raw_data:
                metadata[key] = raw_data[key]
            elif key in raw_metadata:
                metadata[key] = raw_metadata[key]

        # Store raw data reference for debugging
        metadata["litellm_raw_keys"] = list(raw_data.keys())

        return Request(
            request_id=str(request_id),
            session_id=session_id,
            provider=str(provider),
            model=str(model),
            timestamp=timestamp,
            latency_ms=latency_ms,
            ttft_ms=ttft_ms,
            tokens_prompt=tokens_prompt,
            tokens_completion=tokens_completion,
            error=error,
            error_message=error_message,
            cache_hit=cache_hit,
            metadata=metadata,
        )


# =============================================================================
# Sessionless all-key usage collection (usage_requests)
# =============================================================================


class UsageRequestWriter(Protocol):
    """Subset of the usage request repository used by the collector."""

    async def create_many(
        self, requests: list[UsageRequestORM]
    ) -> tuple[list[UsageRequestORM], int]: ...


class BenchmarkSessionLookup(Protocol):
    """Subset of the session repository used to validate join FKs."""

    async def exists(self, id: UUID) -> bool: ...


@dataclass
class UsageCollectionResult:
    """Result of a sessionless usage collection run."""

    usage_requests: list[UsageRequestORM]
    report: UsageReconciliationReport


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class LiteLLMUsageCollector:
    """Collect all-key LiteLLM spend logs into ``usage_requests``.

    Unlike :class:`LiteLLMCollector`, no benchmark session is required. Rows are
    fetched for a time window, normalized, attributed to the ``proxy_keys``
    registry when possible, linked to benchmark sessions when metadata carries
    a known session UUID, and written idempotently by ``litellm_call_id``.
    """

    SPEND_LOGS_PATH = "/spend/logs"
    MAX_ERROR_DETAIL_LENGTH = 200

    def __init__(
        self,
        base_url: str,
        api_key: str,
        repository: UsageRequestWriter | None = None,
        key_resolver: ProxyKeyAttributionResolver | None = None,
        session_lookup: BenchmarkSessionLookup | None = None,
        normalizer: UsageRequestNormalizer | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
        timeout: float = 60.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._repository = repository
        self._key_resolver = key_resolver
        self._session_lookup = session_lookup
        self._normalizer = normalizer or UsageRequestNormalizer()
        self._transport = transport
        self._timeout = timeout
        self._redaction = get_redaction_filter()
        self._session_exists: dict[UUID, bool] = {}

    async def collect(
        self,
        start_time: datetime,
        end_time: datetime,
        dry_run: bool = False,
    ) -> UsageCollectionResult:
        """Fetch, normalize, and (unless dry run) persist usage for a window.

        Args:
            start_time: Inclusive window start (naive values are treated as UTC).
            end_time: Exclusive window end (naive values are treated as UTC).
            dry_run: When True, nothing is written to the database.

        Returns:
            Normalized rows and the reconciliation report. Fetch failures are
            reported in ``report.errors`` with a category instead of raising.
        """
        start, end = _as_utc(start_time), _as_utc(end_time)
        if start >= end:
            raise ValueError("start_time must be earlier than end_time")
        report = UsageReconciliationReport(dry_run=dry_run)
        raw_records = await self.fetch_spend_logs(start, end, report)
        if raw_records is None:
            return UsageCollectionResult(usage_requests=[], report=report)
        usage_requests = await self.process_records(
            raw_records, report, start_time=start, end_time=end, dry_run=dry_run
        )
        return UsageCollectionResult(usage_requests=usage_requests, report=report)

    async def fetch_spend_logs(
        self,
        start_time: datetime,
        end_time: datetime,
        report: UsageReconciliationReport,
    ) -> list[Any] | None:
        """Fetch individual spend-log rows for all keys in a window.

        LiteLLM filters ``/spend/logs`` by calendar date, so the request spans
        every date touched by the window; rows are filtered precisely later.
        Returns None and records a categorized error on failure.
        """
        params = {
            "start_date": start_time.date().isoformat(),
            "end_date": (end_time.date() + timedelta(days=1)).isoformat(),
            "summarize": "false",
        }
        headers = {"Authorization": f"Bearer {self._api_key}"}
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout, transport=self._transport
            ) as client:
                response = await client.get(
                    f"{self._base_url}{self.SPEND_LOGS_PATH}", headers=headers, params=params
                )
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            category = "auth_error" if status in (401, 403) else "http_error"
            detail = self._redaction.redact_string(exc.response.text)[
                : self.MAX_ERROR_DETAIL_LENGTH
            ]
            report.add_error(category, f"GET {self.SPEND_LOGS_PATH} returned {status}: {detail}")
            return None
        except httpx.RequestError as exc:
            report.add_error(
                "connection_error",
                f"GET {self.SPEND_LOGS_PATH} failed: {type(exc).__name__}",
            )
            return None
        except ValueError:
            report.add_error("invalid_response", f"{self.SPEND_LOGS_PATH} returned non-JSON body")
            return None

        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            for key in ("data", "logs"):
                if isinstance(payload.get(key), list):
                    records: list[Any] = payload[key]
                    return records
        report.add_error(
            "invalid_response",
            f"{self.SPEND_LOGS_PATH} returned {type(payload).__name__}, expected a list of rows",
        )
        return None

    async def process_records(
        self,
        raw_records: list[Any],
        report: UsageReconciliationReport,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        dry_run: bool = False,
    ) -> list[UsageRequestORM]:
        """Normalize, attribute, and persist already-fetched raw records."""
        start = _as_utc(start_time) if start_time is not None else None
        end = _as_utc(end_time) if end_time is not None else None
        accepted: list[UsageRequestORM] = []
        seen_ids: set[str] = set()

        for index, raw in enumerate(raw_records):
            result = self._normalizer.normalize(raw, row_index=index)
            usage = result.usage_request
            if usage is not None and self._outside_window(usage.started_at, start, end):
                report.out_of_window_count += 1
                continue
            if usage is not None:
                await self._attribute(result, report)
                await self._link_session(result, report)
                if usage.litellm_call_id in seen_ids:
                    report.duplicate_count += 1
                    result.diagnostics.notes.append("duplicate litellm_call_id within batch")
                    continue
                seen_ids.add(usage.litellm_call_id)
                accepted.append(usage)
            report.record_row(result.diagnostics)

        if dry_run or self._repository is None or not accepted:
            return accepted
        try:
            created, skipped = await self._repository.create_many(accepted)
        except Exception as exc:
            report.add_error("repository_error", f"{type(exc).__name__}: {exc}")
            raise
        report.written_count = len(created)
        report.duplicate_count += skipped
        return created

    @staticmethod
    def _outside_window(
        started_at: datetime | None, start: datetime | None, end: datetime | None
    ) -> bool:
        if started_at is None:
            return False
        return (start is not None and started_at < start) or (end is not None and started_at >= end)

    async def _attribute(
        self, result: UsageNormalizationResult, report: UsageReconciliationReport
    ) -> None:
        if self._key_resolver is None:
            return
        attribution = await self._key_resolver.resolve(
            result.key_reference, result.reported_key_alias
        )
        apply_key_attribution(result, attribution)
        if attribution is not None:
            report.attributed_count += 1
        else:
            label = result.reported_key_alias or (
                key_fingerprint(result.key_reference) if result.key_reference else "<no key>"
            )
            report.record_unattributed(label)

    async def _link_session(
        self, result: UsageNormalizationResult, report: UsageReconciliationReport
    ) -> None:
        usage = result.usage_request
        candidate = result.benchmark_session_candidate
        if usage is None or candidate is None:
            return
        if self._session_lookup is not None:
            if candidate not in self._session_exists:
                self._session_exists[candidate] = await self._session_lookup.exists(candidate)
            if not self._session_exists[candidate]:
                result.diagnostics.notes.append(
                    "benchmark_session_id not found in sessions; preserved in request_metadata only"
                )
                return
        usage.benchmark_session_id = candidate
        report.session_linked_count += 1
