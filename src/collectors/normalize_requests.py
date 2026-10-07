"""Request normalizer job for LiteLLM request data.

Maps raw LiteLLM fields into canonical requests with session correlation
and generates reconciliation reports for unmapped rows.
"""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from benchmark_core.db.models import Request as RequestORM
from benchmark_core.db.models import UsageRequest as UsageRequestORM
from benchmark_core.repositories.request_repository import SQLRequestRepository
from benchmark_core.security import RedactionFilter
from collectors.extraction import (
    extract_cache_fields,
    extract_cost_usd,
    extract_error_fields,
    extract_finished_at,
    extract_latency_ms,
    extract_record_metadata,
    extract_started_at,
    extract_token_counts,
    extract_ttft_ms,
    first_present,
    parse_bool,
    parse_json_list,
    parse_json_object,
)
from collectors.key_attribution import KeyAttribution


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
            self.error_counts[error_category] = self.error_counts.get(error_category, 0) + 1

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
            lines.extend(
                [
                    "## Missing Field Counts",
                    "",
                    "| Field | Count |",
                    "|-------|-------|",
                ]
            )
            for field, count in sorted(
                self.missing_field_counts.items(), key=lambda x: x[1], reverse=True
            ):
                lines.append(f"| {field} | {count} |")
            lines.append("")

        if self.error_counts:
            lines.extend(
                [
                    "## Error Categories",
                    "",
                    "| Category | Count |",
                    "|----------|-------|",
                ]
            )
            for category, count in sorted(
                self.error_counts.items(), key=lambda x: x[1], reverse=True
            ):
                lines.append(f"| {category} | {count} |")
            lines.append("")

        if self.unmapped_diagnostics:
            lines.extend(
                [
                    "## Sample Unmapped Rows (First 10)",
                    "",
                ]
            )
            for i, diag in enumerate(self.unmapped_diagnostics[:10]):
                lines.extend(
                    [
                        f"### Row {diag.row_index or i + 1}",
                        "",
                        f"- **Reason**: {diag.reason}",
                    ]
                )
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
            "unmapped_rows": [diag.to_dict() for diag in self.unmapped_diagnostics[:50]],
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
            raw_data.get("startTime") or raw_data.get("timestamp") or raw_data.get("created_at")
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
                timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
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

    def _extract_tokens(self, raw_data: dict[str, Any]) -> tuple[int | None, int | None]:
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
                # Database/repository failures are distinct from data quality issues.
                # Data quality issues were already tracked during normalization above.
                # Here we just need to report the infrastructure failure.
                # Re-raise to let caller handle (e.g., transaction rollback, alerting)
                raise RuntimeError(
                    f"Bulk insert failed after normalizing {len(requests_to_ingest)} requests: {e}"
                ) from e

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


# =============================================================================
# Sessionless usage normalization (usage_requests)
# =============================================================================

USAGE_OUTCOME_MAPPED = "mapped"
USAGE_OUTCOME_PARTIAL = "partial"
USAGE_OUTCOME_SKIPPED = "skipped"

SKIP_MISSING_STABLE_ID = "missing_stable_request_id"
SKIP_INVALID_RECORD = "invalid_record_type"

# Canonical join field -> accepted source keys, in priority order. The
# ``benchmark_*`` names are the tags written by the session credential service.
USAGE_SESSION_JOIN_FIELDS: dict[str, tuple[str, ...]] = {
    "benchmark_session_id": ("benchmark_session_id", "session_id"),
    "experiment_id": ("benchmark_experiment_id", "experiment_id", "experiment"),
    "variant_id": ("benchmark_variant_id", "variant_id", "variant"),
    "task_card_id": ("benchmark_task_card_id", "task_card_id", "task_card"),
    "harness_profile": ("benchmark_harness_profile", "harness_profile", "harness"),
}
USAGE_TRACE_FIELDS = ("trace_id", "span_id", "parent_span_id")
MAX_METADATA_STRING_LENGTH = 255
MAX_REQUEST_TAGS = 50
MAX_ERROR_MESSAGE_LENGTH = 2000
MAX_USAGE_ROW_DIAGNOSTICS = 100


@dataclass
class UsageRowDiagnostics:
    """Per-row normalization diagnostics for usage collection.

    ``missing_fields`` uses LiteLLM source field names so operators can map
    gaps directly to proxy configuration or the spend-log field inventory.
    """

    row_index: int | None = None
    litellm_call_id: str | None = None
    outcome: str = USAGE_OUTCOME_MAPPED
    reason: str = ""
    missing_fields: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    raw_keys: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert diagnostics to a JSON-serializable dictionary."""
        return {
            "row_index": self.row_index,
            "litellm_call_id": self.litellm_call_id,
            "outcome": self.outcome,
            "reason": self.reason,
            "missing_fields": list(self.missing_fields),
            "notes": list(self.notes),
            "raw_keys": list(self.raw_keys),
        }


@dataclass
class UsageNormalizationResult:
    """Outcome of normalizing one raw spend-log record.

    ``key_reference`` is the LiteLLM key reference used only for registry
    lookup; it is never written to ``usage_requests``.
    """

    usage_request: UsageRequestORM | None
    diagnostics: UsageRowDiagnostics
    key_reference: str | None = field(default=None, repr=False)
    reported_key_alias: str | None = None
    benchmark_session_candidate: UUID | None = None


@dataclass
class UsageReconciliationReport:
    """Reconciliation report for all-key usage collection."""

    dry_run: bool = False
    total_rows: int = 0
    mapped_count: int = 0
    partial_count: int = 0
    skipped_count: int = 0
    out_of_window_count: int = 0
    attributed_count: int = 0
    unattributed_count: int = 0
    session_linked_count: int = 0
    written_count: int = 0
    duplicate_count: int = 0
    missing_field_counts: dict[str, int] = field(default_factory=dict)
    skip_reason_counts: dict[str, int] = field(default_factory=dict)
    unattributed_keys: dict[str, int] = field(default_factory=dict)
    errors: list[dict[str, str]] = field(default_factory=list)
    rows: list[UsageRowDiagnostics] = field(default_factory=list)

    @property
    def accepted_count(self) -> int:
        """Rows accepted for persistence (fully or partially mapped)."""
        return self.mapped_count + self.partial_count

    def record_row(self, diagnostics: UsageRowDiagnostics) -> None:
        """Record the final outcome of one in-window row."""
        self.total_rows += 1
        if diagnostics.outcome == USAGE_OUTCOME_SKIPPED:
            self.skipped_count += 1
            reason = diagnostics.reason or "unknown"
            self.skip_reason_counts[reason] = self.skip_reason_counts.get(reason, 0) + 1
        elif diagnostics.outcome == USAGE_OUTCOME_PARTIAL:
            self.partial_count += 1
        else:
            self.mapped_count += 1
        for name in diagnostics.missing_fields:
            self.missing_field_counts[name] = self.missing_field_counts.get(name, 0) + 1
        if diagnostics.outcome != USAGE_OUTCOME_MAPPED and len(self.rows) < (
            MAX_USAGE_ROW_DIAGNOSTICS
        ):
            self.rows.append(diagnostics)

    def record_unattributed(self, key_label: str) -> None:
        """Record a row whose key could not be resolved in ``proxy_keys``."""
        self.unattributed_count += 1
        self.unattributed_keys[key_label] = self.unattributed_keys.get(key_label, 0) + 1

    def add_error(self, category: str, message: str) -> None:
        """Record a collection-level error (fetch, response, repository)."""
        self.errors.append({"category": category, "message": message})

    def to_dict(self) -> dict[str, Any]:
        """Generate a JSON-serializable report."""
        return {
            "summary": {
                "dry_run": self.dry_run,
                "total_rows": self.total_rows,
                "accepted_count": self.accepted_count,
                "mapped_count": self.mapped_count,
                "partial_count": self.partial_count,
                "skipped_count": self.skipped_count,
                "out_of_window_count": self.out_of_window_count,
                "attributed_count": self.attributed_count,
                "unattributed_count": self.unattributed_count,
                "session_linked_count": self.session_linked_count,
                "written_count": self.written_count,
                "duplicate_count": self.duplicate_count,
            },
            "missing_field_counts": dict(self.missing_field_counts),
            "skip_reason_counts": dict(self.skip_reason_counts),
            "unattributed_keys": dict(self.unattributed_keys),
            "errors": list(self.errors),
            "rows": [row.to_dict() for row in self.rows],
        }

    def to_markdown(self) -> str:
        """Generate a markdown report."""
        lines = [
            "# Usage Collection Reconciliation Report",
            "",
            "## Summary",
            "",
            f"- **Dry run**: {self.dry_run}",
            f"- **Total rows**: {self.total_rows}",
            f"- **Mapped**: {self.mapped_count}",
            f"- **Partially mapped**: {self.partial_count}",
            f"- **Skipped**: {self.skipped_count}",
            f"- **Outside window**: {self.out_of_window_count}",
            f"- **Attributed to proxy_keys**: {self.attributed_count}",
            f"- **Unattributed**: {self.unattributed_count}",
            f"- **Linked to benchmark session**: {self.session_linked_count}",
            f"- **Written**: {self.written_count}",
            f"- **Duplicates skipped**: {self.duplicate_count}",
            "",
        ]
        sections: list[tuple[str, str, dict[str, int]]] = [
            ("Missing Source Fields", "Field", self.missing_field_counts),
            ("Skip Reasons", "Reason", self.skip_reason_counts),
            ("Unattributed Keys", "Key", self.unattributed_keys),
        ]
        for title, column, counts in sections:
            if not counts:
                continue
            lines.extend([f"## {title}", "", f"| {column} | Count |", "|---|---|"])
            for name, count in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
                lines.append(f"| {name} | {count} |")
            lines.append("")
        if self.errors:
            lines.extend(["## Errors", ""])
            lines.extend(f"- `{error['category']}`: {error['message']}" for error in self.errors)
            lines.append("")
        if self.rows:
            lines.extend(["## Rows Needing Attention (first 10)", ""])
            for row in self.rows[:10]:
                label = row.litellm_call_id or f"row {row.row_index}"
                lines.append(f"### {label} ({row.outcome})")
                lines.append("")
                if row.reason:
                    lines.append(f"- **Reason**: {row.reason}")
                if row.missing_fields:
                    lines.append(f"- **Missing fields**: {', '.join(row.missing_fields)}")
                for note in row.notes:
                    lines.append(f"- **Note**: {note}")
                lines.append("")
        return "\n".join(lines)


def apply_key_attribution(
    result: UsageNormalizationResult,
    attribution: KeyAttribution | None,
) -> None:
    """Apply registry attribution to a normalized usage row (ADR-002).

    On a registry match the stable ``proxy_key_id`` and registry alias/ID are
    written and owner/team/customer are denormalized into metadata. Without a
    match, ``proxy_key_id`` and ``key_alias`` stay null; the LiteLLM-reported
    alias (non-secret) is kept in metadata for retroactive matching.
    """
    usage = result.usage_request
    if usage is None:
        return
    metadata = dict(usage.request_metadata or {})
    if attribution is not None:
        usage.proxy_key_id = attribution.proxy_key_id
        usage.key_alias = attribution.key_alias
        usage.litellm_key_id = attribution.litellm_key_id
        metadata["key_attribution"] = attribution.matched_by
        for name in ("owner", "team", "customer"):
            value = getattr(attribution, name)
            if value is not None:
                metadata[name] = value
    else:
        usage.proxy_key_id = None
        usage.key_alias = None
        usage.litellm_key_id = None
        metadata["key_attribution"] = "unresolved"
        if result.reported_key_alias:
            metadata["litellm_key_alias"] = result.reported_key_alias
        if "proxy_key_id" not in result.diagnostics.missing_fields:
            result.diagnostics.missing_fields.append("proxy_key_id")
            result.diagnostics.notes.append(
                "key not found in proxy_keys registry; register the key alias to attribute usage"
            )
        if result.diagnostics.outcome == USAGE_OUTCOME_MAPPED:
            result.diagnostics.outcome = USAGE_OUTCOME_PARTIAL
    usage.request_metadata = metadata


class UsageRequestNormalizer:
    """Normalize raw LiteLLM spend-log records into ``usage_requests`` rows.

    No benchmark session is required. Optional session join fields are
    preserved when present. Only allowlisted, redacted metadata is stored;
    prompt/response content and raw key references are never copied.
    """

    def __init__(self, redaction_filter: RedactionFilter | None = None) -> None:
        self._redaction = redaction_filter or RedactionFilter()

    def normalize(
        self,
        raw_data: Any,
        row_index: int | None = None,
    ) -> UsageNormalizationResult:
        """Normalize one raw spend-log record.

        Args:
            raw_data: Raw record from LiteLLM ``/spend/logs``.
            row_index: Position of the record in the fetched batch.

        Returns:
            Result with the ORM row (None when skipped) and diagnostics.
        """
        if not isinstance(raw_data, dict):
            return UsageNormalizationResult(
                usage_request=None,
                diagnostics=UsageRowDiagnostics(
                    row_index=row_index,
                    outcome=USAGE_OUTCOME_SKIPPED,
                    reason=SKIP_INVALID_RECORD,
                    notes=[f"expected JSON object, got {type(raw_data).__name__}"],
                ),
            )

        diagnostics = UsageRowDiagnostics(row_index=row_index, raw_keys=sorted(raw_data.keys()))
        litellm_call_id = first_present(raw_data, "request_id", "call_id", "litellm_call_id")
        if litellm_call_id is None:
            diagnostics.outcome = USAGE_OUTCOME_SKIPPED
            diagnostics.reason = SKIP_MISSING_STABLE_ID
            diagnostics.missing_fields = ["request_id", "call_id"]
            return UsageNormalizationResult(usage_request=None, diagnostics=diagnostics)
        diagnostics.litellm_call_id = str(litellm_call_id)

        record_metadata = extract_record_metadata(raw_data)
        started_at = extract_started_at(raw_data)
        finished_at = extract_finished_at(raw_data)
        tokens = extract_token_counts(raw_data)
        cache = extract_cache_fields(raw_data)
        errors = extract_error_fields(raw_data)
        cost_usd = extract_cost_usd(raw_data)
        latency_ms = extract_latency_ms(raw_data)
        ttft_ms = extract_ttft_ms(raw_data)
        stream = parse_bool(raw_data.get("stream"))

        resolved_model = first_present(raw_data, "model", "model_id")
        requested_model = first_present(raw_data, "requested_model", "model_group")
        provider_route = first_present(raw_data, "custom_llm_provider")
        provider = first_present(raw_data, "provider") or provider_route
        if provider is None and isinstance(resolved_model, str) and "/" in resolved_model:
            provider = resolved_model.split("/", 1)[0]

        key_reference = first_present(raw_data, "api_key") or first_present(
            record_metadata, "user_api_key_hash", "user_api_key"
        )
        reported_alias = first_present(raw_data, "api_key_alias", "key_alias") or first_present(
            record_metadata, "user_api_key_alias"
        )

        join_fields, session_candidate = self._extract_join_fields(
            raw_data, record_metadata, diagnostics
        )
        request_metadata = self._build_metadata(raw_data, record_metadata, join_fields, stream)

        error_message = errors.error_message
        if error_message is not None:
            error_message = self._redaction.redact_string(error_message)[:MAX_ERROR_MESSAGE_LENGTH]

        cache_hit = cache.cache_hit
        if cache_hit is None and cache.cached_input_tokens:
            cache_hit = True

        request_id = first_present(raw_data, "request_id")
        usage = UsageRequestORM(
            id=uuid.uuid4(),
            litellm_call_id=str(litellm_call_id),
            request_id=str(request_id) if request_id is not None else None,
            key_alias=str(reported_alias) if reported_alias is not None else None,
            litellm_key_id=None,
            proxy_key_id=None,
            benchmark_session_id=None,
            provider=str(provider) if provider is not None else None,
            provider_route=str(provider_route) if provider_route is not None else None,
            requested_model=str(requested_model) if requested_model is not None else None,
            resolved_model=str(resolved_model) if resolved_model is not None else None,
            route=self._optional_str(first_present(raw_data, "call_type", "route")),
            started_at=started_at,
            finished_at=finished_at,
            latency_ms=latency_ms,
            ttft_ms=ttft_ms,
            input_tokens=tokens.input_tokens,
            output_tokens=tokens.output_tokens,
            cached_input_tokens=cache.cached_input_tokens,
            cache_write_tokens=cache.cache_write_tokens,
            cost_usd=cost_usd,
            status=errors.status,
            error_code=errors.error_code,
            error_message=error_message,
            cache_hit=cache_hit,
            request_metadata=request_metadata,
            created_at=datetime.now(UTC),
        )

        missing = diagnostics.missing_fields
        if started_at is None:
            missing.append("startTime")
        if finished_at is None:
            missing.append("endTime")
        if resolved_model is None:
            missing.append("model")
        if provider is None:
            missing.append("provider")
        if tokens.input_tokens is None:
            missing.append("prompt_tokens")
        if tokens.output_tokens is None:
            missing.append("completion_tokens")
        if cost_usd is None:
            missing.append("spend")
        if latency_ms is None:
            missing.append("latency")
        if stream and ttft_ms is None:
            missing.append("ttft")
        if errors.is_error and errors.error_code is None:
            missing.append("error_code")
        if key_reference is None and reported_alias is None:
            missing.append("api_key")
        elif reported_alias is None:
            missing.append("api_key_alias")
        diagnostics.outcome = USAGE_OUTCOME_PARTIAL if missing else USAGE_OUTCOME_MAPPED

        return UsageNormalizationResult(
            usage_request=usage,
            diagnostics=diagnostics,
            key_reference=str(key_reference) if key_reference is not None else None,
            reported_key_alias=str(reported_alias) if reported_alias is not None else None,
            benchmark_session_candidate=session_candidate,
        )

    @staticmethod
    def _optional_str(value: Any) -> str | None:
        return str(value) if value is not None else None

    def _metadata_sources(
        self, raw_data: dict[str, Any], record_metadata: dict[str, Any]
    ) -> list[dict[str, Any]]:
        sources = [
            parse_json_object(record_metadata.get("spend_logs_metadata")),
            parse_json_object(record_metadata.get("requester_metadata")),
            record_metadata,
            self._parse_request_tags(raw_data),
        ]
        # Top-level ``session_id`` on LiteLLM spend logs is LiteLLM's own
        # trace session, not a benchmark session, so it is not a join source.
        top_level = {key: value for key, value in raw_data.items() if key != "session_id"}
        sources.append(top_level)
        return sources

    @staticmethod
    def _parse_request_tags(raw_data: dict[str, Any]) -> dict[str, Any]:
        parsed: dict[str, Any] = {}
        for tag in parse_json_list(raw_data.get("request_tags")):
            if not isinstance(tag, str):
                continue
            for separator in (":", "="):
                if separator in tag:
                    key, value = tag.split(separator, 1)
                    parsed.setdefault(key.strip(), value.strip())
                    break
        return parsed

    def _extract_join_fields(
        self,
        raw_data: dict[str, Any],
        record_metadata: dict[str, Any],
        diagnostics: UsageRowDiagnostics,
    ) -> tuple[dict[str, Any], UUID | None]:
        sources = self._metadata_sources(raw_data, record_metadata)
        join_fields: dict[str, Any] = {}
        for canonical, aliases in USAGE_SESSION_JOIN_FIELDS.items():
            for source in sources:
                value = first_present(source, *aliases)
                sanitized = self._sanitize_scalar(value)
                if sanitized is not None:
                    join_fields[canonical] = sanitized
                    break
        for trace_field in USAGE_TRACE_FIELDS:
            for source in sources:
                sanitized = self._sanitize_scalar(source.get(trace_field))
                if sanitized is not None:
                    join_fields[trace_field] = sanitized
                    break

        session_candidate: UUID | None = None
        session_value = join_fields.get("benchmark_session_id")
        if session_value is not None:
            try:
                session_candidate = UUID(str(session_value))
            except ValueError:
                diagnostics.notes.append(
                    "benchmark_session_id is not a UUID; preserved in request_metadata only"
                )
        return join_fields, session_candidate

    def _build_metadata(
        self,
        raw_data: dict[str, Any],
        record_metadata: dict[str, Any],
        join_fields: dict[str, Any],
        stream: bool | None,
    ) -> dict[str, Any]:
        metadata: dict[str, Any] = dict(join_fields)
        if stream is not None:
            metadata["stream"] = stream
        for target, source_key in (
            ("end_user", "end_user"),
            ("team_id", "team_id"),
            ("litellm_session_id", "session_id"),
            ("cache_key", "cache_key"),
        ):
            sanitized = self._sanitize_scalar(raw_data.get(source_key))
            if sanitized is not None and sanitized != "":
                metadata[target] = sanitized
        for target, source_key in (
            ("team_alias", "user_api_key_team_alias"),
            ("litellm_overhead_time_ms", "litellm_overhead_time_ms"),
            ("attempted_retries", "attempted_retries"),
            ("attempted_fallbacks", "attempted_fallbacks"),
        ):
            sanitized = self._sanitize_scalar(record_metadata.get(source_key))
            if sanitized is not None:
                metadata[target] = sanitized
        tags = [
            self._sanitize_scalar(tag)
            for tag in parse_json_list(raw_data.get("request_tags"))[:MAX_REQUEST_TAGS]
            if isinstance(tag, str)
        ]
        if tags:
            metadata["request_tags"] = tags
        return metadata

    def _sanitize_scalar(self, value: Any) -> Any:
        """Return a redacted scalar suitable for metadata, or None."""
        if value is None:
            return None
        if isinstance(value, bool | int | float):
            return value
        if isinstance(value, str):
            if value == "":
                return None
            return self._redaction.redact_string(value)[:MAX_METADATA_STRING_LENGTH]
        if isinstance(value, UUID):
            return str(value)
        return None
