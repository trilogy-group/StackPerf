"""Shared utilities for benchmark core services.

Provides common helper functions used across multiple service classes
to avoid duplication and ensure consistent behavior.
"""

import warnings


def validate_litellm_url(litellm_base_url: str, enforce_https: bool = True) -> str:
    """Validate and normalize a LiteLLM base URL.

    Strips trailing slashes and optionally enforces HTTPS in
    production environments.

    Args:
        litellm_base_url: The raw base URL for the LiteLLM proxy API.
        enforce_https: Whether to require HTTPS. Defaults to True.

    Returns:
        The normalized URL with trailing slash removed.

    Raises:
        ValueError: If HTTPS is required but the URL is not localhost
            and does not start with ``https://``.
    """
    normalized = litellm_base_url.rstrip("/")
    if enforce_https and not normalized.startswith(
        ("https://", "http://localhost", "http://127.0.0.1")
    ):
        raise ValueError(
            f"LiteLLM URL must use HTTPS in production environments. Got: {litellm_base_url}"
        )
    return normalized


def render_env_shell(env_vars: dict[str, str]) -> str:
    """Render environment variables as shell export commands.

    Variables are sorted alphabetically for deterministic output.

    Args:
        env_vars: Dictionary of environment variables.

    Returns:
        Shell export commands string.
    """
    lines: list[str] = []
    for key in sorted(env_vars.keys()):
        value = env_vars[key]
        escaped = value.replace("'", "'\\''")
        lines.append(f"export {key}='{escaped}'")
    return "\n".join(lines)


def render_env_dotenv(env_vars: dict[str, str]) -> str:
    """Render environment variables as dotenv file content.

    Variables are sorted alphabetically for deterministic output.

    Args:
        env_vars: Dictionary of environment variables.

    Returns:
        Dotenv file content string.
    """
    lines: list[str] = []
    for key in sorted(env_vars.keys()):
        value = env_vars[key]
        if " " in value or "#" in value or "'" in value or '"' in value:
            escaped = value.replace("\\", "\\\\").replace('"', '\\"')
            lines.append(f'{key}="{escaped}"')
        else:
            lines.append(f"{key}={value}")
    return "\n".join(lines)


def warn_revoke_failure(source: str, litellm_key_id: str | None, exc: Exception) -> None:
    """Warn when a LiteLLM key revocation attempt fails.

    This helper centralises the warning issued when a best-effort LiteLLM
    delete call fails, so both :class:`CredentialService` and
    :class:`ProxyKeyService` behave consistently.

    Args:
        source: Human-readable source of the revocation (e.g. ``credential``
            or ``proxy_key``).
        litellm_key_id: The LiteLLM key ID that could not be deleted.
        exc: The original exception that caused the failure.
    """
    warnings.warn(
        f"LiteLLM delete failed for {source} (key_id={litellm_key_id}): {exc}. "
        "Local metadata has been marked revoked but the proxy key may still be active.",
        stacklevel=3,
    )
