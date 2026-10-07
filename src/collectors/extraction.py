"""Shared field-extraction helpers for LiteLLM spend-log records.

These helpers are pure functions over raw LiteLLM records so that benchmark
request normalization and sessionless usage normalization interpret latency,
TTFT, tokens, cache, cost, and error fields identically.

Unit conventions follow docs/data-model-and-observability.md:
``latency``/``total_latency``/``ttft``/``time_to_first_token`` are seconds,
``request_duration_ms`` is milliseconds, and all outputs are milliseconds.
"""

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

STARTED_AT_FIELDS = ("startTime", "start_time", "timestamp", "created_at")
FINISHED_AT_FIELDS = ("endTime", "end_time")
COMPLETION_START_FIELDS = ("completion_start_time", "completionStartTime")
LATENCY_SECONDS_FIELDS = ("latency", "total_latency")
TTFT_SECONDS_FIELDS = ("ttft", "time_to_first_token")
SUCCESS_STATUSES = frozenset({"success", "succeeded", "ok"})
FAILURE_STATUSES = frozenset({"failure", "failed", "error"})


@dataclass(frozen=True)
class TokenCounts:
    """Token counts extracted from a raw record."""

    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None


@dataclass(frozen=True)
class CacheFields:
    """Cache counters extracted from a raw record."""

    cache_hit: bool | None
    cached_input_tokens: int | None
    cache_write_tokens: int | None


@dataclass(frozen=True)
class ErrorFields:
    """Status and error details extracted from a raw record."""

    status: str
    error_code: str | None
    error_message: str | None

    @property
    def is_error(self) -> bool:
        """Whether the record represents a failed request."""
        return self.status in FAILURE_STATUSES


def first_present(data: dict[str, Any], *keys: str) -> Any:
    """Return the first value that is present and not None or empty string."""
    for key in keys:
        value = data.get(key)
        if value is not None and value != "":
            return value
    return None


def to_int(value: Any) -> int | None:
    """Coerce a value to int, returning None when not numeric."""
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def to_float(value: Any) -> float | None:
    """Coerce a value to float, returning None when not numeric."""
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_bool(value: Any) -> bool | None:
    """Parse LiteLLM boolean values, which may be serialized as strings."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes"}:
            return True
        if lowered in {"false", "0", "no", "none", ""}:
            return False
    return None


def parse_timestamp(value: Any) -> datetime | None:
    """Parse ISO-8601 strings, epoch numbers, or datetimes into aware UTC datetimes."""
    if value is None or value == "":
        return None
    parsed: datetime | None = None
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        try:
            parsed = datetime.fromtimestamp(value, tz=UTC)
        except (OverflowError, OSError, ValueError):
            return None
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def parse_json_object(value: Any) -> dict[str, Any]:
    """Return a dict from a dict or JSON-encoded string, else an empty dict."""
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip().startswith("{"):
        try:
            decoded = json.loads(value)
        except ValueError:
            return {}
        return decoded if isinstance(decoded, dict) else {}
    return {}


def parse_json_list(value: Any) -> list[Any]:
    """Return a list from a list or JSON-encoded string, else an empty list."""
    if isinstance(value, list):
        return value
    if isinstance(value, str) and value.strip().startswith("["):
        try:
            decoded = json.loads(value)
        except ValueError:
            return []
        return decoded if isinstance(decoded, list) else []
    return []


def extract_record_metadata(raw: dict[str, Any]) -> dict[str, Any]:
    """Return the record's ``metadata`` object (LiteLLM may JSON-encode it)."""
    return parse_json_object(raw.get("metadata"))


def extract_started_at(raw: dict[str, Any]) -> datetime | None:
    """Extract the request start timestamp."""
    return parse_timestamp(first_present(raw, *STARTED_AT_FIELDS))


def extract_finished_at(raw: dict[str, Any]) -> datetime | None:
    """Extract the request end timestamp."""
    return parse_timestamp(first_present(raw, *FINISHED_AT_FIELDS))


def _elapsed_ms(start: datetime | None, end: datetime | None) -> float | None:
    if start is None or end is None or end < start:
        return None
    return round((end - start).total_seconds() * 1000, 3)


def extract_latency_ms(raw: dict[str, Any]) -> float | None:
    """Extract total latency in milliseconds.

    Prefers explicit seconds fields, then ``request_duration_ms``, then the
    ``endTime - startTime`` difference.
    """
    seconds = to_float(first_present(raw, *LATENCY_SECONDS_FIELDS))
    if seconds is not None:
        return round(seconds * 1000, 3)
    duration_ms = to_float(raw.get("request_duration_ms"))
    if duration_ms is not None:
        return duration_ms
    return _elapsed_ms(extract_started_at(raw), extract_finished_at(raw))


def extract_ttft_ms(raw: dict[str, Any]) -> float | None:
    """Extract time-to-first-token in milliseconds.

    Uses ``ttft``/``time_to_first_token`` (seconds) when present; otherwise
    derives ``round((completion_start_time - startTime) * 1000)``.
    """
    seconds = to_float(first_present(raw, *TTFT_SECONDS_FIELDS))
    if seconds is not None:
        return round(seconds * 1000, 3)
    started_at = extract_started_at(raw)
    completion_start = parse_timestamp(first_present(raw, *COMPLETION_START_FIELDS))
    elapsed = _elapsed_ms(started_at, completion_start)
    return float(round(elapsed)) if elapsed is not None else None


def extract_token_counts(raw: dict[str, Any]) -> TokenCounts:
    """Extract input/output/total token counts from top-level or ``usage`` fields."""
    usage = parse_json_object(raw.get("usage"))
    sources = (raw, usage)

    def _first_int(*keys: str) -> int | None:
        for source in sources:
            value = to_int(first_present(source, *keys))
            if value is not None:
                return value
        return None

    input_tokens = _first_int("prompt_tokens", "input_tokens")
    output_tokens = _first_int("completion_tokens", "output_tokens")
    total_tokens = _first_int("total_tokens")
    if total_tokens is None and input_tokens is not None and output_tokens is not None:
        total_tokens = input_tokens + output_tokens
    return TokenCounts(input_tokens, output_tokens, total_tokens)


def extract_cache_fields(raw: dict[str, Any]) -> CacheFields:
    """Extract cache hit flag and cache token counters.

    Falls back to ``metadata.additional_usage_values`` (LiteLLM provider usage)
    and ``usage.prompt_tokens_details.cached_tokens``.
    """
    metadata = extract_record_metadata(raw)
    additional = parse_json_object(metadata.get("additional_usage_values"))
    usage = parse_json_object(raw.get("usage"))
    prompt_details = parse_json_object(usage.get("prompt_tokens_details"))

    cached_input_tokens = to_int(raw.get("cached_input_tokens"))
    if cached_input_tokens is None:
        cached_input_tokens = to_int(
            first_present(additional, "cache_read_input_tokens", "cached_tokens")
        )
    if cached_input_tokens is None:
        cached_input_tokens = to_int(prompt_details.get("cached_tokens"))

    cache_write_tokens = to_int(raw.get("cache_write_tokens"))
    if cache_write_tokens is None:
        cache_write_tokens = to_int(additional.get("cache_creation_input_tokens"))

    cache_hit = parse_bool(first_present(raw, "cache_hit", "cached"))
    return CacheFields(cache_hit, cached_input_tokens, cache_write_tokens)


def extract_cost_usd(raw: dict[str, Any]) -> float | None:
    """Extract request spend in USD."""
    return to_float(first_present(raw, "spend", "cost", "response_cost"))


def _error_message(value: Any) -> str | None:
    if value is None or value == "" or value is False:
        return None
    if isinstance(value, dict):
        message = first_present(value, "error_message", "message", "error")
        return str(message) if message is not None else None
    if value is True:
        return None
    return str(value)


def extract_error_fields(raw: dict[str, Any]) -> ErrorFields:
    """Extract normalized status, error code, and error message.

    Reads top-level ``status``/``error``/``error_code`` and falls back to
    LiteLLM's ``metadata.status`` and ``metadata.error_information``.
    """
    metadata = extract_record_metadata(raw)
    error_info = parse_json_object(metadata.get("error_information"))
    raw_error = raw.get("error")

    error_message = _error_message(raw_error) or _error_message(error_info)
    if error_message is None:
        response = parse_json_object(raw.get("response"))
        error_message = _error_message(response.get("error"))

    error_code_value = first_present(raw, "error_code")
    if error_code_value is None and isinstance(raw_error, dict):
        error_code_value = first_present(raw_error, "code", "status_code")
    if error_code_value is None:
        error_code_value = first_present(error_info, "error_code", "status_code")
    error_code = str(error_code_value) if error_code_value is not None else None

    status_value = first_present(raw, "status") or first_present(metadata, "status")
    status = str(status_value).strip().lower() if status_value is not None else ""
    if not status:
        has_error = error_message is not None or error_code is not None or raw_error is True
        status = "failure" if has_error else "success"
    return ErrorFields(status=status, error_code=error_code, error_message=error_message)
