"""Export service for session and experiment data."""

import csv
import json
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session as SQLAlchemySession

from benchmark_core.db.models import (
    Experiment,
    Request,
)
from benchmark_core.db.models import (
    Session as DBSession,
)


class ExportService:
    """Service for exporting session and experiment data.

    Provides structured export functionality with:
    - Stable canonical fields for reproducibility
    - Secret redaction by default
    - Multiple output formats (JSON, CSV, optional Parquet)
    """

    # Fields to redact for security
    SENSITIVE_FIELDS = {
        "proxy_credential_id",
        "proxy_credential_alias",
        "api_key",
        "api_key_env",
        "upstream_base_url_env",
    }

    # Canonical session export fields
    SESSION_EXPORT_FIELDS = [
        "id",
        "experiment_id",
        "variant_id",
        "task_card_id",
        "harness_profile",
        "repo_path",
        "git_branch",
        "git_commit",
        "git_dirty",
        "operator_label",
        "status",
        "outcome_state",
        "started_at",
        "ended_at",
        "duration_seconds",
        "created_at",
        "updated_at",
    ]

    # Canonical request export fields
    REQUEST_EXPORT_FIELDS = [
        "id",
        "request_id",
        "session_id",
        "provider",
        "model",
        "timestamp",
        "latency_ms",
        "ttft_ms",
        "tokens_prompt",
        "tokens_completion",
        "tokens_total",
        "error",
        "error_message",
        "cache_hit",
    ]

    # Canonical experiment export fields
    EXPERIMENT_EXPORT_FIELDS = [
        "id",
        "name",
        "description",
        "created_at",
        "updated_at",
    ]

    def __init__(self, db_session: SQLAlchemySession) -> None:
        """Initialize the export service.

        Args:
            db_session: SQLAlchemy session for database operations.
        """
        self._db_session = db_session

    def export_session(
        self,
        session_id: UUID,
        include_requests: bool = True,
        redact_secrets: bool = True,
    ) -> dict[str, Any]:
        """Export session data with canonical fields.

        Args:
            session_id: The session UUID to export.
            include_requests: Whether to include request-level data.
            redact_secrets: Whether to redact sensitive fields.

        Returns:
            Dictionary with session data and optional request data.

        Raises:
            ValueError: If session not found.
        """
        # Fetch session
        session = self._db_session.get(DBSession, session_id)
        if session is None:
            raise ValueError(f"Session not found: {session_id}")

        # Build session data
        session_data = {
            "id": str(session.id),
            "experiment_id": str(session.experiment_id),
            "variant_id": str(session.variant_id),
            "task_card_id": str(session.task_card_id),
            "harness_profile": session.harness_profile,
            "repo_path": session.repo_path,
            "git_branch": session.git_branch,
            "git_commit": session.git_commit,
            "git_dirty": session.git_dirty,
            "operator_label": session.operator_label,
            "status": session.status,
            "outcome_state": session.outcome_state,
            "started_at": session.started_at.isoformat() if session.started_at else None,
            "ended_at": session.ended_at.isoformat() if session.ended_at else None,
            "duration_seconds": self._calculate_duration(session),
            "created_at": session.created_at.isoformat() if session.created_at else None,
            "updated_at": session.updated_at.isoformat() if session.updated_at else None,
        }

        # Add sensitive fields if not redacting
        if not redact_secrets:
            session_data["proxy_credential_alias"] = session.proxy_credential_alias
            session_data["proxy_credential_id"] = session.proxy_credential_id

        # Add notes if present
        if session.notes:
            session_data["notes"] = session.notes

        export: dict[str, Any] = {"session": session_data}

        # Include requests if requested
        if include_requests:
            requests = self._fetch_session_requests(session_id)
            export["requests"] = [
                self._format_request(req) for req in requests
            ]

            # Add summary statistics
            export["summary"] = self._calculate_session_summary(requests)

        return export

    def export_experiment(
        self,
        experiment_id: UUID,
        include_sessions: bool = True,
        include_requests: bool = False,
        redact_secrets: bool = True,
    ) -> dict[str, Any]:
        """Export experiment data with canonical fields.

        Args:
            experiment_id: The experiment UUID to export.
            include_sessions: Whether to include session-level data.
            include_requests: Whether to include request-level data (implies sessions).
            redact_secrets: Whether to redact sensitive fields.

        Returns:
            Dictionary with experiment data and optional session/request data.

        Raises:
            ValueError: If experiment not found.
        """
        # Fetch experiment
        experiment = self._db_session.get(Experiment, experiment_id)
        if experiment is None:
            raise ValueError(f"Experiment not found: {experiment_id}")

        # Build experiment data
        experiment_data = {
            "id": str(experiment.id),
            "name": experiment.name,
            "description": experiment.description,
            "created_at": experiment.created_at.isoformat() if experiment.created_at else None,
            "updated_at": experiment.updated_at.isoformat() if experiment.updated_at else None,
        }

        export: dict[str, Any] = {"experiment": experiment_data}

        # Include sessions if requested
        if include_sessions or include_requests:
            sessions = self._fetch_experiment_sessions(experiment_id)
            sessions_list: list[dict[str, Any]] = []

            for session in sessions:
                session_export: dict[str, Any] = {
                    "id": str(session.id),
                    "variant_id": str(session.variant_id),
                    "task_card_id": str(session.task_card_id),
                    "harness_profile": session.harness_profile,
                    "status": session.status,
                    "outcome_state": session.outcome_state,
                    "started_at": session.started_at.isoformat() if session.started_at else None,
                    "ended_at": session.ended_at.isoformat() if session.ended_at else None,
                    "duration_seconds": self._calculate_duration(session),
                }

                if not redact_secrets:
                    session_export["proxy_credential_alias"] = session.proxy_credential_alias

                sessions_list.append(session_export)

                # Include requests for each session if requested
                if include_requests:
                    requests = self._fetch_session_requests(session.id)
                    session_export["requests"] = [
                        self._format_request(req) for req in requests
                    ]
                    session_export["request_count"] = len(requests)

            export["sessions"] = sessions_list

            # Add experiment-level summary
            export["summary"] = self._calculate_experiment_summary(sessions)

        return export

    def _fetch_session_requests(self, session_id: UUID) -> list[Request]:
        """Fetch all requests for a session.

        Args:
            session_id: The session UUID.

        Returns:
            List of Request objects.
        """
        stmt = (
            select(Request)
            .where(Request.session_id == session_id)
            .order_by(Request.timestamp)
        )
        result = self._db_session.execute(stmt).scalars().all()
        return list(result)

    def _fetch_experiment_sessions(self, experiment_id: UUID) -> list[DBSession]:
        """Fetch all sessions for an experiment.

        Args:
            experiment_id: The experiment UUID.

        Returns:
            List of Session objects.
        """
        stmt = (
            select(DBSession)
            .where(DBSession.experiment_id == experiment_id)
            .order_by(DBSession.started_at)
        )
        result = self._db_session.execute(stmt).scalars().all()
        return list(result)

    def _format_request(self, request: Request) -> dict[str, Any]:
        """Format a request for export.

        Args:
            request: The Request object.

        Returns:
            Dictionary with request data.
        """
        tokens_total = None
        if request.tokens_prompt is not None and request.tokens_completion is not None:
            tokens_total = request.tokens_prompt + request.tokens_completion

        return {
            "id": str(request.id),
            "request_id": request.request_id,
            "session_id": str(request.session_id),
            "provider": request.provider,
            "model": request.model,
            "timestamp": request.timestamp.isoformat() if request.timestamp else None,
            "latency_ms": request.latency_ms,
            "ttft_ms": request.ttft_ms,
            "tokens_prompt": request.tokens_prompt,
            "tokens_completion": request.tokens_completion,
            "tokens_total": tokens_total,
            "error": request.error,
            "error_message": request.error_message,
            "cache_hit": request.cache_hit,
        }

    def _calculate_duration(self, session: DBSession) -> float | None:
        """Calculate session duration in seconds.

        Args:
            session: The Session object.

        Returns:
            Duration in seconds, or None if not finalized.
        """
        if session.ended_at and session.started_at:
            return (session.ended_at - session.started_at).total_seconds()
        return None

    def _calculate_session_summary(self, requests: list[Request]) -> dict[str, Any]:
        """Calculate summary statistics for a session.

        Args:
            requests: List of Request objects.

        Returns:
            Dictionary with summary statistics.
        """
        if not requests:
            return {
                "total_requests": 0,
                "total_tokens_prompt": 0,
                "total_tokens_completion": 0,
                "error_count": 0,
                "cache_hit_count": 0,
            }

        total_latency = 0.0
        total_tokens_prompt = 0
        total_tokens_completion = 0
        error_count = 0
        cache_hit_count = 0

        for req in requests:
            if req.latency_ms is not None:
                total_latency += req.latency_ms
            if req.tokens_prompt is not None:
                total_tokens_prompt += req.tokens_prompt
            if req.tokens_completion is not None:
                total_tokens_completion += req.tokens_completion
            if req.error:
                error_count += 1
            if req.cache_hit:
                cache_hit_count += 1

        return {
            "total_requests": len(requests),
            "total_tokens_prompt": total_tokens_prompt,
            "total_tokens_completion": total_tokens_completion,
            "avg_latency_ms": total_latency / len(requests) if requests else None,
            "error_count": error_count,
            "error_rate": error_count / len(requests) if requests else 0,
            "cache_hit_count": cache_hit_count,
            "cache_hit_rate": cache_hit_count / len(requests) if requests else 0,
        }

    def _calculate_experiment_summary(self, sessions: list[DBSession]) -> dict[str, Any]:
        """Calculate summary statistics for an experiment.

        Args:
            sessions: List of Session objects.

        Returns:
            Dictionary with summary statistics.
        """
        if not sessions:
            return {
                "total_sessions": 0,
                "completed_sessions": 0,
                "active_sessions": 0,
                "failed_sessions": 0,
            }

        status_counts: dict[str, int] = {}
        for session in sessions:
            status = session.status or "unknown"
            status_counts[status] = status_counts.get(status, 0) + 1

        return {
            "total_sessions": len(sessions),
            "status_breakdown": status_counts,
            "completed_sessions": status_counts.get("completed", 0),
            "active_sessions": status_counts.get("active", 0),
            "failed_sessions": status_counts.get("failed", 0),
        }


class ExportSerializer:
    """Serializer for export data in various formats."""

    @staticmethod
    def to_json(data: dict[str, Any], output_path: Path) -> None:
        """Serialize export data to JSON.

        Args:
            data: The export data dictionary.
            output_path: Path to write the output file.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    @staticmethod
    def to_csv(
        data: dict[str, Any],
        output_path: Path,
        record_type: str = "requests",
    ) -> None:
        """Serialize export data to CSV.

        Note: CSV export flattens nested data structures.

        Args:
            data: The export data dictionary.
            output_path: Path to write the output file.
            record_type: Type of records to export ('requests' or 'sessions').
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Extract records based on type
        if record_type == "requests" and "requests" in data:
            records = data["requests"]
            fieldnames = ExportService.REQUEST_EXPORT_FIELDS
        elif record_type == "sessions" and "sessions" in data:
            records = data["sessions"]
            fieldnames = ["id", "variant_id", "status", "started_at", "ended_at", "duration_seconds"]
        else:
            # Fallback to session-level data for single session export
            if "session" in data:
                records = [data["session"]]
                fieldnames = ExportService.SESSION_EXPORT_FIELDS
            else:
                records = []
                fieldnames = []

        if not records:
            # Write empty file with headers
            with open(output_path, "w", newline="") as f:
                if fieldnames:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
            return

        # Get all unique keys from records
        all_keys = sorted({k for record in records for k in record})

        with open(output_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=all_keys)
            writer.writeheader()
            writer.writerows(records)

    @staticmethod
    def to_parquet(
        data: dict[str, Any],
        output_path: Path,
        record_type: str = "requests",
    ) -> None:
        """Serialize export data to Parquet format.

        Args:
            data: The export data dictionary.
            output_path: Path to write the output file.
            record_type: Type of records to export ('requests' or 'sessions').

        Raises:
            ImportError: If pyarrow is not installed.
        """
        try:
            import pyarrow as pa
            import pyarrow.parquet as pq
        except ImportError as e:
            raise ImportError(
                "Parquet export requires pyarrow. "
                "Install with: pip install pyarrow"
            ) from e

        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Extract records based on type
        if record_type == "requests" and "requests" in data:
            records = data["requests"]
        elif record_type == "sessions" and "sessions" in data:
            records = data["sessions"]
        elif "session" in data:
            records = [data["session"]]
        else:
            records = []

        table = pa.table({}) if not records else pa.Table.from_pylist(records)

        pq.write_table(table, output_path)
