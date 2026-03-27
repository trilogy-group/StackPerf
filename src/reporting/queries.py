"""Dashboard query helpers for the canonical query model.

All queries use parameterized placeholders (:param_name) to prevent SQL injection.
Never use string interpolation or f-strings for user-provided values.
"""

from typing import Any


class DashboardQueries:
    """Query helpers for dashboard data.

    All methods return SQL with parameterized placeholders. Callers must use
    an async database driver with proper parameter binding to prevent SQL injection.
    """

    @staticmethod
    def session_overview() -> tuple[str, dict[str, Any]]:
        """Generate parameterized SQL for session overview.

        Returns:
            Tuple of (SQL query string with :session_id placeholder,
                     parameter template dict)

        Example:
            sql, params = DashboardQueries.session_overview()
            # Execute with driver parameter binding:
            # await db.fetch_one(sql, {"session_id": str(session_id)})
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
        return query, {"session_id": None}  # Params set by caller with proper binding

    @staticmethod
    def experiment_summary() -> tuple[str, dict[str, Any]]:
        """Generate parameterized SQL for experiment summary.

        Returns:
            Tuple of (SQL query string with :experiment_id placeholder,
                     parameter template dict)

        Example:
            sql, params = DashboardQueries.experiment_summary()
            # Execute with driver parameter binding:
            # await db.fetch_all(sql, {"experiment_id": experiment_id})
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
        return query, {"experiment_id": None}  # Params set by caller with proper binding

    @staticmethod
    def latency_distribution(session_count: int) -> tuple[str, list[str]]:
        """Generate parameterized SQL for latency distribution across sessions.

        Uses programmatically-generated parameterized placeholders for the IN clause.
        All placeholders are safe as they are generated server-side without
        user input interpolation.

        Args:
            session_count: Number of session IDs to query (must be validated > 0)

        Returns:
            Tuple of (SQL query string with numbered :session_id_N placeholders,
                     list of placeholder names for parameter binding)

        Example:
            sql, placeholders = DashboardQueries.latency_distribution(len(session_ids))
            params = {p: str(sid) for p, sid in zip(placeholders, session_ids)}
            # Execute with driver parameter binding:
            # await db.fetch_all(sql, params)
        """
        # Build parameterized placeholders server-side (safe - no user input)
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

    @staticmethod
    def experiment_summary_valid_only() -> tuple[str, dict[str, Any]]:
        """Generate parameterized SQL for experiment summary (valid sessions only).

        Excludes sessions with outcome_state='invalid' for clean comparisons.
        Sessions with outcome_state='valid' or outcome_state IS NULL are included.

        Returns:
            Tuple of (SQL query string with :experiment_id placeholder,
                     parameter template dict)

        Example:
            sql, params = DashboardQueries.experiment_summary_valid_only()
            # Execute with driver parameter binding:
            # await db.fetch_all(sql, {"experiment_id": experiment_id})
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
          AND (s.outcome_state IS NULL OR s.outcome_state != 'invalid')
        GROUP BY v.variant_id
        """
        return query, {"experiment_id": None}  # Params set by caller with proper binding

    @staticmethod
    def list_sessions_with_outcome() -> tuple[str, dict[str, Any]]:
        """Generate parameterized SQL to list sessions with their outcome state.

        Returns:
            Tuple of (SQL query string with optional filters,
                     parameter template dict with :experiment_id)

        Example:
            sql, params = DashboardQueries.list_sessions_with_outcome()
            # Execute with driver parameter binding:
            # await db.fetch_all(sql, {"experiment_id": exp_id})
        """
        query = """
        SELECT
            s.id as session_id,
            s.status,
            s.outcome_state,
            s.started_at,
            s.ended_at,
            s.notes,
            e.name as experiment_name,
            v.name as variant_name,
            t.name as task_card_name
        FROM sessions s
        JOIN experiments e ON s.experiment_id = e.id
        JOIN variants v ON s.variant_id = v.id
        JOIN task_cards t ON s.task_card_id = t.id
        WHERE s.experiment_id = :experiment_id
        ORDER BY s.started_at DESC
        """
        return query, {"experiment_id": None}
