"""LiteLLM request collection and normalization."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import httpx

from benchmark_core.models import Request
from benchmark_core.repositories import RequestRepository


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
            try:
                timestamp = datetime.fromisoformat(data["last_timestamp"])
            except ValueError:
                pass
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
            ingested = await self._repository.create_many(requests_to_ingest)
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
        if watermark and watermark.last_timestamp:
            # Resume from watermark position
            params["start_time"] = watermark.last_timestamp.isoformat()

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
                    return data["logs"]
                else:
                    diagnostics.add_error(f"Unexpected API response format: {type(data)}")
                    return []

        except httpx.HTTPStatusError as e:
            diagnostics.add_error(f"HTTP error fetching logs: {e.response.status_code} - {e.response.text}")
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
        timestamp_str = raw_data.get("startTime") or raw_data.get("timestamp") or raw_data.get("created_at")
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

        # Preserve session correlation keys from raw data if present
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
        for key in correlation_keys:
            if key in raw_data:
                metadata[key] = raw_data[key]

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
