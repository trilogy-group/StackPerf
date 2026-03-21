"""LiteLLM request collector for ingesting raw request records."""
import structlog
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from benchmark_core.models import Request, RequestStatus
from benchmark_core.repositories.request_repository import RequestRepository
from benchmark_core.repositories.session_repository import SessionRepository


logger = structlog.get_logger()


class MissingFieldError(Exception):
    """Raised when a required field is missing from raw data."""
    pass


class UnmappedRowError(Exception):
    """Raised when a row cannot be mapped to a session."""
    pass


class LiteLLMCollector:
    """Collector for ingesting LiteLLM request data."""

    REQUIRED_FIELDS = ["litellm_call_id", "model", "started_at"]
    CORRELATION_KEYS = ["session_id", "experiment_id", "variant_id", "provider_id"]

    def __init__(self, session: AsyncSession):
        self.session = session
        self.request_repo = RequestRepository()
        self.session_repo = SessionRepository()
        self.diagnostics: List[Dict[str, Any]] = []

    def _validate_required_fields(self, raw_data: Dict[str, Any]) -> None:
        """Validate that required fields are present."""
        missing = []
        for field in self.REQUIRED_FIELDS:
            if field not in raw_data or raw_data[field] is None:
                missing.append(field)
        
        if missing:
            error_msg = f"Missing required fields: {', '.join(missing)}"
            self.diagnostics.append({
                "type": "missing_field",
                "fields": missing,
                "raw_data_sample": {k: str(v)[:100] for k, v in list(raw_data.items())[:5]},
                "message": error_msg,
            })
            raise MissingFieldError(error_msg)

    def _extract_correlation_keys(self, raw_data: Dict[str, Any]) -> Dict[str, Optional[str]]:
        """Extract correlation keys from raw data."""
        keys = {}
        for key in self.CORRELATION_KEYS:
            value = raw_data.get(key)
            if value is not None:
                keys[key] = str(value)
            else:
                keys[key] = None
        
        # Try to extract from tags if present
        tags = raw_data.get("tags", {})
        if isinstance(tags, dict):
            for key in self.CORRELATION_KEYS:
                if keys[key] is None and key in tags:
                    keys[key] = str(tags[key])
        
        return keys

    async def _resolve_session(
        self, 
        correlation_keys: Dict[str, Optional[str]],
        proxy_key_alias: Optional[str] = None,
    ) -> Optional[str]:
        """Resolve session from correlation keys or proxy key alias."""
        # First try direct session_id
        if correlation_keys.get("session_id"):
            return correlation_keys["session_id"]
        
        # Try to find session by proxy_key_alias
        if proxy_key_alias:
            session_model = await self.session_repo.get_by_proxy_key_alias(
                self.session, proxy_key_alias
            )
            if session_model:
                return session_model.session_id
        
        return None

    def _parse_status(self, raw_status: Optional[str]) -> RequestStatus:
        """Parse request status from raw data."""
        if raw_status is None:
            return RequestStatus.SUCCESS
        
        status_map = {
            "success": RequestStatus.SUCCESS,
            "error": RequestStatus.ERROR,
            "timeout": RequestStatus.TIMEOUT,
            "cancelled": RequestStatus.CANCELLED,
        }
        return status_map.get(raw_status.lower(), RequestStatus.SUCCESS)

    async def ingest_raw_request(self, raw_data: Dict[str, Any]) -> Optional[Request]:
        """Ingest a single raw request record.

        Args:
            raw_data: Raw request data from LiteLLM

        Returns:
            Normalized Request model or None if duplicate

        Raises:
            MissingFieldError: If required fields are missing
            UnmappedRowError: If row cannot be mapped to session (when required)
        """
        # Validate required fields
        self._validate_required_fields(raw_data)

        litellm_call_id = raw_data["litellm_call_id"]

        # Check for duplicate
        if await self.request_repo.exists_by_litellm_call_id(
            self.session, litellm_call_id
        ):
            logger.debug(
                "Skipping duplicate request",
                litellm_call_id=litellm_call_id,
            )
            return None

        # Extract correlation keys
        correlation_keys = self._extract_correlation_keys(raw_data)
        proxy_key_alias = raw_data.get("proxy_key_alias")

        # Resolve session
        session_id = await self._resolve_session(correlation_keys, proxy_key_alias)

        # Map status
        status = self._parse_status(raw_data.get("status"))

        # Build normalized request
        request = Request(
            session_id=UUID(session_id) if session_id else None,
            experiment_id=UUID(correlation_keys["experiment_id"]) if correlation_keys.get("experiment_id") else None,
            variant_id=UUID(correlation_keys["variant_id"]) if correlation_keys.get("variant_id") else None,
            provider_id=UUID(correlation_keys["provider_id"]) if correlation_keys.get("provider_id") else None,
            provider_route=raw_data.get("provider_route"),
            model=raw_data.get("model"),
            harness_profile_id=UUID(correlation_keys.get("harness_profile_id")) if correlation_keys.get("harness_profile_id") else None,
            litellm_call_id=litellm_call_id,
            provider_request_id=raw_data.get("provider_request_id"),
            started_at=raw_data.get("started_at"),
            finished_at=raw_data.get("finished_at"),
            latency_ms=raw_data.get("latency_ms"),
            ttft_ms=raw_data.get("ttft_ms"),
            proxy_overhead_ms=raw_data.get("proxy_overhead_ms"),
            provider_latency_ms=raw_data.get("provider_latency_ms"),
            input_tokens=raw_data.get("input_tokens"),
            output_tokens=raw_data.get("output_tokens"),
            cached_input_tokens=raw_data.get("cached_input_tokens"),
            cache_write_tokens=raw_data.get("cache_write_tokens"),
            status=status,
            error_code=raw_data.get("error_code"),
        )

        # Persist
        model = await self.request_repo.create(self.session, request)
        
        logger.info(
            "Ingested request",
            request_id=model.request_id,
            litellm_call_id=litellm_call_id,
            session_id=session_id,
        )

        return request

    async def ingest_batch(self, raw_requests: List[Dict[str, Any]]) -> int:
        """Ingest multiple raw request records.

        Args:
            raw_requests: List of raw request data

        Returns:
            Number of successfully ingested records
        """
        ingested = 0
        for raw_data in raw_requests:
            try:
                result = await self.ingest_raw_request(raw_data)
                if result:
                    ingested += 1
            except (MissingFieldError, UnmappedRowError) as e:
                logger.warning(
                    "Failed to ingest request",
                    error=str(e),
                    litellm_call_id=raw_data.get("litellm_call_id"),
                )
        return ingested

    def get_diagnostics(self) -> List[Dict[str, Any]]:
        """Get accumulated diagnostics."""
        return self.diagnostics
