"""Request normalization logic for canonical field mapping."""
import structlog
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from benchmark_core.db.models import RequestModel, SessionModel, VariantModel
from benchmark_core.models import Request


logger = structlog.get_logger()


class NormalizationDiagnostics:
    """Container for normalization diagnostics."""

    def __init__(self):
        self.missing_sessions: List[str] = []
        self.missing_variants: List[str] = []
        self.unmapped_rows: List[Dict[str, Any]] = []

    def has_issues(self) -> bool:
        return bool(self.missing_sessions or self.missing_variants or self.unmapped_rows)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "missing_sessions": self.missing_sessions,
            "missing_variants": self.missing_variants,
            "unmapped_rows": self.unmapped_rows,
        }


class RequestNormalizer:
    """Normalizes raw requests to canonical format."""

    CANONICAL_FIELDS = [
        "request_id",
        "session_id",
        "variant_id",
        "experiment_id",
        "provider_id",
        "provider_route",
        "model",
        "harness_profile_id",
        "litellm_call_id",
        "provider_request_id",
        "started_at",
        "finished_at",
        "latency_ms",
        "ttft_ms",
        "input_tokens",
        "output_tokens",
        "cached_input_tokens",
        "cache_write_tokens",
        "status",
    ]

    def __init__(self, session: AsyncSession):
        self.session = session
        self.diagnostics = NormalizationDiagnostics()

    async def normalize_request(self, request: RequestModel) -> Optional[Request]:
        """Normalize a single request model to canonical format.

        Args:
            request: Raw request model from database

        Returns:
            Normalized Request domain model
        """
        # Check join integrity
        if request.session_id and not request.session:
            self.diagnostics.missing_sessions.append(request.session_id)
            logger.warning(
                "Request references missing session",
                request_id=request.request_id,
                session_id=request.session_id,
            )

        if request.variant_id and not request.variant:
            self.diagnostics.missing_variants.append(request.variant_id)
            logger.warning(
                "Request references missing variant",
                request_id=request.request_id,
                variant_id=request.variant_id,
            )

        return Request(
            request_id=UUID(request.request_id),
            session_id=UUID(request.session_id) if request.session_id else None,
            experiment_id=UUID(request.experiment_id) if request.experiment_id else None,
            variant_id=UUID(request.variant_id) if request.variant_id else None,
            provider_id=UUID(request.provider_id) if request.provider_id else None,
            provider_route=request.provider_route,
            model=request.model,
            harness_profile_id=UUID(request.harness_profile_id) if request.harness_profile_id else None,
            litellm_call_id=request.litellm_call_id,
            provider_request_id=request.provider_request_id,
            started_at=request.started_at,
            finished_at=request.finished_at,
            latency_ms=request.latency_ms,
            ttft_ms=request.ttft_ms,
            proxy_overhead_ms=request.proxy_overhead_ms,
            provider_latency_ms=request.provider_latency_ms,
            input_tokens=request.input_tokens,
            output_tokens=request.output_tokens,
            cached_input_tokens=request.cached_input_tokens,
            cache_write_tokens=request.cache_write_tokens,
            status=request.status,
            error_code=request.error_code,
        )

    async def normalize_unmapped(
        self, 
        raw_requests: List[Dict[str, Any]],
        session_alias_map: Optional[Dict[str, str]] = None,
    ) -> int:
        """Normalize raw requests that lack session correlation.

        This method attempts to map requests to sessions using
        proxy_key_alias lookups.

        Args:
            raw_requests: Raw request data lacking session_id
            session_alias_map: Optional mapping of proxy_key_alias to session_id

        Returns:
            Number of successfully mapped requests
        """
        mapped = 0
        session_alias_map = session_alias_map or {}

        for raw in raw_requests:
            proxy_alias = raw.get("proxy_key_alias")
            if not proxy_alias or proxy_alias not in session_alias_map:
                self.diagnostics.unmapped_rows.append({
                    "litellm_call_id": raw.get("litellm_call_id"),
                    "reason": "no_matching_proxy_alias",
                })
                continue

            # Inject session_id from mapping
            raw["session_id"] = session_alias_map[proxy_alias]
            mapped += 1

        return mapped

    async def join_to_sessions(
        self, 
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Join requests to sessions and variants for analysis.

        Args:
            start_time: Filter requests after this time
            end_time: Filter requests before this time

        Returns:
            List of joined records with session and variant info
        """
        query = (
            select(RequestModel, SessionModel, VariantModel)
            .join(SessionModel, RequestModel.session_id == SessionModel.session_id)
            .join(VariantModel, SessionModel.variant_id == VariantModel.variant_id)
        )

        if start_time:
            query = query.where(RequestModel.started_at >= start_time)
        if end_time:
            query = query.where(RequestModel.started_at <= end_time)

        result = await self.session.execute(query)
        
        joined = []
        for req, sess, var in result.all():
            joined.append({
                "request_id": req.request_id,
                "session_id": sess.session_id,
                "variant_id": var.variant_id,
                "experiment_id": sess.experiment_id,
                "provider_id": var.provider_id,
                "model": req.model,
                "latency_ms": req.latency_ms,
                "ttft_ms": req.ttft_ms,
                "status": req.status.value,
                "started_at": req.started_at.isoformat() if req.started_at else None,
            })

        return joined

    def get_diagnostics(self) -> NormalizationDiagnostics:
        """Get normalization diagnostics."""
        return self.diagnostics
