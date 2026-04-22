"""Service for sessionless proxy key operations via LiteLLM API.

Provides creation, listing, revocation, and environment rendering
for LiteLLM virtual keys without requiring a benchmark session.
Only non-secret key metadata is persisted locally.
"""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import httpx
from pydantic import SecretStr

from benchmark_core.config import UsagePolicyProfile
from benchmark_core.db.models import ProxyKey as ProxyKeyORM
from benchmark_core.models import ProxyKey, ProxyKeyStatus
from benchmark_core.repositories.proxy_key_repository import SQLProxyKeyRepository


class ProxyKeyServiceError(Exception):
    """Raised when proxy key service operations fail."""

    pass


class LiteLLMAPIError(ProxyKeyServiceError):
    """Raised when LiteLLM API call fails."""

    pass


class ProxyKeyService:
    """Service for managing sessionless proxy keys.

    Coordinates LiteLLM virtual key lifecycle with local non-secret
    metadata persistence. Key secrets are displayed once at creation
    and never stored in the benchmark database.
    """

    def __init__(
        self,
        repository: SQLProxyKeyRepository,
        litellm_base_url: str = "http://localhost:4000",
        master_key: str | None = None,
        enforce_https: bool = True,
    ) -> None:
        """Initialize the proxy key service.

        Args:
            repository: Repository for proxy key metadata persistence.
            litellm_base_url: Base URL for LiteLLM proxy API.
            master_key: LiteLLM master key for API authentication.
            enforce_https: Whether to enforce HTTPS in production.

        Raises:
            ValueError: If litellm_base_url doesn't use HTTPS in production.
        """
        self._repository = repository
        self.litellm_base_url = litellm_base_url.rstrip("/")
        self.master_key = master_key

        if enforce_https and not self.litellm_base_url.startswith(
            ("https://", "http://localhost", "http://127.0.0.1")
        ):
            raise ValueError(
                f"LiteLLM URL must use HTTPS in production environments. Got: {litellm_base_url}"
            )

    def _http_headers(self) -> dict[str, str]:
        """Build HTTP headers for LiteLLM API calls."""
        if self.master_key is None:
            raise ProxyKeyServiceError(
                "LiteLLM master_key not configured. "
                "Set LITELLM_MASTER_KEY or initialize ProxyKeyService with master_key."
            )
        return {"Authorization": f"Bearer {self.master_key}"}

    def _build_key_alias(self, prefix: str | None = None) -> str:
        """Generate a stable unique key alias.

        Format: {prefix}-{uuid8} or usage-{uuid8} if no prefix.
        """
        short_uuid = str(uuid4())[:8]
        if prefix:
            return f"{prefix}-{short_uuid}"
        return f"usage-{short_uuid}"

    async def create_key(
        self,
        key_alias: str | None = None,
        owner: str | None = None,
        team: str | None = None,
        customer: str | None = None,
        purpose: str | None = None,
        allowed_models: list[str] | None = None,
        budget_duration: str | None = None,
        budget_amount: float | None = None,
        ttl_hours: int = 168,
        metadata: dict[str, str] | None = None,
        usage_policy: UsagePolicyProfile | None = None,
    ) -> tuple[ProxyKey, SecretStr]:
        """Create a new sessionless proxy key via LiteLLM API.

        The key secret is returned once and never persisted to the database.
        Only non-secret metadata (alias, owner, team, etc.) is stored locally.

        Args:
            key_alias: Human-readable alias. Auto-generated if None.
            owner: Key owner label.
            team: Team metadata.
            customer: Customer metadata.
            purpose: Key purpose/description.
            allowed_models: Optional list of allowed model aliases.
            budget_duration: Budget interval (e.g., "1d", "30d").
            budget_amount: Budget limit in currency units.
            ttl_hours: Key time-to-live in hours (default 7 days).
            metadata: Additional metadata tags.
            usage_policy: Optional usage policy profile to apply defaults from.

        Returns:
            Tuple of (ProxyKey metadata model, SecretStr with the actual key).

        Raises:
            LiteLLMAPIError: If LiteLLM API call fails.
            ProxyKeyServiceError: If master_key not configured.
        """
        if self.master_key is None:
            raise ProxyKeyServiceError("Cannot create key: LiteLLM master_key not configured.")

        # Apply usage policy defaults if provided
        effective_alias = key_alias or self._build_key_alias(
            usage_policy.name if usage_policy else None
        )
        effective_owner = owner or (usage_policy.owner if usage_policy else None)
        effective_team = team or (usage_policy.team if usage_policy else None)
        effective_customer = customer or (usage_policy.customer if usage_policy else None)
        effective_models = allowed_models or (
            list(usage_policy.allowed_models) if usage_policy else []
        )
        effective_budget_duration = budget_duration or (
            usage_policy.budget_duration if usage_policy else None
        )
        effective_budget_amount = budget_amount or (
            usage_policy.budget_amount if usage_policy else None
        )
        effective_ttl = (
            usage_policy.ttl_seconds // 3600
            if usage_policy and usage_policy.ttl_seconds
            else ttl_hours
        )

        # Merge metadata
        effective_metadata: dict[str, Any] = {}
        if usage_policy and usage_policy.metadata:
            effective_metadata.update(usage_policy.metadata)
        if metadata:
            effective_metadata.update(metadata)

        # Calculate expiration
        expires_at = datetime.now(UTC) + timedelta(hours=effective_ttl)

        # Build LiteLLM API payload
        litellm_payload: dict[str, Any] = {
            "key_alias": effective_alias,
            "metadata": effective_metadata,
            "expires": expires_at.isoformat(),
        }
        if effective_models:
            litellm_payload["models"] = effective_models
        if effective_budget_duration:
            litellm_payload["budget_duration"] = effective_budget_duration
        if effective_budget_amount is not None:
            litellm_payload["budget_amount"] = effective_budget_amount

        # Call LiteLLM API to create the key
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{self.litellm_base_url}/key/generate",
                    headers=self._http_headers(),
                    json=litellm_payload,
                )
                response.raise_for_status()
                data: dict[str, Any] = response.json()
            except httpx.HTTPStatusError as e:
                raise LiteLLMAPIError(
                    f"LiteLLM API error creating key: {e.response.status_code} - {e.response.text}"
                ) from e
            except httpx.RequestError as e:
                raise LiteLLMAPIError(
                    f"Failed to connect to LiteLLM at {self.litellm_base_url}: {e}"
                ) from e

        api_key = data.get("key")
        litellm_key_id = data.get("key_id")

        if not api_key:
            raise LiteLLMAPIError(f"LiteLLM API response missing 'key' field: {data}")

        # Build budget_currency from policy default
        budget_currency = "USD"
        if usage_policy and usage_policy.budget_currency:
            budget_currency = usage_policy.budget_currency

        # Create local metadata record (NO secret stored)
        proxy_key = ProxyKey(
            proxy_key_id=uuid4(),
            key_alias=effective_alias,
            litellm_key_id=litellm_key_id,
            owner=effective_owner,
            team=effective_team,
            customer=effective_customer,
            purpose=purpose,
            allowed_models=list(effective_models) if effective_models else [],
            budget_duration=effective_budget_duration,
            budget_amount=effective_budget_amount,
            budget_currency=budget_currency,
            status=ProxyKeyStatus.ACTIVE,
            key_metadata=effective_metadata,
            created_at=datetime.now(UTC),
            expires_at=expires_at,
        )

        # Persist metadata to database
        orm = ProxyKeyORM(
            id=proxy_key.proxy_key_id,
            key_alias=proxy_key.key_alias,
            litellm_key_id=proxy_key.litellm_key_id,
            owner=proxy_key.owner,
            team=proxy_key.team,
            customer=proxy_key.customer,
            purpose=proxy_key.purpose,
            allowed_models=proxy_key.allowed_models,
            budget_duration=proxy_key.budget_duration,
            budget_amount=proxy_key.budget_amount,
            budget_currency=proxy_key.budget_currency,
            status=proxy_key.status.value,
            key_metadata=proxy_key.key_metadata,
            created_at=proxy_key.created_at,
            expires_at=proxy_key.expires_at,
        )
        await self._repository.create(orm)

        return proxy_key, SecretStr(api_key)

    async def list_keys(
        self,
        owner: str | None = None,
        team: str | None = None,
        customer: str | None = None,
        status: ProxyKeyStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ProxyKey]:
        """List proxy keys with optional filtering.

        Args:
            owner: Filter by owner label.
            team: Filter by team label.
            customer: Filter by customer label.
            status: Filter by status.
            limit: Maximum results.
            offset: Results to skip.

        Returns:
            List of ProxyKey metadata models (no secrets).
        """
        if owner:
            orm_list = await self._repository.list_by_owner(owner, limit, offset)
        elif team:
            orm_list = await self._repository.list_by_team(team, limit, offset)
        elif customer:
            orm_list = await self._repository.list_by_customer(customer, limit, offset)
        else:
            orm_list = await self._repository.list_all(limit, offset)

        if status:
            orm_list = [k for k in orm_list if k.status == status.value]

        return [self._orm_to_model(k) for k in orm_list]

    async def get_key_info(self, proxy_key_id: UUID) -> ProxyKey | None:
        """Get detailed info for a proxy key.

        Args:
            proxy_key_id: The UUID of the proxy key.

        Returns:
            ProxyKey model if found, None otherwise.
        """
        orm = await self._repository.get_by_id(proxy_key_id)
        if orm is None:
            return None
        return self._orm_to_model(orm)

    async def get_key_by_alias(self, key_alias: str) -> ProxyKey | None:
        """Get proxy key by its alias.

        Args:
            key_alias: The unique key alias.

        Returns:
            ProxyKey model if found, None otherwise.
        """
        orm = await self._repository.get_by_alias(key_alias)
        if orm is None:
            return None
        return self._orm_to_model(orm)

    async def revoke_key(self, proxy_key_id: UUID) -> ProxyKey | None:
        """Revoke a proxy key.

        Marks the local metadata as inactive and attempts LiteLLM deletion.
        LiteLLM API errors are intentionally silenced since revocation is
        best-effort.

        Args:
            proxy_key_id: The UUID of the proxy key to revoke.

        Returns:
            Updated ProxyKey model if found, None otherwise.
        """
        orm = await self._repository.get_by_id(proxy_key_id)
        if orm is None:
            return None

        if orm.status == ProxyKeyStatus.REVOKED.value:
            return self._orm_to_model(orm)

        # Attempt LiteLLM deletion if we have the key_id
        if orm.litellm_key_id and self.master_key:
            async with httpx.AsyncClient(timeout=30.0) as client:
                try:
                    response = await client.post(
                        f"{self.litellm_base_url}/key/delete",
                        headers=self._http_headers(),
                        json={"key_ids": [orm.litellm_key_id]},
                    )
                    response.raise_for_status()
                except httpx.HTTPStatusError:
                    pass  # Best-effort: key may already be expired/deleted
                except httpx.RequestError:
                    pass  # Best-effort: proxy may be temporarily unavailable

        # Mark local metadata as revoked
        revoked_orm = await self._repository.revoke(proxy_key_id)
        if revoked_orm is None:
            return None
        return self._orm_to_model(revoked_orm)

    def render_env_snippet(
        self,
        api_key: SecretStr,
        proxy_base_url: str = "http://localhost:4000",
        model: str | None = None,
        harness_profile: str = "openai-compatible",
    ) -> dict[str, str]:
        """Render generic OpenAI-compatible environment snippet.

        Args:
            api_key: The proxy key secret.
            proxy_base_url: LiteLLM proxy base URL.
            model: Optional default model alias.
            harness_profile: Harness profile hint for rendering.

        Returns:
            Dictionary of environment variables.
        """
        env_vars: dict[str, str] = {
            "OPENAI_API_BASE": proxy_base_url,
            "OPENAI_API_KEY": api_key.get_secret_value(),
        }
        if model:
            env_vars["OPENAI_MODEL"] = model
        return env_vars

    def render_env_shell(self, env_vars: dict[str, str]) -> str:
        """Render environment variables as shell export commands.

        Args:
            env_vars: Dictionary of environment variables.

        Returns:
            Shell commands string.
        """
        lines = []
        for key in sorted(env_vars.keys()):
            value = env_vars[key]
            escaped = value.replace("'", "'\\''")
            lines.append(f"export {key}='{escaped}'")
        return "\n".join(lines)

    def render_env_dotenv(self, env_vars: dict[str, str]) -> str:
        """Render environment variables as dotenv file content.

        Args:
            env_vars: Dictionary of environment variables.

        Returns:
            Dotenv file content string.
        """
        lines = []
        for key in sorted(env_vars.keys()):
            value = env_vars[key]
            if " " in value or "#" in value or "'" in value or '"' in value:
                escaped = value.replace("\\", "\\\\").replace('"', '\\"')
                lines.append(f'{key}="{escaped}"')
            else:
                lines.append(f"{key}={value}")
        return "\n".join(lines)

    def render_harness_env(
        self,
        api_key: SecretStr,
        harness_profile_name: str,
        proxy_base_url: str = "http://localhost:4000",
        model: str | None = None,
    ) -> dict[str, str]:
        """Render harness-profile-based environment snippet.

        Args:
            api_key: The proxy key secret.
            harness_profile_name: Name of the harness profile.
            proxy_base_url: LiteLLM proxy base URL.
            model: Optional default model alias.

        Returns:
            Dictionary of environment variables.
        """
        # Generic OpenAI-compatible rendering
        # Future: could load harness profile from config and adapt variable names
        env_vars: dict[str, str] = {
            "OPENAI_API_BASE": proxy_base_url,
            "OPENAI_API_KEY": api_key.get_secret_value(),
        }
        if model:
            env_vars["OPENAI_MODEL"] = model
        env_vars["LITELLM_KEY_ALIAS"] = harness_profile_name
        return env_vars

    def _orm_to_model(self, orm: ProxyKeyORM) -> ProxyKey:
        """Convert an ORM ProxyKey to a domain model.

        Args:
            orm: The ORM model.

        Returns:
            The domain model.
        """
        return ProxyKey(
            proxy_key_id=orm.id,
            key_alias=orm.key_alias,
            litellm_key_id=orm.litellm_key_id,
            owner=orm.owner,
            team=orm.team,
            customer=orm.customer,
            purpose=orm.purpose,
            allowed_models=list(orm.allowed_models) if orm.allowed_models else [],
            budget_duration=orm.budget_duration,
            budget_amount=orm.budget_amount,
            budget_currency=orm.budget_currency,
            status=ProxyKeyStatus(orm.status),
            key_metadata=dict(orm.key_metadata) if orm.key_metadata else {},
            proxy_credential_id=orm.proxy_credential_id,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
            revoked_at=orm.revoked_at,
            expires_at=orm.expires_at,
        )
