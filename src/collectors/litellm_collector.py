"""LiteLLM request collection and normalization."""

from typing import Any
from uuid import UUID

from benchmark_core.models import Request
from benchmark_core.repositories import RequestRepository


class LiteLLMCollector:
    """Collector for LiteLLM request data."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        repository: RequestRepository,
    ) -> None:
        self._base_url = base_url
        self._api_key = api_key
        self._repository = repository

    async def collect_requests(
        self,
        session_id: UUID,
        start_time: str | None = None,
        end_time: str | None = None,
    ) -> list[Request]:
        """Collect LiteLLM requests for a session.

        This method is idempotent - duplicate requests are handled
        by the repository layer.
        """
        # Placeholder: actual implementation will query LiteLLM API
        return []

    def normalize_request(self, raw_data: dict[str, Any]) -> Request | None:
        """Normalize raw LiteLLM request data into canonical Request model."""
        # Placeholder: actual implementation will extract and normalize fields
        return None
