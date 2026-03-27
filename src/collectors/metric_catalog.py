"""Rollup metric catalog defining Prometheus queries and computation logic."""

from benchmark_core.models import MetricRollup


class MetricCatalog:
    """Catalog of rollup metric definitions and PromQL queries.

    Provides standardized metric definitions for:
    - Latency percentiles (median, p95, p99)
    - Throughput rates
    - Error rates
    - Cache hit rates

    The catalog generates PromQL queries filtered by session_id and
    handles computation of derived statistics from raw metric values.
    """

    # Prometheus metric names for LiteLLM
    LATENCY_HISTOGRAM = "litellm_request_latency_seconds_bucket"
    THROUGHPUT_COUNTER = "litellm_requests_total"
    ERROR_COUNTER = "litellm_request_errors_total"
    CACHE_COUNTER = "litellm_cache_hit_total"

    def get_latency_queries(self, session_id: str) -> dict[str, str]:
        """Get PromQL queries for latency percentiles.

        Args:
            session_id: Session identifier for filtering metrics

        Returns:
            Dictionary mapping metric names to PromQL query strings
        """
        base_filter = f'session_id="{session_id}"'

        return {
            "latency_median_ms": f"""
                histogram_quantile(0.5,
                    sum(rate({self.LATENCY_HISTOGRAM}{{{base_filter}}}[5m])) by (le)
                ) * 1000
            """.strip(),
            "latency_p95_ms": f"""
                histogram_quantile(0.95,
                    sum(rate({self.LATENCY_HISTOGRAM}{{{base_filter}}}[5m])) by (le)
                ) * 1000
            """.strip(),
            "latency_p99_ms": f"""
                histogram_quantile(0.99,
                    sum(rate({self.LATENCY_HISTOGRAM}{{{base_filter}}}[5m])) by (le)
                ) * 1000
            """.strip(),
        }

    def get_throughput_query(self, session_id: str) -> str:
        """Get PromQL query for throughput rate.

        Args:
            session_id: Session identifier for filtering metrics

        Returns:
            PromQL query string for requests per minute
        """
        return f"""
            rate({self.THROUGHPUT_COUNTER}{{session_id="{session_id}"}}[5m]) * 60
        """.strip()

    def get_error_queries(self, session_id: str) -> dict[str, str]:
        """Get PromQL queries for error metrics.

        Args:
            session_id: Session identifier for filtering metrics

        Returns:
            Dictionary mapping metric names to PromQL query strings
        """
        base_filter = f'session_id="{session_id}"'

        return {
            "error_rate": f"""
                rate({self.ERROR_COUNTER}{{{base_filter}}}[5m])
            """.strip(),
            "error_percentage": f"""
                (
                    rate({self.ERROR_COUNTER}{{{base_filter}}}[5m]) /
                    rate({self.THROUGHPUT_COUNTER}{{{base_filter}}}[5m])
                ) * 100
            """.strip(),
        }

    def get_cache_queries(self, session_id: str) -> dict[str, str]:
        """Get PromQL queries for cache metrics.

        Args:
            session_id: Session identifier for filtering metrics

        Returns:
            Dictionary mapping metric names to PromQL query strings
        """
        base_filter = f'session_id="{session_id}"'

        return {
            "cache_hit_rate": f"""
                rate({self.CACHE_COUNTER}{{{base_filter}}}[5m])
            """.strip(),
            "cache_hit_percentage": f"""
                (
                    rate({self.CACHE_COUNTER}{{{base_filter}}}[5m]) /
                    rate({self.THROUGHPUT_COUNTER}{{{base_filter}}}[5m])
                ) * 100
            """.strip(),
        }

    def compute_rollup(
        self,
        dimension_type: str,
        dimension_id: str,
        metric_name: str,
        values: list[float],
    ) -> MetricRollup | None:
        """Compute a rollup from raw metric values.

        Handles empty windows gracefully without corrupting aggregates.

        Args:
            dimension_type: Type of dimension (request, session, variant, experiment)
            dimension_id: Identifier for the dimension
            metric_name: Name of the metric being computed
            values: List of raw float values from Prometheus

        Returns:
            MetricRollup object or None if values are empty/invalid
        """
        if not values:
            # Empty windows should not corrupt aggregates
            return None

        # Compute statistics
        sorted_values = sorted(values)
        n = len(sorted_values)

        # Median: average of middle two for even-length lists
        if n % 2 == 1:
            metric_value = sorted_values[n // 2]
        else:
            metric_value = (sorted_values[n // 2 - 1] + sorted_values[n // 2]) / 2

        return MetricRollup(
            dimension_type=dimension_type,
            dimension_id=dimension_id,
            metric_name=metric_name,
            metric_value=metric_value,
            sample_count=n,
        )
