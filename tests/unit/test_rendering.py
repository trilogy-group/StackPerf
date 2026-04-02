"""Unit tests for environment rendering service.

Tests for COE-311: Render harness-specific environment snippets from harness profiles.
"""

import pytest
from pydantic import ValidationError

from benchmark_core.config import HarnessProfile, Variant
from benchmark_core.services.rendering import (
    EnvRenderingService,
    EnvSnippet,
    ProfileValidationError,
    RenderingError,
    render_env_for_session,
)


@pytest.fixture
def rendering_service() -> EnvRenderingService:
    """Create a rendering service instance."""
    return EnvRenderingService()


@pytest.fixture
def claude_code_profile() -> HarnessProfile:
    """Create a claude-code harness profile for testing."""
    return HarnessProfile(
        name="claude-code",
        protocol_surface="anthropic_messages",
        base_url_env="ANTHROPIC_BASE_URL",
        api_key_env="ANTHROPIC_API_KEY",
        model_env="ANTHROPIC_MODEL",
        extra_env={
            "ANTHROPIC_DEFAULT_SONNET_MODEL": "{{ model_alias }}",
            "ANTHROPIC_DEFAULT_HAIKU_MODEL": "{{ model_alias }}",
            "ANTHROPIC_DEFAULT_OPUS_MODEL": "{{ model_alias }}",
        },
        render_format="shell",
        launch_checks=[
            "base URL points to local LiteLLM",
            "session API key is present",
        ],
    )


@pytest.fixture
def openai_cli_profile() -> HarnessProfile:
    """Create an openai-cli harness profile for testing."""
    return HarnessProfile(
        name="openai-cli",
        protocol_surface="openai_responses",
        base_url_env="OPENAI_BASE_URL",
        api_key_env="OPENAI_API_KEY",
        model_env="OPENAI_MODEL",
        extra_env={},
        render_format="shell",
        launch_checks=[
            "base URL points to local LiteLLM",
            "session API key is present",
        ],
    )


@pytest.fixture
def claude_code_variant() -> Variant:
    """Create a claude-code variant with overrides."""
    return Variant(
        name="fireworks-glm-5-claude-code",
        provider="fireworks",
        provider_route="fireworks-main",
        model_alias="glm-5",
        harness_profile="claude-code",
        harness_env_overrides={
            "CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS": "1",
            "ANTHROPIC_TIMEOUT": "120",
        },
        benchmark_tags={
            "harness": "claude-code",
            "provider": "fireworks",
            "model": "glm-5",
            "config": "beta-off",
        },
    )


@pytest.fixture
def openai_cli_variant() -> Variant:
    """Create an openai-cli variant with overrides."""
    return Variant(
        name="openai-gpt-4o-cli",
        provider="openai",
        provider_route="openai-main",
        model_alias="gpt-4o",
        harness_profile="openai-cli",
        harness_env_overrides={
            "OPENAI_TIMEOUT": "120",
        },
        benchmark_tags={
            "harness": "openai-cli",
            "provider": "openai",
            "model": "gpt-4o",
            "config": "default",
        },
    )


class TestEnvRenderingService:
    """Tests for EnvRenderingService."""

    def test_render_shell_format(
        self,
        rendering_service: EnvRenderingService,
        claude_code_profile: HarnessProfile,
        claude_code_variant: Variant,
    ) -> None:
        """Shell format produces valid export commands."""
        snippet = rendering_service.render_env_snippet(
            harness_profile=claude_code_profile,
            variant=claude_code_variant,
            credential="sk-test-key-123",
            proxy_base_url="http://localhost:4000",
            include_secrets=False,
        )

        assert snippet.format == "shell"
        assert "export ANTHROPIC_BASE_URL=" in snippet.content
        assert "export ANTHROPIC_API_KEY=" in snippet.content
        assert "export ANTHROPIC_MODEL=" in snippet.content
        # Should not expose the actual credential
        assert "sk-test-key-123" not in snippet.content
        assert "<SESSION_CREDENTIAL>" in snippet.content

    def test_render_dotenv_format(
        self,
        rendering_service: EnvRenderingService,
        openai_cli_profile: HarnessProfile,
        openai_cli_variant: Variant,
    ) -> None:
        """Dotenv format produces valid KEY=value lines."""
        snippet = rendering_service.render_env_snippet(
            harness_profile=openai_cli_profile,
            variant=openai_cli_variant,
            credential="sk-test-key-456",
            proxy_base_url="http://localhost:4000",
            format_override="dotenv",
            include_secrets=False,
        )

        assert snippet.format == "dotenv"
        assert "OPENAI_BASE_URL=" in snippet.content
        assert "OPENAI_API_KEY=" in snippet.content
        assert "OPENAI_MODEL=" in snippet.content
        # Should not expose the actual credential
        assert "sk-test-key-456" not in snippet.content

    def test_include_secrets_exposes_credential(
        self,
        rendering_service: EnvRenderingService,
        claude_code_profile: HarnessProfile,
        claude_code_variant: Variant,
    ) -> None:
        """When include_secrets=True, credential is exposed."""
        snippet = rendering_service.render_env_snippet(
            harness_profile=claude_code_profile,
            variant=claude_code_variant,
            credential="sk-secret-key-789",
            proxy_base_url="http://localhost:4000",
            include_secrets=True,
        )

        assert snippet.has_secrets is True
        assert "sk-secret-key-789" in snippet.content
        assert "<SESSION_CREDENTIAL>" not in snippet.content

    def test_variant_overrides_applied(
        self,
        rendering_service: EnvRenderingService,
        claude_code_profile: HarnessProfile,
        claude_code_variant: Variant,
    ) -> None:
        """Variant env overrides are included in output."""
        snippet = rendering_service.render_env_snippet(
            harness_profile=claude_code_profile,
            variant=claude_code_variant,
            proxy_base_url="http://localhost:4000",
            include_secrets=False,
        )

        # Check variant overrides are present
        assert "CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS" in snippet.content
        assert "ANTHROPIC_TIMEOUT" in snippet.content
        assert snippet.env_vars["CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS"] == "1"
        assert snippet.env_vars["ANTHROPIC_TIMEOUT"] == "120"

    def test_deterministic_ordering(
        self,
        rendering_service: EnvRenderingService,
        claude_code_profile: HarnessProfile,
        claude_code_variant: Variant,
    ) -> None:
        """Environment variables are sorted alphabetically."""
        snippet = rendering_service.render_env_snippet(
            harness_profile=claude_code_profile,
            variant=claude_code_variant,
            proxy_base_url="http://localhost:4000",
            include_secrets=False,
        )

        # Extract variable names from output
        lines = snippet.content.split("\n")
        var_names = [line.split("=")[0].replace("export ", "") for line in lines if "=" in line]

        # Should be sorted alphabetically
        assert var_names == sorted(var_names)

    def test_template_substitution(
        self,
        rendering_service: EnvRenderingService,
        claude_code_profile: HarnessProfile,
    ) -> None:
        """Template variables {{ model_alias }} are substituted."""
        snippet = rendering_service.render_env_snippet(
            harness_profile=claude_code_profile,
            model_alias="claude-sonnet-4",
            proxy_base_url="http://localhost:4000",
            include_secrets=False,
        )

        # Check template substitution happened
        assert snippet.env_vars["ANTHROPIC_DEFAULT_SONNET_MODEL"] == "claude-sonnet-4"
        assert snippet.env_vars["ANTHROPIC_DEFAULT_HAIKU_MODEL"] == "claude-sonnet-4"
        assert "{{ model_alias }}" not in snippet.content

    def test_model_alias_from_variant(
        self,
        rendering_service: EnvRenderingService,
        claude_code_profile: HarnessProfile,
        claude_code_variant: Variant,
    ) -> None:
        """Model alias is taken from variant if not specified."""
        snippet = rendering_service.render_env_snippet(
            harness_profile=claude_code_profile,
            variant=claude_code_variant,
            proxy_base_url="http://localhost:4000",
            include_secrets=False,
        )

        # Should use variant's model_alias
        assert snippet.env_vars["ANTHROPIC_MODEL"] == "glm-5"
        assert snippet.env_vars["ANTHROPIC_DEFAULT_SONNET_MODEL"] == "glm-5"

    def test_missing_model_alias_raises_error(
        self,
        rendering_service: EnvRenderingService,
        claude_code_profile: HarnessProfile,
    ) -> None:
        """Missing model_alias raises RenderingError."""
        with pytest.raises(RenderingError, match="model_alias is required"):
            rendering_service.render_env_snippet(
                harness_profile=claude_code_profile,
                proxy_base_url="http://localhost:4000",
            )

    def test_unknown_template_variable_raises_error(
        self,
        rendering_service: EnvRenderingService,
    ) -> None:
        """Unknown template variable raises RenderingError."""
        profile = HarnessProfile(
            name="test-profile",
            protocol_surface="openai_responses",
            base_url_env="TEST_BASE_URL",
            api_key_env="TEST_API_KEY",
            model_env="TEST_MODEL",
            extra_env={
                "TEST_VAR": "{{ unknown_var }}",
            },
        )

        with pytest.raises(RenderingError, match="template variable 'unknown_var' not found"):
            rendering_service.render_env_snippet(
                harness_profile=profile,
                model_alias="test-model",
                proxy_base_url="http://localhost:4000",
            )

    def test_shell_convenience_method(
        self,
        rendering_service: EnvRenderingService,
        openai_cli_profile: HarnessProfile,
        openai_cli_variant: Variant,
    ) -> None:
        """render_shell method returns content string."""
        content = rendering_service.render_shell(
            harness_profile=openai_cli_profile,
            variant=openai_cli_variant,
            credential="sk-test",
            proxy_base_url="http://localhost:4000",
            include_secrets=False,
        )

        assert isinstance(content, str)
        assert "export OPENAI_BASE_URL=" in content
        assert "export OPENAI_MODEL=" in content

    def test_dotenv_convenience_method(
        self,
        rendering_service: EnvRenderingService,
        openai_cli_profile: HarnessProfile,
        openai_cli_variant: Variant,
    ) -> None:
        """render_dotenv method returns content string."""
        content = rendering_service.render_dotenv(
            harness_profile=openai_cli_profile,
            variant=openai_cli_variant,
            credential="sk-test",
            proxy_base_url="http://localhost:4000",
            include_secrets=False,
        )

        assert isinstance(content, str)
        assert "OPENAI_BASE_URL=" in content
        assert "OPENAI_MODEL=" in content


class TestProfileValidation:
    """Tests for harness profile validation."""

    def test_valid_profile_passes(
        self,
        rendering_service: EnvRenderingService,
        claude_code_profile: HarnessProfile,
    ) -> None:
        """Valid profile passes validation."""
        warnings = rendering_service.validate_profile(claude_code_profile)
        assert warnings == []

    def test_missing_name_fails(
        self,
        rendering_service: EnvRenderingService,
    ) -> None:
        """Profile without name fails validation at Pydantic level."""
        # Pydantic validates this at model construction time
        with pytest.raises(ValidationError):
            HarnessProfile(
                name="",  # Empty name
                protocol_surface="openai_responses",
                base_url_env="TEST_BASE_URL",
                api_key_env="TEST_API_KEY",
                model_env="TEST_MODEL",
            )

    def test_missing_required_env_vars_fails(
        self,
        rendering_service: EnvRenderingService,
    ) -> None:
        """Profile without required env vars fails validation at Pydantic level."""
        # Pydantic validates this at model construction time
        with pytest.raises(ValidationError):
            HarnessProfile(
                name="test-profile",
                protocol_surface="openai_responses",
                base_url_env="",
                api_key_env="",
                model_env="",
            )

    def test_duplicate_env_vars_fails(
        self,
        rendering_service: EnvRenderingService,
    ) -> None:
        """Profile with duplicate env var names fails validation."""
        profile = HarnessProfile(
            name="test-profile",
            protocol_surface="openai_responses",
            base_url_env="TEST_VAR",
            api_key_env="TEST_VAR",  # Duplicate!
            model_env="TEST_MODEL",
        )

        with pytest.raises(ProfileValidationError, match="duplicate environment variable name"):
            rendering_service.validate_profile(profile)

    def test_invalid_protocol_surface_fails(
        self,
        rendering_service: EnvRenderingService,
    ) -> None:
        """Profile with invalid protocol surface fails at Pydantic level."""
        # Pydantic validates Literal types at model construction time
        with pytest.raises(ValidationError):
            HarnessProfile(
                name="test-profile",
                protocol_surface="invalid_protocol",  # type: ignore
                base_url_env="TEST_BASE_URL",
                api_key_env="TEST_API_KEY",
                model_env="TEST_MODEL",
            )

    def test_invalid_render_format_fails(
        self,
        rendering_service: EnvRenderingService,
    ) -> None:
        """Profile with invalid render format fails at Pydantic level."""
        # Pydantic validates Literal types at model construction time
        with pytest.raises(ValidationError):
            HarnessProfile(
                name="test-profile",
                protocol_surface="openai_responses",
                base_url_env="TEST_BASE_URL",
                api_key_env="TEST_API_KEY",
                model_env="TEST_MODEL",
                render_format="invalid_format",  # type: ignore
            )

    def test_unknown_template_variable_warns(
        self,
        rendering_service: EnvRenderingService,
    ) -> None:
        """Unknown template variable in extra_env produces warning."""
        profile = HarnessProfile(
            name="test-profile",
            protocol_surface="openai_responses",
            base_url_env="TEST_BASE_URL",
            api_key_env="TEST_API_KEY",
            model_env="TEST_MODEL",
            extra_env={
                "TEST_VAR": "{{ unknown_template }}",
            },
        )

        # Should not raise, but return warnings
        warnings = rendering_service.validate_profile(profile)
        assert len(warnings) == 1
        assert "unknown template variable" in warnings[0].lower()


class TestVariantProfileCompatibility:
    """Tests for variant and profile compatibility validation."""

    def test_compatible_variant_passes(
        self,
        rendering_service: EnvRenderingService,
        claude_code_profile: HarnessProfile,
        claude_code_variant: Variant,
    ) -> None:
        """Compatible variant and profile pass validation."""
        errors = rendering_service.validate_variant_profile_compatibility(
            variant=claude_code_variant,
            harness_profile=claude_code_profile,
        )
        assert errors == []

    def test_mismatched_profile_name_fails(
        self,
        rendering_service: EnvRenderingService,
        claude_code_profile: HarnessProfile,
        openai_cli_variant: Variant,
    ) -> None:
        """Variant with wrong profile name fails validation."""
        errors = rendering_service.validate_variant_profile_compatibility(
            variant=openai_cli_variant,
            harness_profile=claude_code_profile,
        )
        assert len(errors) == 1
        assert "does not match" in errors[0]

    def test_override_shadows_required_var(
        self,
        rendering_service: EnvRenderingService,
    ) -> None:
        """Variant override that shadows required var produces error."""
        profile = HarnessProfile(
            name="test-profile",
            protocol_surface="openai_responses",
            base_url_env="BASE_URL",
            api_key_env="API_KEY",
            model_env="MODEL",
        )

        variant = Variant(
            name="test-variant",
            provider="test",
            model_alias="test-model",
            harness_profile="test-profile",
            harness_env_overrides={
                "BASE_URL": "http://override",  # Shadows required var!
            },
            benchmark_tags={"harness": "test", "provider": "test", "model": "test"},
        )

        errors = rendering_service.validate_variant_profile_compatibility(
            variant=variant,
            harness_profile=profile,
        )
        assert len(errors) == 1
        assert "shadows required harness profile variable" in errors[0]


class TestShellRendering:
    """Tests for shell format rendering."""

    def test_escapes_single_quotes(
        self,
        rendering_service: EnvRenderingService,
    ) -> None:
        """Shell format escapes single quotes in values."""
        profile = HarnessProfile(
            name="test-profile",
            protocol_surface="openai_responses",
            base_url_env="TEST_BASE_URL",
            api_key_env="TEST_API_KEY",
            model_env="TEST_MODEL",
            extra_env={
                "TEST_VAR": "value'with'quotes",
            },
        )

        snippet = rendering_service.render_env_snippet(
            harness_profile=profile,
            model_alias="test-model",
            proxy_base_url="http://localhost:4000",
            include_secrets=False,
        )

        # Should escape single quotes
        assert "'\\''" in snippet.content or "'\"'\"'" in snippet.content

    def test_handles_spaces(
        self,
        rendering_service: EnvRenderingService,
    ) -> None:
        """Shell format handles values with spaces."""
        profile = HarnessProfile(
            name="test-profile",
            protocol_surface="openai_responses",
            base_url_env="TEST_BASE_URL",
            api_key_env="TEST_API_KEY",
            model_env="TEST_MODEL",
            extra_env={
                "TEST_VAR": "value with spaces",
            },
        )

        snippet = rendering_service.render_env_snippet(
            harness_profile=profile,
            model_alias="test-model",
            proxy_base_url="http://localhost:4000",
            include_secrets=False,
        )

        # Should quote the value
        assert "export TEST_VAR='value with spaces'" in snippet.content


class TestDotenvRendering:
    """Tests for dotenv format rendering."""

    def test_quotes_values_with_spaces(
        self,
        rendering_service: EnvRenderingService,
    ) -> None:
        """Dotenv format quotes values with spaces."""
        profile = HarnessProfile(
            name="test-profile",
            protocol_surface="openai_responses",
            base_url_env="TEST_BASE_URL",
            api_key_env="TEST_API_KEY",
            model_env="TEST_MODEL",
            extra_env={
                "TEST_VAR": "value with spaces",
            },
        )

        snippet = rendering_service.render_env_snippet(
            harness_profile=profile,
            model_alias="test-model",
            proxy_base_url="http://localhost:4000",
            format_override="dotenv",
            include_secrets=False,
        )

        # Should quote the value
        assert 'TEST_VAR="value with spaces"' in snippet.content

    def test_escapes_double_quotes(
        self,
        rendering_service: EnvRenderingService,
    ) -> None:
        """Dotenv format escapes double quotes in values."""
        profile = HarnessProfile(
            name="test-profile",
            protocol_surface="openai_responses",
            base_url_env="TEST_BASE_URL",
            api_key_env="TEST_API_KEY",
            model_env="TEST_MODEL",
            extra_env={
                "TEST_VAR": 'value"with"quotes',
            },
        )

        snippet = rendering_service.render_env_snippet(
            harness_profile=profile,
            model_alias="test-model",
            proxy_base_url="http://localhost:4000",
            format_override="dotenv",
            include_secrets=False,
        )

        # Should escape double quotes
        assert '\\"' in snippet.content

    def test_no_quotes_for_simple_values(
        self,
        rendering_service: EnvRenderingService,
    ) -> None:
        """Dotenv format doesn't quote simple values."""
        profile = HarnessProfile(
            name="test-profile",
            protocol_surface="openai_responses",
            base_url_env="TEST_BASE_URL",
            api_key_env="TEST_API_KEY",
            model_env="TEST_MODEL",
            extra_env={
                "TEST_VAR": "simple_value",
            },
        )

        snippet = rendering_service.render_env_snippet(
            harness_profile=profile,
            model_alias="test-model",
            proxy_base_url="http://localhost:4000",
            format_override="dotenv",
            include_secrets=False,
        )

        # Should not quote simple value
        assert "TEST_VAR=simple_value" in snippet.content

    def test_escapes_newlines(
        self,
        rendering_service: EnvRenderingService,
    ) -> None:
        """Dotenv format escapes newlines in values."""
        profile = HarnessProfile(
            name="test-profile",
            protocol_surface="openai_responses",
            base_url_env="TEST_BASE_URL",
            api_key_env="TEST_API_KEY",
            model_env="TEST_MODEL",
            extra_env={
                "TEST_VAR": "line1\nline2",
            },
        )

        snippet = rendering_service.render_env_snippet(
            harness_profile=profile,
            model_alias="test-model",
            proxy_base_url="http://localhost:4000",
            format_override="dotenv",
            include_secrets=False,
        )

        # Should escape newlines as \n (not literal newlines)
        assert "line1\\nline2" in snippet.content
        # Should not contain literal newline in the value
        lines = snippet.content.split("\n")
        # Each env var should be on a single line
        for line in lines:
            if line.startswith("TEST_VAR="):
                assert "\n" not in line.split("=", 1)[1]


class TestModuleConvenienceFunction:
    """Tests for module-level convenience function."""

    def test_render_env_for_session(
        self,
        claude_code_profile: HarnessProfile,
        claude_code_variant: Variant,
    ) -> None:
        """Module-level function works correctly."""
        snippet = render_env_for_session(
            harness_profile=claude_code_profile,
            variant=claude_code_variant,
            credential="sk-test-key",
            proxy_base_url="http://localhost:4000",
            include_secrets=False,
        )

        assert isinstance(snippet, EnvSnippet)
        assert snippet.source_profile == "claude-code"
        assert snippet.variant_name == "fireworks-glm-5-claude-code"
        assert snippet.has_secrets is False


class TestSecretProtection:
    """Tests for secret protection in rendered output."""

    def test_default_protects_secrets(
        self,
        rendering_service: EnvRenderingService,
        claude_code_profile: HarnessProfile,
        claude_code_variant: Variant,
    ) -> None:
        """By default, secrets are not exposed in output."""
        secret_credential = "sk-super-secret-key-12345"

        snippet = rendering_service.render_env_snippet(
            harness_profile=claude_code_profile,
            variant=claude_code_variant,
            credential=secret_credential,
            proxy_base_url="http://localhost:4000",
            include_secrets=False,  # Default
        )

        assert secret_credential not in snippet.content
        assert secret_credential not in str(snippet.env_vars)
        assert "<SESSION_CREDENTIAL>" in snippet.content
        assert snippet.has_secrets is False

    def test_no_credential_uses_placeholder(
        self,
        rendering_service: EnvRenderingService,
        claude_code_profile: HarnessProfile,
        claude_code_variant: Variant,
    ) -> None:
        """When no credential provided, placeholder is used."""
        snippet = rendering_service.render_env_snippet(
            harness_profile=claude_code_profile,
            variant=claude_code_variant,
            credential=None,
            proxy_base_url="http://localhost:4000",
            include_secrets=False,
        )

        assert "<SESSION_CREDENTIAL>" in snippet.content
        assert snippet.has_secrets is False

    def test_env_vars_dict_has_placeholder(
        self,
        rendering_service: EnvRenderingService,
        claude_code_profile: HarnessProfile,
    ) -> None:
        """The env_vars dict has placeholder for credential."""
        snippet = rendering_service.render_env_snippet(
            harness_profile=claude_code_profile,
            model_alias="test-model",
            credential="sk-secret",
            proxy_base_url="http://localhost:4000",
            include_secrets=False,
        )

        # env_vars should have placeholder, not secret
        assert snippet.env_vars["ANTHROPIC_API_KEY"] == "<SESSION_CREDENTIAL>"


class TestEnvSnippetModel:
    """Tests for EnvSnippet model."""

    def test_snippet_metadata(
        self,
        rendering_service: EnvRenderingService,
        claude_code_profile: HarnessProfile,
        claude_code_variant: Variant,
    ) -> None:
        """EnvSnippet has correct metadata."""
        snippet = rendering_service.render_env_snippet(
            harness_profile=claude_code_profile,
            variant=claude_code_variant,
            proxy_base_url="http://localhost:4000",
            include_secrets=False,
        )

        assert snippet.source_profile == "claude-code"
        assert snippet.variant_name == "fireworks-glm-5-claude-code"
        assert snippet.format == "shell"

    def test_snippet_without_variant(
        self,
        rendering_service: EnvRenderingService,
        claude_code_profile: HarnessProfile,
    ) -> None:
        """EnvSnippet works without variant."""
        snippet = rendering_service.render_env_snippet(
            harness_profile=claude_code_profile,
            model_alias="test-model",
            proxy_base_url="http://localhost:4000",
            include_secrets=False,
        )

        assert snippet.source_profile == "claude-code"
        assert snippet.variant_name is None
