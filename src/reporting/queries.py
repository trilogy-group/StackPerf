"""Dashboard query helpers for the canonical query model."""

from typing import Any


class DashboardQueries:
    """Query helpers for dashboard data."""

    @staticmethod
    def session_overview() -> tuple[str, dict[str, Any]]:
        """Generate parameterized SQL for session overview.

        Returns:
            Tuple of (SQL query string, parameter dict with :session_id placeholder)
        """
        query = """
        SELECT
            s.session_id,
            s.experiment_id,
            s.variant_id,
            s.task_card_id,
            s.status,
            s.started_at,
            s.ended_at,
            COUNT(r.request_id) as request_count,
            AVG(r.latency_ms) as avg_latency_ms,
            SUM(CASE WHEN r.error THEN 1 ELSE 0 END) as error_count
        FROM sessions s
        LEFT JOIN requests r ON s.session_id = r.session_id
        WHERE s.session_id = :session_id
        GROUP BY s.session_id
        """
        return query, {"session_id": None}  # Params set by caller

    @staticmethod
    def experiment_summary() -> tuple[str, dict[str, Any]]:
        """Generate parameterized SQL for experiment summary.

        Returns:
            Tuple of (SQL query string, parameter dict with :experiment_id placeholder)
        """
        query = """
        SELECT
            v.variant_id,
            COUNT(DISTINCT s.session_id) as session_count,
            COUNT(r.request_id) as total_requests,
            AVG(r.latency_ms) as avg_latency_ms,
            AVG(r.ttft_ms) as avg_ttft_ms,
            SUM(CASE WHEN r.error THEN 1 ELSE 0 END) as total_errors
        FROM variants v
        JOIN sessions s ON s.variant_id = v.variant_id
        LEFT JOIN requests r ON s.session_id = r.session_id
        WHERE s.experiment_id = :experiment_id
        GROUP BY v.variant_id
        """
        return query, {"experiment_id": None}  # Params set by caller

    @staticmethod
    def latency_distribution(session_count: int) -> tuple[str, list[str]]:
        """Generate parameterized SQL for latency distribution across sessions.

        Args:
            session_count: Number of session IDs to query

        Returns:
            Tuple of (SQL query string, list of placeholder names)
        """
        # Build parameterized placeholders
        placeholders = [f":session_id_{i}" for i in range(session_count)]
        placeholders_str = ", ".join(placeholders)

        query = f"""
        SELECT
            session_id,
            latency_ms,
            ttft_ms,
            timestamp
        FROM requests
        WHERE session_id IN ({placeholders_str})
        ORDER BY timestamp
        """
        return query, placeholders
