"""Session-scoped proxy credential issuance."""

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Any

from benchmark_core.config import Settings
from benchmark_core.models import ProxyCredential


class CredentialIssuer:
    """Issues and manages session-scoped proxy credentials."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or Settings()

    def generate_session_credential(
        self,
        session_id: str,
        experiment_id: str | None = None,
        variant_id: str | None = None,
        task_card_id: str | None = None,
        harness_profile_id: str | None = None,
        ttl_hours: int | None = None,
    ) -> ProxyCredential:
        """Generate a session-scoped proxy credential.

        Args:
            session_id: Benchmark session ID
            experiment_id: Optional experiment ID
            variant_id: Optional variant ID
            task_card_id: Optional task card ID
            harness_profile_id: Optional harness profile ID
            ttl_hours: Credential TTL in hours

        Returns:
            ProxyCredential with alias and metadata
        """
        # Generate a secure random key
        raw_key = secrets.token_urlsafe(32)

        # Create unique alias from session ID + random component
        # Format: bench-session-{short_hash}
        # This ensures each session gets a unique alias
        unique_component = secrets.token_hex(4)  # 8 hex chars
        key_alias = f"bench-session-{unique_component}"

        # Create virtual key ID (would be set by LiteLLM integration)
        # For now, derive deterministic ID from the raw key
        virtual_key_id = hashlib.sha256(raw_key.encode()).hexdigest()[:16]

        # Set expiration
        ttl = ttl_hours or self.settings.session_credential_ttl_hours
        expires_at = datetime.utcnow() + timedelta(hours=ttl)

        # Build correlation metadata
        metadata: dict[str, Any] = {
            "session_id": session_id,
            "benchmark_system": "stackperf",
            "created_at": datetime.utcnow().isoformat(),
        }

        if experiment_id:
            metadata["experiment_id"] = experiment_id
        if variant_id:
            metadata["variant_id"] = variant_id
        if task_card_id:
            metadata["task_card_id"] = task_card_id
        if harness_profile_id:
            metadata["harness_profile_id"] = harness_profile_id

        cred = ProxyCredential(
            key_alias=key_alias,
            virtual_key_id=virtual_key_id,
            created_at=datetime.utcnow(),
            expires_at=expires_at,
            metadata=metadata,
        )
        # Store raw_key as a private attribute
        object.__setattr__(cred, '_raw_key', raw_key)
        return cred

    def generate_api_key_value(self, credential: ProxyCredential) -> str:
        """Generate the actual API key value for the credential.

        This should only be called at credential creation time and
        the value should be shown to the operator exactly once.

        Args:
            credential: The proxy credential

        Returns:
            The API key value
        """
        # The raw key is attached during creation
        return getattr(credential, "_raw_key", "")


def build_credential_metadata(
    session_id: str,
    experiment_id: str | None = None,
    variant_id: str | None = None,
    task_card_id: str | None = None,
    harness_profile_id: str | None = None,
    **extra: Any,
) -> dict[str, Any]:
    """Build metadata for attaching to a proxy credential.

    Args:
        session_id: Benchmark session ID
        experiment_id: Optional experiment ID
        variant_id: Optional variant ID
        task_card_id: Optional task card ID
        harness_profile_id: Optional harness profile ID
        **extra: Additional metadata fields

    Returns:
        Metadata dict suitable for credential attachment
    """
    metadata: dict[str, Any] = {
        "session_id": session_id,
        "benchmark_system": "stackperf",
        "created_at": datetime.utcnow().isoformat(),
    }

    if experiment_id:
        metadata["experiment_id"] = experiment_id
    if variant_id:
        metadata["variant_id"] = variant_id
    if task_card_id:
        metadata["task_card_id"] = task_card_id
    if harness_profile_id:
        metadata["harness_profile_id"] = harness_profile_id

    metadata.update(extra)
    return metadata
