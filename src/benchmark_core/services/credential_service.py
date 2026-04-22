"""Service for rendering and managing session-scoped proxy credentials.

Unified implementation moved from services_abc.py. Provides both the
full LiteLLM-backed credential lifecycle and backward-compatible
convenience methods.
"""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import httpx
from pydantic import SecretStr

from benchmark_core.models import ProxyCredential
from benchmark_core.services.common import (
    render_env_dotenv,
    render_env_shell,
    validate_litellm_url,
    warn_revoke_failure,
)


class CredentialService:
    """Service for issuing and managing session-scoped proxy credentials.

    Implements the key aliasing convention and metadata tagging strategy
    for correlating LiteLLM traffic back to benchmark sessions.
    """

    def __init__(
        self,
        litellm_base_url: str = "http://localhost:4000",
        master_key: str | None = None,
        enforce_https: bool = True,
    ) -> None:
        """Initialize the credential service.

        Args:
            litellm_base_url: Base URL for LiteLLM proxy API
            master_key: LiteLLM master key for API authentication
            enforce_https: Whether to enforce HTTPS in production (default True)

        Raises:
            ValueError: If litellm_base_url doesn't use HTTPS in production
        """
        self.litellm_base_url = validate_litellm_url(litellm_base_url, enforce_https)
        self.master_key = master_key

    def _generate_key_alias(
        self,
        session_id: UUID,
        experiment_id: str,
        variant_id: str,
    ) -> str:
        """Generate a stable key alias for correlation.

        Format: session-{session_id[:8]}-{experiment_id[:8]}-{variant_id[:8]}

        This alias is:
        - Human-readable for operators
        - Unique per session
        - Joinable back to session via metadata
        """
        session_short = str(session_id)[:8]
        exp_short = experiment_id[:8] if len(experiment_id) >= 8 else experiment_id
        var_short = variant_id[:8] if len(variant_id) >= 8 else variant_id
        return f"session-{session_short}-{exp_short}-{var_short}"

    def _build_metadata_tags(
        self,
        session_id: UUID,
        experiment_id: str,
        variant_id: str,
        harness_profile: str,
    ) -> dict[str, str]:
        """Build metadata tags for LiteLLM credential.

        These tags enable joining LiteLLM request logs back to
        the benchmark session and its dimensions.
        """
        return {
            "benchmark_session_id": str(session_id),
            "benchmark_experiment_id": experiment_id,
            "benchmark_variant_id": variant_id,
            "benchmark_harness_profile": harness_profile,
            "benchmark_source": "opensymphony",
        }

    async def issue_credential(
        self,
        session_id: UUID,
        experiment_id: str,
        variant_id: str,
        harness_profile: str,
        ttl_hours: int = 24,
    ) -> ProxyCredential:
        """Issue a session-scoped proxy credential via LiteLLM API.

        Creates a LiteLLM virtual key with:
        - Unique key alias for correlation
        - Metadata tags linking to session
        - Configurable TTL (default 24 hours)

        Args:
            session_id: Benchmark session UUID
            experiment_id: Experiment identifier
            variant_id: Variant identifier
            harness_profile: Harness profile name
            ttl_hours: Credential time-to-live in hours

        Returns:
            ProxyCredential with metadata and API key

        Raises:
            RuntimeError: If LiteLLM API call fails or master_key not configured
        """
        if self.master_key is None:
            raise RuntimeError(
                "Cannot issue credential: LiteLLM master_key not configured. "
                "Initialize CredentialService with master_key parameter."
            )

        # Generate stable alias for correlation
        key_alias = self._generate_key_alias(session_id, experiment_id, variant_id)

        # Build metadata tags for LiteLLM correlation
        metadata_tags = self._build_metadata_tags(
            session_id, experiment_id, variant_id, harness_profile
        )

        # Calculate expiration
        expires_at = datetime.now(UTC) + timedelta(hours=ttl_hours)

        # Call LiteLLM API to create the key
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{self.litellm_base_url}/key/generate",
                    headers={"Authorization": f"Bearer {self.master_key}"},
                    json={
                        "key_alias": key_alias,
                        "metadata": metadata_tags,
                        "expires": expires_at.isoformat(),
                    },
                )
                response.raise_for_status()
                data: dict[str, Any] = response.json()
            except httpx.HTTPStatusError as e:
                raise RuntimeError(
                    f"LiteLLM API error creating credential: {e.response.status_code} - "
                    f"{e.response.text}"
                ) from e
            except httpx.RequestError as e:
                raise RuntimeError(
                    f"Failed to connect to LiteLLM at {self.litellm_base_url}: {e}"
                ) from e

        # Extract key and key_id from LiteLLM response
        api_key = data.get("key")
        litellm_key_id = data.get("key_id")

        if not api_key:
            raise RuntimeError(f"LiteLLM API response missing 'key' field: {data}")

        # Create credential domain model
        credential = ProxyCredential(
            session_id=session_id,
            key_alias=key_alias,
            api_key=SecretStr(api_key),
            experiment_id=experiment_id,
            variant_id=variant_id,
            harness_profile=harness_profile,
            metadata_tags=metadata_tags,
            litellm_key_id=litellm_key_id,
            expires_at=expires_at,
            is_active=True,
        )

        return credential

    async def revoke_credential(self, credential: ProxyCredential) -> ProxyCredential:
        """Revoke an active credential via LiteLLM API.

        Marks the credential as revoked and records revocation time.
        Also calls LiteLLM API to delete the key if litellm_key_id is present.

        Args:
            credential: Credential to revoke

        Returns:
            Updated credential with is_active=False

        Note:
            LiteLLM API errors are intentionally silenced since revocation is
            best-effort - the key may already be expired or the proxy may be
            temporarily unavailable.  A warning is still emitted so operators
            can detect state inconsistency.
        """
        # Call LiteLLM API to delete the key if we have the key_id
        if credential.litellm_key_id and self.master_key:
            async with httpx.AsyncClient(timeout=30.0) as client:
                try:
                    response = await client.post(
                        f"{self.litellm_base_url}/key/delete",
                        headers={"Authorization": f"Bearer {self.master_key}"},
                        json={"key_ids": [credential.litellm_key_id]},
                    )
                    response.raise_for_status()
                except httpx.HTTPStatusError as e:
                    warn_revoke_failure("credential", credential.litellm_key_id, e)
                except httpx.RequestError as e:
                    warn_revoke_failure("credential", credential.litellm_key_id, e)

        updated = credential.model_copy(
            update={
                "is_active": False,
                "revoked_at": datetime.now(UTC),
                # Clear the secret from memory
                "api_key": SecretStr("REDACTED"),
            }
        )
        return updated

    # ------------------------------------------------------------------
    # Environment rendering
    # ------------------------------------------------------------------

    def render_env_snippet(
        self,
        credential: ProxyCredential,
        proxy_base_url: str,
        model: str,
    ) -> dict[str, str]:
        """Render environment variable snippet for a harness.

        Args:
            credential: Proxy credential with API key
            proxy_base_url: LiteLLM proxy base URL
            model: Model identifier/alias

        Returns:
            Dictionary of environment variables
        """
        return {
            "OPENAI_API_BASE": proxy_base_url,
            "OPENAI_API_KEY": credential.api_key.get_secret_value(),
            "OPENAI_MODEL": model,
            "LITELLM_SESSION_ALIAS": credential.key_alias,
        }

    def render_env_shell(self, env_vars: dict[str, str]) -> str:
        """Render environment variables as shell export commands.

        Args:
            env_vars: Dictionary of environment variables.

        Returns:
            Shell commands string.
        """
        return render_env_shell(env_vars)

    def render_env_dotenv(self, env_vars: dict[str, str]) -> str:
        """Render environment variables as dotenv file content.

        Args:
            env_vars: Dictionary of environment variables.

        Returns:
            Dotenv file content string.
        """
        return render_env_dotenv(env_vars)
