"""Dashboard query helpers for the canonical query model."""


class DashboardQueries:
    """Query helpers for dashboard data."""

    @staticmethod
    def session_overview(session_id: str) -> str:
        """Generate SQL for session overview."""
        return f"""
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
        WHERE s.session_id = '{session_id}'
        GROUP BY s.session_id
        """

    @staticmethod
    def experiment_summary(experiment_id: str) -> str:
        """Generate SQL for experiment summary."""
        return f"""
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
        WHERE s.experiment_id = '{experiment_id}'
        GROUP BY v.variant_id
        """

    @staticmethod
    def latency_distribution(session_ids: list[str]) -> str:
        """Generate SQL for latency distribution across sessions."""
        ids_str = ", ".join(f"'{s}'" for s in session_ids)
        return f"""
        SELECT
            session_id,
            latency_ms,
            ttft_ms,
            timestamp
        FROM requests
        WHERE session_id IN ({ids_str})
        ORDER BY timestamp
        """
