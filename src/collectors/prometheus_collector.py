"""Prometheus metric collection and rollups."""

from typing import Any

import httpx

from benchmark_core.models import MetricRollup


class PrometheusCollector:
    """Collector for Prometheus metrics."""

    def __init__(
        self,
        base_url: str,
        session_id: str,
    ) -> None:
        self._base_url = base_url
        self._session_id = session_id

    async def query_range(
        self,
        query: str,
        start: str,
        end: str,
        step: str = "1m",
    ) -> dict[str, Any]:
        """Query Prometheus range data."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self._base_url}/api/v1/query_range",
                params={
                    "query": query,
                    "start": start,
                    "end": end,
                    "step": step,
                },
            )
            response.raise_for_status()
            data: dict[str, Any] = response.json()
            return data

    async def collect_session_metrics(
        self,
        start: str,
        end: str,
    ) -> list[MetricRollup]:
        """Collect metrics for a session time window.

        Returns derived rollups for latency, throughput, errors, and cache.
        """
        # Placeholder: actual implementation will query and compute rollups
        return []
