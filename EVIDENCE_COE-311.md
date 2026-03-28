# Evidence for COE-311: Render harness-specific environment snippets from harness profiles

## Implementation Summary

This ticket implements an environment rendering service that produces harness-specific
environment snippets from harness profiles, with support for shell and dotenv formats,
variant overrides, and secret protection.

## Deliverables Completed

### 1. Env Rendering Service (`src/benchmark_core/services/rendering.py`)

Core service with:
- `EnvRenderingService` class with full rendering capabilities
- `EnvSnippet` Pydantic model for rendered output
- `RenderingError` and `ProfileValidationError` exception classes
- `render_env_for_session()` convenience function

### 2. Shell and Dotenv Renderers

**Shell format:**
```bash
export ANTHROPIC_API_KEY='<SESSION_CREDENTIAL>'
export ANTHROPIC_BASE_URL='http://localhost:4000'
export ANTHROPIC_DEFAULT_HAIKU_MODEL='glm-5'
export ANTHROPIC_DEFAULT_OPUS_MODEL='glm-5'
export ANTHROPIC_DEFAULT_SONNET_MODEL='glm-5'
export ANTHROPIC_MODEL='glm-5'
export CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS='1'
export ANTHROPIC_TIMEOUT='120'
```

**Dotenv format:**
```env
ANTHROPIC_API_KEY=<SESSION_CREDENTIAL>
ANTHROPIC_BASE_URL=http://localhost:4000
ANTHROPIC_DEFAULT_HAIKU_MODEL=glm-5
...
```

### 3. Profile Validation Checks

- `validate_profile()` - Validates harness profile configuration
- `validate_variant_profile_compatibility()` - Checks variant-profile compatibility
- Duplicate env var detection
- Template syntax validation

### 4. CLI Commands (`src/cli/commands/render.py`)

```bash
# Render environment for a variant
benchmark render env --variant openai-gpt-4o-cli

# Render dotenv format
benchmark render env --variant fireworks-glm-5-claude-code --format dotenv

# Include actual credential value (for copy-paste to harness)
benchmark render env --variant my-variant --secrets --credential sk-xxx

# Validate a harness profile
benchmark render validate --profile claude-code

# List available profiles
benchmark render list-profiles

# Check variant-profile compatibility
benchmark render check-compatibility --variant openai-gpt-4o-cli
```

## Acceptance Criteria Verification

### ✅ Rendered output uses the correct variable names for each harness profile

**Evidence:**
- Uses `base_url_env`, `api_key_env`, `model_env` from profile config
- Includes all `extra_env` variables with template substitution

Example with `claude-code` profile:
```
ANTHROPIC_BASE_URL, ANTHROPIC_API_KEY, ANTHROPIC_MODEL
+ ANTHROPIC_DEFAULT_SONNET_MODEL, ANTHROPIC_DEFAULT_HAIKU_MODEL, ANTHROPIC_DEFAULT_OPUS_MODEL
```

Example with `openai-cli` profile:
```
OPENAI_BASE_URL, OPENAI_API_KEY, OPENAI_MODEL
```

### ✅ Variant overrides are included deterministically

**Evidence:**
- Variant `harness_env_overrides` applied after base profile vars
- Keys sorted alphabetically for reproducibility

Test case: `openai-gpt-4o-cli` variant has `OPENAI_TIMEOUT=120` override
Test case: `fireworks-glm-5-claude-code` has overrides for `CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS` and `ANTHROPIC_TIMEOUT`

### ✅ Rendered output never writes secrets into tracked files

**Evidence:**
- Default behavior uses `<SESSION_CREDENTIAL>` placeholder
- Must explicitly set `include_secrets=True` to expose secrets
- Clear warning displayed when secrets are exposed

Test cases:
- `test_default_protects_secrets` - Verifies placeholder is used
- `test_no_credential_uses_placeholder` - Verifies placeholder when no credential
- `test_env_vars_dict_has_placeholder` - Verifies placeholder in env_vars dict

## Test Results

### Unit Tests: 32/32 passing

```
tests/unit/test_rendering.py::TestEnvRenderingService::test_render_shell_format PASSED
tests/unit/test_rendering.py::TestEnvRenderingService::test_render_dotenv_format PASSED
tests/unit/test_rendering.py::TestEnvRenderingService::test_include_secrets_exposes_credential PASSED
tests/unit/test_rendering.py::TestEnvRenderingService::test_variant_overrides_applied PASSED
tests/unit/test_rendering.py::TestEnvRenderingService::test_deterministic_ordering PASSED
tests/unit/test_rendering.py::TestEnvRenderingService::test_template_substitution PASSED
tests/unit/test_rendering.py::TestEnvRenderingService::test_model_alias_from_variant PASSED
tests/unit/test_rendering.py::TestEnvRenderingService::test_missing_model_alias_raises_error PASSED
tests/unit/test_rendering.py::TestEnvRenderingService::test_unknown_template_variable_raises_error PASSED
tests/unit/test_rendering.py::TestEnvRenderingService::test_shell_convenience_method PASSED
tests/unit/test_rendering.py::TestEnvRenderingService::test_dotenv_convenience_method PASSED
tests/unit/test_rendering.py::TestProfileValidation::test_valid_profile_passes PASSED
tests/unit/test_rendering.py::TestProfileValidation::test_missing_name_fails PASSED
tests/unit/test_rendering.py::TestProfileValidation::test_missing_required_env_vars_fails PASSED
tests/unit/test_rendering.py::TestProfileValidation::test_duplicate_env_vars_fails PASSED
tests/unit/test_rendering.py::TestProfileValidation::test_invalid_protocol_surface_fails PASSED
tests/unit/test_rendering.py::TestProfileValidation::test_invalid_render_format_fails PASSED
tests/unit/test_rendering.py::TestProfileValidation::test_unknown_template_variable_warns PASSED
tests/unit/test_rendering.py::TestVariantProfileCompatibility::test_compatible_variant_passes PASSED
tests/unit/test_rendering.py::TestVariantProfileCompatibility::test_mismatched_profile_name_fails PASSED
tests/unit/test_rendering.py::TestVariantProfileCompatibility::test_override_shadows_required_var PASSED
tests/unit/test_rendering.py::TestShellRendering::test_escapes_single_quotes PASSED
tests/unit/test_rendering.py::TestShellRendering::test_handles_spaces PASSED
tests/unit/test_rendering.py::TestDotenvRendering::test_quotes_values_with_spaces PASSED
tests/unit/test_rendering.py::TestDotenvRendering::test_escapes_double_quotes PASSED
tests/unit/test_rendering.py::TestDotenvRendering::test_no_quotes_for_simple_values PASSED
tests/unit/test_rendering.py::TestModuleConvenienceFunction::test_render_env_for_session PASSED
tests/unit/test_rendering.py::TestSecretProtection::test_default_protects_secrets PASSED
tests/unit/test_rendering.py::TestSecretProtection::test_no_credential_uses_placeholder PASSED
tests/unit/test_rendering.py::TestSecretProtection::test_env_vars_dict_has_placeholder PASSED
tests/unit/test_rendering.py::TestEnvSnippetModel::test_snippet_metadata PASSED
tests/unit/test_rendering.py::TestEnvSnippetModel::test_snippet_without_variant PASSED
```

## CLI Demo

### Render environment for openai-gpt-4o-cli variant

```
$ benchmark render env --variant openai-gpt-4o-cli

Environment for variant: openai-gpt-4o-cli
  Harness Profile: openai-cli
  Model: gpt-4o
  Format: shell
  Variables: 4
  Secrets protected (use --secrets to expose)

export OPENAI_API_KEY='<SESSION_CREDENTIAL>'
export OPENAI_BASE_URL='http://localhost:4000'
export OPENAI_MODEL='gpt-4o'
export OPENAI_TIMEOUT='120'
```

### Validate a profile

```
$ benchmark render validate --profile claude-code

✓ Profile 'claude-code' is valid
  Protocol: anthropic_messages
  Format: shell
  Base URL env: ANTHROPIC_BASE_URL
  API key env: ANTHROPIC_API_KEY
  Model env: ANTHROPIC_MODEL
  Extra env vars: ANTHROPIC_DEFAULT_SONNET_MODEL, ANTHROPIC_DEFAULT_HAIKU_MODEL, ANTHROPIC_DEFAULT_OPUS_MODEL
```

### List profiles

```
$ benchmark render list-profiles

Harness Profiles (2):

  claude-code
    Protocol: anthropic_messages
    Format: shell
    Env vars: ANTHROPIC_BASE_URL, ANTHROPIC_API_KEY, ANTHROPIC_MODEL
    Extra: ANTHROPIC_DEFAULT_SONNET_MODEL, ANTHROPIC_DEFAULT_HAIKU_MODEL, ANTHROPIC_DEFAULT_OPUS_MODEL

  openai-cli
    Protocol: openai_responses
    Format: shell
    Env vars: OPENAI_BASE_URL, OPENAI_API_KEY, OPENAI_MODEL
```

### Check compatibility

```
$ benchmark render check-compatibility --variant openai-gpt-4o-cli

Variant: openai-gpt-4o-cli
  Provider: openai
  Model: gpt-4o
  Profile: openai-cli

✓ Variant and profile are compatible
  Overrides: 1
    - OPENAI_TIMEOUT=120
```

## Files Changed

### New Files
- `src/benchmark_core/services/rendering.py` - Env rendering service
- `src/cli/commands/render.py` - CLI commands for rendering
- `tests/unit/test_rendering.py` - 32 unit tests

### Modified Files
- `src/benchmark_core/services/__init__.py` - Export new rendering classes
- `src/benchmark_core/config_loader.py` - Added single-item loading methods
- `src/cli/main.py` - Register render CLI subcommand

## Code Quality

- ✅ All linting checks pass (ruff)
- ✅ Type checking passes for new modules (mypy)
- ✅ All 329 unit tests pass
- ✅ No secrets hardcoded in any file

## Blocker

**Linear MCP or `linear_graphql` tool is not available** - Cannot interact with Linear to:
- Update ticket status from Todo to In Progress
- Create workpad comments
- Link PR to issue

The implementation is complete and all acceptance criteria are verified through tests.