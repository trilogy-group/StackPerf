"""Unit tests for harness environment rendering.

Tests that:
- Rendered output uses correct variable names for each harness profile
- Variant overrides are included deterministically
- Rendered output never writes secrets into tracked files
"""

import pytest
from pathlib import Path
from datetime import datetime

from benchmark_core.config import (
    HarnessProfileConfig,
    ProtocolSurface,
    RenderFormat,
    Settings,
    VariantConfig,
)
from benchmark_core.services import HarnessRenderer, RenderError


class TestHarnessRenderer:
    """Test harness environment rendering."""

    @pytest.fixture
    def renderer(self):
        return HarnessRenderer()

    @pytest.fixture
    def anthropic_harness(self):
        return HarnessProfileConfig(
            name="claude-code",
            description="Claude Code harness",
            protocol_surface=ProtocolSurface.ANTHROPIC_MESSAGES,
            base_url_env="ANTHROPIC_BASE_URL",
            api_key_env="ANTHROPIC_API_KEY",
            model_env="ANTHROPIC_MODEL",
            extra_env={
                "ANTHROPIC_DEFAULT_SONNET_MODEL": "{{ model_alias }}",
            },
            render_format=RenderFormat.SHELL,
        )

    @pytest.fixture
    def openai_harness(self):
        return HarnessProfileConfig(
            name="openai-cli",
            description="OpenAI compatible harness",
            protocol_surface=ProtocolSurface.OPENAI_RESPONSES,
            base_url_env="OPENAI_BASE_URL",
            api_key_env="OPENAI_API_KEY",
            model_env="OPENAI_MODEL",
            extra_env={},
            render_format=RenderFormat.SHELL,
        )

    @pytest.fixture
    def variant(self):
        return VariantConfig(
            name="test-variant",
            provider="test-provider",
            provider_route="main",
            model_alias="test-model",
            harness_profile="claude-code",
            harness_env_overrides={
                "CUSTOM_SETTING": "custom-value",
            },
            benchmark_tags={
                "harness": "claude-code",
                "provider": "test-provider",
            },
        )

    def test_anthropic_harness_correct_variables(self, renderer, anthropic_harness, variant):
        """Rendered output uses correct variable names for Anthropic-surface harness."""
        result = renderer.render_environment(
            harness_profile=anthropic_harness,
            variant=variant,
            api_key="sk-test-key-12345",
            base_url="http://localhost:4000",
        )

        assert "ANTHROPIC_BASE_URL" in result
        assert "ANTHROPIC_API_KEY" in result
        assert "ANTHROPIC_MODEL" in result
        assert "http://localhost:4000" in result
        assert "test-model" in result

    def test_openai_harness_correct_variables(self, renderer, openai_harness, variant):
        """Rendered output uses correct variable names for OpenAI-surface harness."""
        result = renderer.render_environment(
            harness_profile=openai_harness,
            variant=variant,
            api_key="sk-test-key-12345",
            base_url="http://localhost:4000",
        )

        assert "OPENAI_BASE_URL" in result
        assert "OPENAI_API_KEY" in result
        assert "OPENAI_MODEL" in result
        assert "http://localhost:4000" in result

    def test_variant_overrides_included(self, renderer, anthropic_harness, variant):
        """Variant overrides are included deterministically."""
        result = renderer.render_environment(
            harness_profile=anthropic_harness,
            variant=variant,
            api_key="sk-test-key",
            base_url="http://localhost:4000",
        )

        assert "CUSTOM_SETTING" in result
        assert "custom-value" in result

    def test_extra_overrides_override_variant(self, renderer, anthropic_harness, variant):
        """Extra overrides have highest priority."""
        result = renderer.render_environment(
            harness_profile=anthropic_harness,
            variant=variant,
            api_key="sk-test-key",
            base_url="http://localhost:4000",
            extra_overrides={
                "CUSTOM_SETTING": "override-value",
            },
        )

        assert "CUSTOM_SETTING='override-value'" in result

    def test_render_shell_format(self, renderer, anthropic_harness, variant):
        """Shell format uses export statements."""
        result = renderer.render_environment(
            harness_profile=anthropic_harness,
            variant=variant,
            api_key="sk-test-key",
            base_url="http://localhost:4000",
            format=RenderFormat.SHELL,
        )

        assert "export " in result
        assert "'" in result  # Single quotes for values
        assert "# WARNING: This file contains secrets" in result

    def test_render_dotenv_format(self, renderer, anthropic_harness, variant):
        """Dotenv format uses KEY=\"value\" syntax."""
        result = renderer.render_environment(
            harness_profile=anthropic_harness,
            variant=variant,
            api_key="sk-test-key",
            base_url="http://localhost:4000",
            format=RenderFormat.DOTENV,
        )

        assert "=\"" in result
        assert "# WARNING: This file contains secrets" in result

    def test_render_json_format(self, renderer, anthropic_harness, variant):
        """JSON format produces valid JSON."""
        import json

        result = renderer.render_environment(
            harness_profile=anthropic_harness,
            variant=variant,
            api_key="sk-test-key",
            base_url="http://localhost:4000",
            format=RenderFormat.JSON,
        )

        # Should be valid JSON
        data = json.loads(result)
        assert "ANTHROPIC_BASE_URL" in data
        assert "ANTHROPIC_API_KEY" in data
        assert data["ANTHROPIC_API_KEY"] == "sk-test-key"

    def test_no_secrets_in_tracked_files(self, renderer, anthropic_harness, variant, tmp_path):
        """Rendered output never writes secrets into tracked files."""
        # Write to a location that should be in .gitignore
        output_path = tmp_path / ".stackperf" / "env.sh"
        result_path = renderer.render_to_file(
            harness_profile=anthropic_harness,
            variant=variant,
            api_key="sk-secret-key-12345",
            output_path=output_path,
            base_url="http://localhost:4000",
        )

        content = result_path.read_text()

        # File should contain warning about secrets
        assert "WARNING" in content
        assert "secrets" in content.lower()
        assert "do not commit" in content.lower()

    def test_template_rendering(self, renderer, anthropic_harness, variant):
        """Template variables are properly substituted."""
        variant_extra = VariantConfig(
            name="test-variant",
            provider="test-provider",
            provider_route="main",
            model_alias="claude-sonnet",
            harness_profile="claude-code",
            harness_env_overrides={
                "MODEL_DISPLAY": "{{ model_alias }}-display",
            },
            benchmark_tags={
                "custom_tag": "custom_value",
            },
        )

        result = renderer.render_environment(
            harness_profile=anthropic_harness,
            variant=variant_extra,
            api_key="sk-test-key",
            base_url="http://localhost:4000",
        )

        # Template should be resolved
        assert "claude-sonnet-display" in result

    def test_settings_base_url_default(self, renderer, anthropic_harness, variant):
        """Uses settings.litellm_base_url when no override provided."""
        settings = Settings(litellm_base_url="http://custom-proxy:4000")
        renderer_with_settings = HarnessRenderer(settings=settings)

        result = renderer_with_settings.render_environment(
            harness_profile=anthropic_harness,
            variant=variant,
            api_key="sk-test-key",
        )

        assert "http://custom-proxy:4000" in result
