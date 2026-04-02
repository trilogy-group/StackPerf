"""Normalization jobs for ingesting raw proxy records."""

from typing import Any
from uuid import UUID

from benchmark_core.models import Request
from benchmark_core.repositories import RequestRepository
from benchmark_core.security import (
    DEFAULT_CONTENT_CAPTURE_CONFIG,
    ContentCaptureConfig,
    RedactionFilter,
    should_capture_content,
)


class NormalizationJob:
    """Idempotent normalization job for LiteLLM requests.

    Enforces security controls:
    - Content capture is disabled by default (prompts, responses, tool payloads)
    - Secrets are redacted from metadata fields
    - Only correlation keys and metrics are preserved
    """

    def __init__(
        self,
        repository: RequestRepository,
        content_capture: ContentCaptureConfig | None = None,
        redaction_filter: RedactionFilter | None = None,
    ) -> None:
        """Initialize normalization job.

        Args:
            repository: Repository for persisting normalized requests.
            content_capture: Content capture configuration. Defaults to disabled.
            redaction_filter: Filter for redacting secrets. Defaults to enabled.
        """
        self._repository = repository
        self._content_capture = content_capture or DEFAULT_CONTENT_CAPTURE_CONFIG
        self._redaction_filter = redaction_filter or RedactionFilter()

    async def run(
        self,
        session_id: UUID,
        raw_requests: list[dict[str, Any]],
    ) -> list[Request]:
        """Run normalization job for a batch of raw requests.

        This job is idempotent - re-running with the same data
        produces the same results without duplicates.

        Security guarantees:
        - Prompts and responses are NOT captured by default
        - Secrets in metadata are redacted
        - Only safe metadata (correlation keys, metrics) are preserved
        """
        requests = []
        for raw in raw_requests:
            request = self._normalize(raw, session_id)
            if request:
                requests.append(request)

        # Bulk insert with idempotency handling
        return await self._repository.create_many(requests)  # type: ignore[no-any-return]

    def _normalize(self, raw: dict[str, Any], session_id: UUID) -> Request | None:
        """Normalize a single raw request.

        Enforces content capture defaults and secret redaction.
        """
        # Placeholder: actual implementation would:
        # 1. Extract correlation keys (session_id, experiment_id, etc.)
        # 2. Extract metrics (latency, tokens, cache hits)
        # 3. Skip prompt/response content unless explicitly enabled
        # 4. Redact secrets from any captured metadata
        # 5. Return normalized Request model
        return None

    def _should_capture_content(self, content_type: str) -> bool:
        """Check if content should be captured.

        Args:
            content_type: Type of content (prompt, response, tool_payload).

        Returns:
            True if content should be captured per policy.
        """
        return should_capture_content(content_type, self._content_capture)  # type: ignore[no-any-return]

    def _redact_metadata(self, metadata: dict[str, Any]) -> dict[str, Any]:
        """Redact secrets from metadata before storage.

        Args:
            metadata: Raw metadata dictionary.

        Returns:
            Metadata with secrets redacted.
        """
        return self._redaction_filter.redact_dict(metadata)  # type: ignore[no-any-return]
