"""Normalization jobs for ingesting raw proxy records."""

from typing import Any

from benchmark_core.models import Request
from benchmark_core.repositories import RequestRepository


class NormalizationJob:
    """Idempotent normalization job for LiteLLM requests."""

    def __init__(self, repository: RequestRepository) -> None:
        self._repository = repository

    async def run(
        self,
        session_id: str,
        raw_requests: list[dict[str, Any]],
    ) -> list[Request]:
        """Run normalization job for a batch of raw requests.

        This job is idempotent - re-running with the same data
        produces the same results without duplicates.
        """
        requests = []
        for raw in raw_requests:
            request = self._normalize(raw)
            if request:
                requests.append(request)

        # Bulk insert with idempotency handling
        return await self._repository.create_many(requests)

    def _normalize(self, raw: dict[str, Any]) -> Request | None:
        """Normalize a single raw request."""
        # Placeholder: actual implementation
        return None
