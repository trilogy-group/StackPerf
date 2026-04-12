"""Service for rendering harness-specific harness snippets from harness profiles.

This module provides rendering capabilities for benchmark sessions, supporting
shell, dotenv, JSON, and TOML outputs depending on how a harness is configured.
"""

import json
import re

from pydantic import BaseModel

from benchmark_core.config import HarnessProfile, RenderFormat, Variant


class RenderingError(Exception):
    """Raised when environment rendering fails."""

    pass


class ProfileValidationError(Exception):
    """Raised when harness profile validation fails."""

    pass


class EnvSnippet(BaseModel):
    """Rendered environment snippet result.

    Attributes:
        format: Output format (shell or dotenv).
        content: Rendered environment content.
        env_vars: Dictionary of environment variables (without secrets exposed).
        has_secrets: Whether any values contain sensitive credentials.
        source_profile: Name of the harness profile used.
        variant_name: Name of the variant (if overrides were applied).
    """

    format: RenderFormat
    content: str
    env_vars: dict[str, str]
    has_secrets: bool
    source_profile: str
    variant_name: str | None = None


class EnvRenderingService:
    """Service for rendering harness-specific environment snippets.

    This service handles:
    - Environment variable rendering from harness profiles
    - Variant override application (deterministic ordering)
    - Template substitution for model aliases
    - Shell and dotenv format generation
    - Secret protection (never write secrets to tracked files)

    The service ensures that rendered output:
    - Uses correct variable names for each harness profile
    - Includes variant overrides deterministically
    - Never writes secrets into tracked files (uses placeholders)
    """

    # Template pattern for {{ variable }} substitution
    TEMPLATE_PATTERN = re.compile(r"\{\{\s*(\w+)\s*\}\}")

    # Placeholder for secrets in tracked file output
    SECRET_PLACEHOLDER = "<SESSION_CREDENTIAL>"

    def __init__(self) -> None:
        """Initialize the rendering service."""
        pass

    def render_env_snippet(
        self,
        harness_profile: HarnessProfile,
        variant: Variant | None = None,
        credential: str | None = None,
        proxy_base_url: str = "http://localhost:4000",
        model_alias: str | None = None,
        format_override: RenderFormat | None = None,
        include_secrets: bool = False,
    ) -> EnvSnippet:
        """Render an environment snippet from a harness profile.

        Args:
            harness_profile: The harness profile configuration.
            variant: Optional variant with env overrides.
            credential: Session credential (API key). If None, placeholder is used.
            proxy_base_url: LiteLLM proxy base URL.
            model_alias: Model alias to use. Falls back to variant or profile default.
            format_override: Override the profile's render_format.
            include_secrets: Whether to include actual credential value.
                If False (default), uses placeholder to protect secrets.

        Returns:
            EnvSnippet with rendered content and metadata.

        Raises:
            RenderingError: If template substitution fails or required values missing.
        """
        # Determine model alias
        effective_model = model_alias
        if effective_model is None and variant:
            effective_model = variant.model_alias
        if effective_model is None:
            raise RenderingError("model_alias is required (not provided in variant or arguments)")

        # Determine output format
        output_format = format_override if format_override else harness_profile.render_format

        # Build environment variables from harness profile
        env_vars: dict[str, str] = {}

        # 1. Base URL
        env_vars[harness_profile.base_url_env] = proxy_base_url

        # 2. API Key (credential) - protect secrets by default
        if include_secrets and credential:
            env_vars[harness_profile.api_key_env] = credential
        else:
            env_vars[harness_profile.api_key_env] = self.SECRET_PLACEHOLDER

        # 3. Model
        env_vars[harness_profile.model_env] = effective_model

        # 4. Extra environment variables with template substitution
        for key, value in harness_profile.extra_env.items():
            substituted = self._substitute_template(value, {"model_alias": effective_model})
            env_vars[key] = substituted

        # 5. Apply variant overrides (deterministic ordering via sorted keys)
        if variant and variant.harness_env_overrides:
            for key in sorted(variant.harness_env_overrides.keys()):
                value = variant.harness_env_overrides[key]
                # Also apply template substitution to overrides
                substituted = self._substitute_template(value, {"model_alias": effective_model})
                env_vars[key] = substituted

        # Render in the requested format
        if output_format == "shell":
            content = self._render_shell(env_vars)
        elif output_format == "dotenv":
            content = self._render_dotenv(env_vars)
        elif output_format == "json":
            content = self._render_json(harness_profile.name, env_vars, effective_model)
        else:
            content = self._render_toml(harness_profile.name, env_vars, effective_model)

        return EnvSnippet(
            format=output_format,
            content=content,
            env_vars=env_vars,
            has_secrets=include_secrets and credential is not None,
            source_profile=harness_profile.name,
            variant_name=variant.name if variant else None,
        )

    def render_shell(
        self,
        harness_profile: HarnessProfile,
        variant: Variant | None = None,
        credential: str | None = None,
        proxy_base_url: str = "http://localhost:4000",
        model_alias: str | None = None,
        include_secrets: bool = False,
    ) -> str:
        """Render environment as shell export commands.

        This is a convenience method that returns just the content string.

        Args:
            harness_profile: The harness profile configuration.
            variant: Optional variant with env overrides.
            credential: Session credential (API key).
            proxy_base_url: LiteLLM proxy base URL.
            model_alias: Model alias to use.
            include_secrets: Whether to include actual credential value.

        Returns:
            Shell export commands string.
        """
        snippet = self.render_env_snippet(
            harness_profile=harness_profile,
            variant=variant,
            credential=credential,
            proxy_base_url=proxy_base_url,
            model_alias=model_alias,
            format_override="shell",
            include_secrets=include_secrets,
        )
        return snippet.content

    def render_dotenv(
        self,
        harness_profile: HarnessProfile,
        variant: Variant | None = None,
        credential: str | None = None,
        proxy_base_url: str = "http://localhost:4000",
        model_alias: str | None = None,
        include_secrets: bool = False,
    ) -> str:
        """Render environment as dotenv file content.

        This is a convenience method that returns just the content string.

        Args:
            harness_profile: The harness profile configuration.
            variant: Optional variant with env overrides.
            credential: Session credential (API key).
            proxy_base_url: LiteLLM proxy base URL.
            model_alias: Model alias to use.
            include_secrets: Whether to include actual credential value.

        Returns:
            Dotenv file content string.
        """
        snippet = self.render_env_snippet(
            harness_profile=harness_profile,
            variant=variant,
            credential=credential,
            proxy_base_url=proxy_base_url,
            model_alias=model_alias,
            format_override="dotenv",
            include_secrets=include_secrets,
        )
        return snippet.content

    def validate_profile(self, harness_profile: HarnessProfile) -> list[str]:
        """Validate a harness profile configuration.

        Checks:
        - Required environment variable names are present
        - Template syntax in extra_env is valid
        - No duplicate environment variable names

        Args:
            harness_profile: The harness profile to validate.

        Returns:
            List of validation warnings (empty if all checks pass).

        Raises:
            ProfileValidationError: If validation fails with errors.
        """
        errors: list[str] = []
        warnings: list[str] = []

        # Check required fields
        if not harness_profile.name:
            errors.append("profile name is required")
        if not harness_profile.base_url_env:
            errors.append("base_url_env is required")
        if not harness_profile.api_key_env:
            errors.append("api_key_env is required")
        if not harness_profile.model_env:
            errors.append("model_env is required")

        # Check for duplicate env var names
        all_env_names = [
            harness_profile.base_url_env,
            harness_profile.api_key_env,
            harness_profile.model_env,
        ] + list(harness_profile.extra_env.keys())

        seen: set[str] = set()
        for name in all_env_names:
            if name in seen:
                errors.append(f"duplicate environment variable name: {name}")
            seen.add(name)

        # Validate template syntax in extra_env
        for key, value in harness_profile.extra_env.items():
            matches = self.TEMPLATE_PATTERN.findall(value)
            for match in matches:
                if match != "model_alias":
                    warnings.append(
                        f"unknown template variable '{match}' in extra_env['{key}']; "
                        "only {{ model_alias }} is supported"
                    )

        # Check protocol surface
        valid_protocols = ["anthropic_messages", "openai_responses"]
        if harness_profile.protocol_surface not in valid_protocols:
            errors.append(
                f"invalid protocol_surface '{harness_profile.protocol_surface}'; "
                f"must be one of {valid_protocols}"
            )

        # Check render format
        valid_formats = ["shell", "dotenv", "json", "toml"]
        if harness_profile.render_format not in valid_formats:
            errors.append(
                f"invalid render_format '{harness_profile.render_format}'; "
                f"must be one of {valid_formats}"
            )

        if errors:
            raise ProfileValidationError("; ".join(errors))

        return warnings

    def validate_variant_profile_compatibility(
        self,
        variant: Variant,
        harness_profile: HarnessProfile,
    ) -> list[str]:
        """Validate that a variant is compatible with a harness profile.

        Checks:
        - Variant's harness_profile name matches
        - Variant overrides don't conflict with required profile vars

        Args:
            variant: The variant to validate.
            harness_profile: The harness profile to validate against.

        Returns:
            List of validation errors (empty if compatible).
        """
        errors: list[str] = []

        # Check profile name matches
        if variant.harness_profile != harness_profile.name:
            errors.append(
                f"variant harness_profile '{variant.harness_profile}' does not match "
                f"profile name '{harness_profile.name}'"
            )

        # Check overrides don't shadow required vars
        required_vars = {
            harness_profile.base_url_env,
            harness_profile.api_key_env,
            harness_profile.model_env,
        }
        for override_key in variant.harness_env_overrides:
            if override_key in required_vars:
                errors.append(
                    f"variant override '{override_key}' shadows required harness profile variable; "
                    "this may cause unexpected behavior"
                )

        return errors

    def _substitute_template(self, value: str, context: dict[str, str]) -> str:
        """Substitute template variables in a value.

        Args:
            value: String potentially containing {{ variable }} templates.
            context: Dictionary of variable names to values.

        Returns:
            String with templates substituted.

        Raises:
            RenderingError: If a template variable is not found in context.
        """

        def replace_match(match: re.Match) -> str:
            var_name = match.group(1)
            if var_name not in context:
                raise RenderingError(
                    f"template variable '{var_name}' not found in context; "
                    f"available: {list(context.keys())}"
                )
            return context[var_name]

        return self.TEMPLATE_PATTERN.sub(replace_match, value)

    def _render_shell(self, env_vars: dict[str, str]) -> str:
        """Render environment variables as shell export commands.

        Variables are sorted alphabetically for deterministic output.

        Args:
            env_vars: Dictionary of environment variables.

        Returns:
            Shell export commands string.
        """
        lines: list[str] = []
        # Sort keys for deterministic output
        for key in sorted(env_vars.keys()):
            value = env_vars[key]
            # Escape single quotes for shell safety
            escaped = value.replace("'", "'\\''")
            lines.append(f"export {key}='{escaped}'")
        return "\n".join(lines)

    def _render_dotenv(self, env_vars: dict[str, str]) -> str:
        """Render environment variables as dotenv file content.

        Variables are sorted alphabetically for deterministic output.

        Args:
            env_vars: Dictionary of environment variables.

        Returns:
            Dotenv file content string.
        """
        lines: list[str] = []
        # Sort keys for deterministic output
        for key in sorted(env_vars.keys()):
            value = env_vars[key]
            # Escape newlines first (dotenv doesn't support literal newlines)
            if "\n" in value:
                value = value.replace("\n", "\\n")
            # Quote values that need escaping
            if " " in value or "#" in value or "'" in value or '"' in value:
                # Escape backslashes and double quotes
                escaped = value.replace("\\", "\\\\").replace('"', '\\"')
                lines.append(f'{key}="{escaped}"')
            else:
                lines.append(f"{key}={value}")
        return "\n".join(lines)

    def _render_json(self, profile_name: str, env_vars: dict[str, str], model_alias: str) -> str:
        """Render harness configuration as JSON."""
        if profile_name != "opencode":
            raise RenderingError(f"json rendering is not supported for profile '{profile_name}'")

        config = {
            "$schema": "https://opencode.ai/config.json",
            "provider": {
                "stackperf": {
                    "npm": "@ai-sdk/openai-compatible",
                    "name": "StackPerf LiteLLM",
                    "options": {
                        "baseURL": env_vars["OPENAI_BASE_URL"],
                        "apiKey": env_vars["OPENAI_API_KEY"],
                    },
                    "models": {
                        model_alias: {
                            "name": model_alias,
                        }
                    },
                }
            },
            "model": f"stackperf/{model_alias}",
        }
        return json.dumps(config, indent=2)

    def _render_toml(self, profile_name: str, env_vars: dict[str, str], model_alias: str) -> str:
        """Render harness configuration as TOML."""
        if profile_name != "codex":
            raise RenderingError(f"toml rendering is not supported for profile '{profile_name}'")

        escaped_key = env_vars["OPENAI_API_KEY"].replace("'", "'\\''")
        lines = [
            f"# Export before starting Codex: export OPENAI_API_KEY='{escaped_key}'",
            f'model = "{model_alias}"',
            'model_provider = "stackperf"',
            "",
            "[model_providers.stackperf]",
            'name = "StackPerf LiteLLM"',
            f'base_url = "{env_vars["OPENAI_BASE_URL"]}"',
            'env_key = "OPENAI_API_KEY"',
        ]
        return "\n".join(lines)


def render_env_for_session(
    harness_profile: HarnessProfile,
    variant: Variant,
    credential: str | None = None,
    proxy_base_url: str = "http://localhost:4000",
    format_override: RenderFormat | None = None,
    include_secrets: bool = False,
) -> EnvSnippet:
    """Convenience function to render environment for a session.

    This is a module-level convenience function that creates a service
    instance and renders the environment snippet.

    Args:
        harness_profile: The harness profile configuration.
        variant: The variant with model alias and optional overrides.
        credential: Session credential (API key).
        proxy_base_url: LiteLLM proxy base URL.
        format_override: Override the profile's render_format.
        include_secrets: Whether to include actual credential value.

    Returns:
        EnvSnippet with rendered content.
    """
    service = EnvRenderingService()
    return service.render_env_snippet(
        harness_profile=harness_profile,
        variant=variant,
        credential=credential,
        proxy_base_url=proxy_base_url,
        format_override=format_override,
        include_secrets=include_secrets,
    )
