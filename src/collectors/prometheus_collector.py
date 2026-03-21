"""Prometheus metrics collector for operational data."""
import structlog
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx

logger = structlog.get_logger()


class PrometheusCollector:
    """Collector for Prometheus metrics."""

    def __init__(self, prometheus_url: str):
        self.prometheus_url = prometheus_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=30.0)

    async def close(self) -> None:
        """Close HTTP client."""
        await self.client.aclose()

    async def query(self, query: str) -> Dict[str, Any]:
        """Execute instant query.

        Args:
            query: PromQL query string

        Returns:
            Query result dict
        """
        try:
            response = await self.client.get(
                f"{self.prometheus_url}/api/v1/query",
                params={"query": query},
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(
                "Prometheus query failed",
                query=query,
                error=str(e),
            )
            raise

    async def query_range(
        self,
        query: str,
        start: datetime,
        end: datetime,
        step: str = "15s",
    ) -> Dict[str, Any]:
        """Execute range query.

        Args:
            query: PromQL query string
            start: Start time
            end: End time
            step: Query step interval

        Returns:
            Query result dict
        """
        try:
            response = await self.client.get(
                f"{self.prometheus_url}/api/v1/query_range",
                params={
                    "query": query,
                    "start": start.timestamp(),
                    "end": end.timestamp(),
                    "step": step,
                },
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(
                "Prometheus range query failed",
                query=query,
                error=str(e),
            )
            raise

    async def collect_litellm_latency(
        self,
        window_seconds: int = 300,
    ) -> List[Dict[str, Any]]:
        """Collect LiteLLM latency metrics.

        Args:
            window_seconds: Time window to query

        Returns:
            List of latency metric records
        """
        end = datetime.utcnow()
        start = end - timedelta(seconds=window_seconds)

        # Query for latency histogram
        result = await self.query_range(
            'histogram_quantile(0.50, rate(litellm_request_duration_seconds_bucket[1m]))',
            start,
            end,
        )

        metrics = []
        if result.get("status") == "success":
            for item in result.get("data", {}).get("result", []):
                metrics.append({
                    "metric_name": "latency_p50_seconds",
                    "labels": item.get("metric", {}),
                    "values": item.get("values", []),
                })

        return metrics

    async def collect_request_counts(
        self,
        window_seconds: int = 300,
        tags: Optional[Dict[str, str]] = None,
    ) -> Dict[str, int]:
        """Collect request count metrics.

        Args:
            window_seconds: Time window to query
            tags: Optional tags to filter by

        Returns:
            Dict with request counts
        """
        end = datetime.utcnow()
        start = end - timedelta(seconds=window_seconds)

        # Build label filter
        label_filter = ""
        if tags:
            label_parts = [f'{k}="{v}"' for k, v in tags.items()]
            label_filter = "{" + ",".join(label_parts) + "}"

        # Query for total requests
        total_query = f'sum(increase(litellm_requests_total{label_filter}[{window_seconds}s]))'
        total_result = await self.query(total_query)

        total = 0.0
        if total_result.get("status") == "success":
            results = total_result.get("data", {}).get("result", [])
            if results:
                total = float(results[0].get("value", [None, 0])[1])

        # Query for error requests
        error_query = f'sum(increase(litellm_request_errors_total{label_filter}[{window_seconds}s]))'
        error_result = await self.query(error_query)

        errors = 0.0
        if error_result.get("status") == "success":
            results = error_result.get("data", {}).get("result", [])
            if results:
                errors = float(results[0].get("value", [None, 0])[1])

        return {
            "total_requests": int(total),
            "error_requests": int(errors),
            "success_requests": int(total - errors),
            "window_seconds": window_seconds,
        }

    async def collect_cache_metrics(
        self,
        window_seconds: int = 300,
    ) -> Dict[str, int]:
        """Collect cache hit/miss metrics.

        Args:
            window_seconds: Time window to query

        Returns:
            Dict with cache metrics
        """
        end = datetime.utcnow()
        start = end - timedelta(seconds=window_seconds)

        # Query for cache hits
        hits_query = f'sum(increase(litellm_cache_hits_total[{window_seconds}s]))'
        hits_result = await self.query(hits_query)

        hits = 0.0
        if hits_result.get("status") == "success":
            results = hits_result.get("data", {}).get("result", [])
            if results:
                hits = float(results[0].get("value", [None, 0])[1])

        # Query for total requests with potential caching
        total_query = f'sum(increase(litellm_requests_total[{window_seconds}s]))'
        total_result = await self.query(total_query)

        total = 0.0
        if total_result.get("status") == "success":
            results = total_result.get("data", {}).get("result", [])
            if results:
                total = float(results[0].get("value", [None, 0])[1])

        return {
            "cache_hits": int(hits),
            "total_requests": int(total),
            "cache_hit_ratio": hits / total if total > 0 else 0.0,
            "window_seconds": window_seconds,
        }

    async def collect_summary(
        self,
        window_seconds: int = 300,
        tags: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Collect comprehensive metrics summary.

        Args:
            window_seconds: Time window to query
            tags: Optional tags to filter by

        Returns:
            Dict with all collected metrics
        """
        try:
            request_counts = await self.collect_request_counts(window_seconds, tags)
            cache_metrics = await self.collect_cache_metrics(window_seconds)

            return {
                "requests": request_counts,
                "cache": cache_metrics,
                "window_seconds": window_seconds,
            }
        except httpx.HTTPError as e:
            logger.error(
                "Failed to collect Prometheus summary",
                error=str(e),
            )
            # Return empty window handling
            return {
                "requests": {
                    "total_requests": 0,
                    "error_requests": 0,
                    "success_requests": 0,
                },
                "cache": {
                    "cache_hits": 0,
                    "total_requests": 0,
                    "cache_hit_ratio": 0.0,
                },
                "window_seconds": window_seconds,
                "error": str(e),
            }
