"""Prometheus metric collection and rollups."""

from typing import Any
from uuid import UUID

import httpx

from benchmark_core.models import MetricRollup
from collectors.metric_catalog import MetricCatalog


class PrometheusCollector:
    """Collector for Prometheus metrics.

    Queries Prometheus for LLM inference metrics and computes derived rollups
    including latency percentiles, throughput, error rates, and cache metrics.
    """

    def __init__(
        self,
        base_url: str,
        session_id: UUID,
    ) -> None:
        self._base_url = base_url
        self._session_id = session_id
        self._catalog = MetricCatalog()

    async def query_range(
        self,
        query: str,
        start: str,
        end: str,
        step: str = "1m",
    ) -> dict[str, Any]:
        """Query Prometheus range data.

        Args:
            query: PromQL query string
            start: Start time (RFC3339 or Unix timestamp)
            end: End time (RFC3339 or Unix timestamp)
            step: Query resolution step width

        Returns:
            Parsed JSON response from Prometheus API

        Raises:
            httpx.HTTPStatusError: If the API returns an error status
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
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

    async def query_instant(
        self,
        query: str,
        time: str | None = None,
    ) -> dict[str, Any]:
        """Query Prometheus instant data at a specific time.

        Args:
            query: PromQL query string
            time: Evaluation timestamp (optional, defaults to now)

        Returns:
            Parsed JSON response from Prometheus API
        """
        params: dict[str, str] = {"query": query}
        if time:
            params["time"] = time

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self._base_url}/api/v1/query",
                params=params,
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

        Queries Prometheus for LLM metrics and computes derived rollups for:
        - Latency statistics (median, p95, p99)
        - Throughput (requests per minute)
        - Error rates
        - Cache hit rates

        Args:
            start: Start time (RFC3339 or Unix timestamp)
            end: End time (RFC3339 or Unix timestamp)

        Returns:
            List of computed MetricRollup objects
        """
        rollups: list[MetricRollup] = []
        session_id_str = str(self._session_id)

        # Collect latency metrics using histogram quantiles
        latency_queries = self._catalog.get_latency_queries(session_id_str)

        for metric_name, query in latency_queries.items():
            try:
                result = await self.query_range(query, start, end, step="1m")
                values = self._extract_values_from_matrix(result)

                if values:
                    rollup = self._catalog.compute_rollup(
                        dimension_type="session",
                        dimension_id=session_id_str,
                        metric_name=metric_name,
                        values=values,
                    )
                    if rollup:
                        rollups.append(rollup)
            except httpx.HTTPStatusError:
                # Empty windows should not corrupt aggregates
                # Skip metrics that fail to query
                continue

        # Collect throughput metrics
        throughput_query = self._catalog.get_throughput_query(session_id_str)
        try:
            result = await self.query_range(throughput_query, start, end, step="1m")
            values = self._extract_rate_values(result)
            if values:
                rollup = self._catalog.compute_rollup(
                    dimension_type="session",
                    dimension_id=session_id_str,
                    metric_name="throughput_rpm",
                    values=values,
                )
                if rollup:
                    rollups.append(rollup)
        except httpx.HTTPStatusError:
            pass

        # Collect error metrics
        error_queries = self._catalog.get_error_queries(session_id_str)
        for metric_name, query in error_queries.items():
            try:
                result = await self.query_range(query, start, end, step="1m")
                values = self._extract_rate_values(result)
                if values:
                    rollup = self._catalog.compute_rollup(
                        dimension_type="session",
                        dimension_id=session_id_str,
                        metric_name=metric_name,
                        values=values,
                    )
                    if rollup:
                        rollups.append(rollup)
            except httpx.HTTPStatusError:
                pass

        # Collect cache metrics
        cache_queries = self._catalog.get_cache_queries(session_id_str)
        for metric_name, query in cache_queries.items():
            try:
                result = await self.query_range(query, start, end, step="1m")
                values = self._extract_rate_values(result)
                if values:
                    rollup = self._catalog.compute_rollup(
                        dimension_type="session",
                        dimension_id=session_id_str,
                        metric_name=metric_name,
                        values=values,
                    )
                    if rollup:
                        rollups.append(rollup)
            except httpx.HTTPStatusError:
                pass

        return rollups

    def _extract_values_from_matrix(
        self,
        result: dict[str, Any],
    ) -> list[float]:
        """Extract float values from a matrix query result.

        Handles the matrix result format from range queries.
        Returns empty list for empty results without corrupting aggregates.
        """
        values: list[float] = []

        if result.get("status") != "success":
            return values

        data = result.get("data", {})
        result_type = data.get("resultType", "")
        result_data = data.get("result", [])

        if result_type != "matrix" or not result_data:
            return values

        for series in result_data:
            series_values = series.get("values", [])
            for _, value_str in series_values:
                try:
                    values.append(float(value_str))
                except (ValueError, TypeError):
                    # Skip non-numeric values
                    continue

        return values

    def _extract_rate_values(
        self,
        result: dict[str, Any],
    ) -> list[float]:
        """Extract rate values from a matrix query result.

        Similar to _extract_values_from_matrix but optimized for rate queries.
        """
        return self._extract_values_from_matrix(result)
