"""Request normalizer job for LiteLLM request data.

Maps raw LiteLLM fields into canonical requests with session correlation
and generates reconciliation reports for unmapped rows.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from benchmark_core.db.models import Request as RequestORM
from benchmark_core.repositories.request_repository import SQLRequestRepository


@dataclass
class UnmappedRowDiagnostics:
    """Diagnostics for a single unmapped row."""

    raw_data: dict[str, Any] = field(repr=False)
    reason: str = ""
    missing_fields: list[str] = field(default_factory=list)
    error_message: str = ""
    row_index: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert diagnostics to dictionary."""
        return {
            "reason": self.reason,
            "missing_fields": self.missing_fields,
            "error_message": self.error_message,
            "row_index": self.row_index,
            "raw_keys": list(self.raw_data.keys()) if self.raw_data else [],
        }


@dataclass
class ReconciliationReport:
    """Reconciliation report for unmapped rows with actionable diagnostics."""

    total_rows: int = 0
    mapped_count: int = 0
    unmapped_count: int = 0
    missing_field_counts: dict[str, int] = field(default_factory=dict)
    error_counts: dict[str, int] = field(default_factory=dict)
    unmapped_diagnostics: list[UnmappedRowDiagnostics] = field(default_factory=list)

    def add_mapped(self) -> None:
        """Record a successfully mapped row."""
        self.total_rows += 1
        self.mapped_count += 1

    def add_unmapped(
        self,
        raw_data: dict[str, Any],
        reason: str,
        missing_fields: list[str] | None = None,
        error_message: str = "",
        row_index: int | None = None,
    ) -> None:
        """Record an unmapped row with diagnostics."""
        self.total_rows += 1
        self.unmapped_count += 1

        # Track missing field counts
        if missing_fields:
            for field_name in missing_fields:
                self.missing_field_counts[field_name] = (
                    self.missing_field_counts.get(field_name, 0) + 1
                )

        # Track error counts by category
        if error_message:
            error_category = self._categorize_error(error_message)
            self.error_counts[error_category] = (
                self.error_counts.get(error_category, 0) + 1
            )

        # Store detailed diagnostics (limit to first 100 for memory efficiency)
        if len(self.unmapped_diagnostics) < 100:
            self.unmapped_diagnostics.append(
                UnmappedRowDiagnostics(
                    raw_data=raw_data,
                    reason=reason,
                    missing_fields=missing_fields or [],
                    error_message=error_message,
                    row_index=row_index,
                )
            )

    def _categorize_error(self, error_message: str) -> str:
        """Categorize an error message into a broad category.

        Uses specific keyword matching to avoid misclassification.
        Order matters - more specific patterns are checked first.
        """
        error_lower = error_message.lower()

        # Timestamp-related errors (check first as it's specific)
        if "timestamp" in error_lower:
            return "timestamp_parse_error"
        if "time" in error_lower and "parse" in error_lower:
            return "timestamp_parse_error"

        # HTTP/API errors
        if "http" in error_lower or "status" in error_lower:
            return "http_error"

        # JSON/parsing errors
        if "json" in error_lower or "invalid" in error_lower or "parse" in error_lower:
            return "parse_error"

        # Database/connection errors
        if "database" in error_lower or "connection" in error_lower or "timeout" in error_lower:
            return "database_error"

        # Repository/bulk insert failures
        if "repository" in error_lower or "bulk insert" in error_lower:
            return "repository_error"

        # ID-related errors (less specific, check later)
        if "request_id" in error_lower:
            return "id_error"

        return "other_error"

    @property
    def success_rate(self) -> float:
        """Calculate the success rate as a percentage."""
        if self.total_rows == 0:
            return 0.0
        return (self.mapped_count / self.total_rows) * 100.0

    def to_markdown(self) -> str:
        """Generate a markdown formatted report."""
        lines = [
            "# Request Normalization Reconciliation Report",
            "",
            "## Summary",
            "",
            f"- **Total Rows**: {self.total_rows}",
            f"- **Mapped**: {self.mapped_count} ({self.success_rate:.1f}%)",
            f"- **Unmapped**: {self.unmapped_count} ({100 - self.success_rate:.1f}%)",
            "",
        ]

        if self.missing_field_counts:
            lines.extend([
                "## Missing Field Counts",
                "",
                "| Field | Count |",
                "|-------|-------|",
            ])
            for field, count in sorted(
                self.missing_field_counts.items(), key=lambda x: x[1], reverse=True
            ):
                lines.append(f"| {field} | {count} |")
            lines.append("")

        if self.error_counts:
            lines.extend([
                "## Error Categories",
                "",
                "| Category | Count |",
                "|----------|-------|",
            ])
            for category, count in sorted(
                self.error_counts.items(), key=lambda x: x[1], reverse=True
            ):
                lines.append(f"| {category} | {count} |")
            lines.append("")

        if self.unmapped_diagnostics:
            lines.extend([
                "## Sample Unmapped Rows (First 10)",
                "",
            ])
            for i, diag in enumerate(self.unmapped_diagnostics[:10]):
                lines.extend([
                    f"### Row {diag.row_index or i + 1}",
                    "",
                    f"- **Reason**: {diag.reason}",
                ])
                if diag.missing_fields:
                    lines.append(f"- **Missing Fields**: {', '.join(diag.missing_fields)}")
                if diag.error_message:
                    lines.append(f"- **Error**: {diag.error_message}")
                if diag.raw_data:
                    lines.append(f"- **Available Keys**: {', '.join(diag.raw_data.keys())}")
                lines.append("")

        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """Generate a dictionary report suitable for JSON serialization."""
        return {
            "summary": {
                "total_rows": self.total_rows,
                "mapped_count": self.mapped_count,
                "unmapped_count": self.unmapped_count,
                "success_rate_percent": round(self.success_rate, 2),
            },
            "missing_field_counts": self.missing_field_counts,
            "error_counts": self.error_counts,
            "unmapped_rows": [
                diag.to_dict() for diag in self.unmapped_diagnostics[:50]
            ],
        }


class RequestNormalizer:
    """Normalizes raw LiteLLM request data into canonical Request ORM entities."""

    # Canonical correlation keys to preserve from raw data
    CORRELATION_KEYS = [
        "session_id",
        "experiment_id",
        "variant_id",
        "task_card_id",
        "harness_profile",
        "trace_id",
        "span_id",
        "parent_span_id",
    ]

    def __init__(self, session_id: UUID) -> None:
        """Initialize the normalizer with a session ID.

        Args:
            session_id: The benchmark session ID for correlation
        """
        self._session_id = session_id

    def normalize(
        self,
        raw_data: dict[str, Any],
        row_index: int | None = None,
    ) -> tuple[RequestORM | None, UnmappedRowDiagnostics | None]:
        """Normalize a single raw LiteLLM request into canonical form.

        Args:
            raw_data: Raw request data from LiteLLM API
            row_index: Optional row index for diagnostics

        Returns:
            Tuple of (normalized Request ORM, or None if failed,
                     UnmappedRowDiagnostics if failed, None if success)
        """
        if not isinstance(raw_data, dict):
            return None, UnmappedRowDiagnostics(
                raw_data=raw_data if isinstance(raw_data, dict) else {},
                reason="Invalid data type - expected dict",
                row_index=row_index,
            )

        missing_fields: list[str] = []

        # Extract request_id (required)
        request_id = raw_data.get("request_id") or raw_data.get("id")
        if not request_id:
            missing_fields.append("request_id")

        # Extract timestamp (required)
        timestamp_str = (
            raw_data.get("startTime")
            or raw_data.get("timestamp")
            or raw_data.get("created_at")
        )
        if not timestamp_str:
            missing_fields.append("timestamp")

        # If required fields are missing, return early
        if missing_fields:
            return None, UnmappedRowDiagnostics(
                raw_data=raw_data,
                reason="Missing required fields",
                missing_fields=missing_fields,
                row_index=row_index,
            )

        # Parse timestamp
        try:
            if isinstance(timestamp_str, (int, float)):
                timestamp = datetime.fromtimestamp(timestamp_str, tz=UTC)
            elif isinstance(timestamp_str, str):
                timestamp = datetime.fromisoformat(
                    timestamp_str.replace("Z", "+00:00")
                )
            else:
                return None, UnmappedRowDiagnostics(
                    raw_data=raw_data,
                    reason="Invalid timestamp type",
                    missing_fields=["timestamp"],
                    error_message=f"Unexpected timestamp type: {type(timestamp_str)}",
                    row_index=row_index,
                )
        except (ValueError, TypeError) as e:
            return None, UnmappedRowDiagnostics(
                raw_data=raw_data,
                reason="Failed to parse timestamp",
                missing_fields=["timestamp"],
                error_message=str(e),
                row_index=row_index,
            )

        # Extract provider and model
        provider = raw_data.get("user") or raw_data.get("customer_identifier") or "unknown"
        model = raw_data.get("model") or raw_data.get("model_id") or "unknown"

        # Extract latency metrics
        latency_ms = self._extract_latency(raw_data)
        ttft_ms = self._extract_ttft(raw_data)

        # Extract token counts
        tokens_prompt, tokens_completion = self._extract_tokens(raw_data)

        # Check for error status
        error, error_message = self._extract_error(raw_data)

        # Check cache hit
        cache_hit = self._extract_cache_hit(raw_data)

        # Collect metadata including session correlation keys
        metadata = self._build_metadata(raw_data)

        # Create the normalized Request ORM entity
        request = RequestORM(
            request_id=str(request_id),
            session_id=self._session_id,
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
            request_metadata=metadata,
        )

        return request, None

    def _extract_latency(self, raw_data: dict[str, Any]) -> float | None:
        """Extract latency in milliseconds from raw data."""
        if "latency" in raw_data:
            try:
                return float(raw_data["latency"]) * 1000  # Convert seconds to ms
            except (ValueError, TypeError):
                pass
        if "total_latency" in raw_data:
            try:
                return float(raw_data["total_latency"])
            except (ValueError, TypeError):
                pass
        if "duration" in raw_data:
            try:
                return float(raw_data["duration"])
            except (ValueError, TypeError):
                pass
        return None

    def _extract_ttft(self, raw_data: dict[str, Any]) -> float | None:
        """Extract time to first token in milliseconds from raw data."""
        if "ttft" in raw_data:
            try:
                return float(raw_data["ttft"])
            except (ValueError, TypeError):
                pass
        if "time_to_first_token" in raw_data:
            try:
                return float(raw_data["time_to_first_token"])
            except (ValueError, TypeError):
                pass
        return None

    def _extract_tokens(
        self, raw_data: dict[str, Any]
    ) -> tuple[int | None, int | None]:
        """Extract prompt and completion token counts from raw data."""
        tokens_prompt = None
        tokens_completion = None

        # Try nested usage object first
        if "usage" in raw_data and isinstance(raw_data["usage"], dict):
            usage = raw_data["usage"]
            tokens_prompt = usage.get("prompt_tokens") or usage.get("input_tokens")
            tokens_completion = usage.get("completion_tokens") or usage.get("output_tokens")
        else:
            # Try top-level keys
            tokens_prompt = raw_data.get("prompt_tokens") or raw_data.get("input_tokens")
            tokens_completion = raw_data.get("completion_tokens") or raw_data.get("output_tokens")

        # Convert to int if present
        if tokens_prompt is not None:
            try:
                tokens_prompt = int(tokens_prompt)
            except (ValueError, TypeError):
                tokens_prompt = None
        if tokens_completion is not None:
            try:
                tokens_completion = int(tokens_completion)
            except (ValueError, TypeError):
                tokens_completion = None

        return tokens_prompt, tokens_completion

    def _extract_error(self, raw_data: dict[str, Any]) -> tuple[bool, str | None]:
        """Extract error status and message from raw data."""
        error = False
        error_message = None

        if "error" in raw_data:
            error = bool(raw_data["error"])
            if isinstance(raw_data["error"], str):
                error_message = raw_data["error"]
            elif isinstance(raw_data["error"], dict):
                error_message = raw_data["error"].get("message", "Unknown error")

        # Also check for error in response object
        if not error and "response" in raw_data:
            response = raw_data["response"]
            if isinstance(response, dict) and "error" in response:
                error = True
                error_message = str(response["error"])

        return error, error_message

    def _extract_cache_hit(self, raw_data: dict[str, Any]) -> bool | None:
        """Extract cache hit status from raw data."""
        if "cache_hit" in raw_data:
            return bool(raw_data["cache_hit"])
        if "cached" in raw_data:
            return bool(raw_data["cached"])
        return None

    def _build_metadata(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """Build metadata dictionary with correlation keys from raw data."""
        metadata: dict[str, Any] = {}

        # Check both top-level and nested metadata for correlation keys
        raw_metadata = raw_data.get("metadata", {})
        if not isinstance(raw_metadata, dict):
            raw_metadata = {}

        for key in self.CORRELATION_KEYS:
            if key in raw_data:
                metadata[key] = raw_data[key]
            elif key in raw_metadata:
                metadata[key] = raw_metadata[key]

        # Store raw data keys for debugging
        metadata["litellm_raw_keys"] = list(raw_data.keys())

        return metadata


class RequestNormalizerJob:
    """Idempotent normalization job for LiteLLM requests.

    This job normalizes raw LiteLLM request data into canonical Request
    entities and writes them to the database with idempotent semantics.
    Generates a reconciliation report for unmapped rows.
    """

    def __init__(
        self,
        repository: SQLRequestRepository,
        session_id: UUID,
    ) -> None:
        """Initialize the normalization job.

        Args:
            repository: Repository for writing normalized requests
            session_id: Benchmark session ID for correlation
        """
        self._repository = repository
        self._session_id = session_id
        self._normalizer = RequestNormalizer(session_id)

    async def run(
        self,
        raw_requests: list[dict[str, Any]],
    ) -> tuple[list[RequestORM], ReconciliationReport]:
        """Run normalization job for a batch of raw requests.

        This job is idempotent - re-running with the same data
        produces the same results without duplicates.

        Args:
            raw_requests: List of raw request data from LiteLLM API

        Returns:
            Tuple of (list of normalized Request ORMs written,
                     ReconciliationReport with diagnostics)
        """
        report = ReconciliationReport()
        requests_to_ingest: list[RequestORM] = []

        # Normalize each raw request
        for i, raw in enumerate(raw_requests):
            normalized, diagnostics = self._normalizer.normalize(raw, row_index=i)

            if normalized is not None:
                requests_to_ingest.append(normalized)
                report.add_mapped()
            else:
                report.add_unmapped(
                    raw_data=raw,
                    reason=diagnostics.reason if diagnostics else "Unknown error",
                    missing_fields=diagnostics.missing_fields if diagnostics else [],
                    error_message=diagnostics.error_message if diagnostics else "",
                    row_index=i,
                )

        # Bulk insert with idempotency handling
        if requests_to_ingest:
            try:
                written = await self._repository.create_many(requests_to_ingest)
                return written, report
            except Exception as e:
                # If bulk insert fails, mark all as unmapped
                for req in requests_to_ingest:
                    report.add_unmapped(
                        raw_data={"request_id": req.request_id},
                        reason="Repository bulk insert failed",
                        error_message=str(e),
                    )
                return [], report

        return [], report

    async def run_with_validation(
        self,
        raw_requests: list[dict[str, Any]],
        validate_session: bool = True,
    ) -> tuple[list[RequestORM], ReconciliationReport]:
        """Run normalization job with optional session validation.

        Args:
            raw_requests: List of raw request data from LiteLLM API
            validate_session: Whether to validate session exists before writing

        Returns:
            Tuple of (list of normalized Request ORMs written,
                     ReconciliationReport with diagnostics)
        """
        # For now, delegate to run() - session validation can be added
        # when session repository integration is needed
        return await self.run(raw_requests)
