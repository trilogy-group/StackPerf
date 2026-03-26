# COE-302: Evidence for Typed Config Schemas

## Summary
This document provides evidence that the typed config schemas and validation are working correctly, as requested in PR review.

## Config Loading Evidence

### Demo Script Execution

```bash
$ python scripts/demo_config_loading.py
```

**Output:**

```
============================================================
COE-302: Config Loading Evidence Demo
============================================================

1. Providers Loaded:
----------------------------------------
  • fireworks
    - protocol_surface: anthropic_messages
    - models: ['kimi-k2-5', 'glm-5']
  • openai
    - protocol_surface: openai_responses
    - models: ['gpt-4o', 'gpt-4o-mini']

2. Harness Profiles Loaded:
----------------------------------------
  • claude-code
    - protocol_surface: anthropic_messages
    - base_url_env: ANTHROPIC_BASE_URL
  • openai-cli
    - protocol_surface: openai_responses
    - base_url_env: OPENAI_BASE_URL

3. Variants Loaded:
----------------------------------------
  • fireworks-glm-5-claude-code
    - provider: fireworks
    - harness_profile: claude-code
    - model_alias: glm-5
  • fireworks-kimi-k2-5-claude-code
    - provider: fireworks
    - harness_profile: claude-code
    - model_alias: kimi-k2-5
  • openai-gpt-4o-cli
    - provider: openai
    - harness_profile: openai-cli
    - model_alias: gpt-4o

4. Experiments Loaded:
----------------------------------------
  • fireworks-terminal-agents-comparison
    - variants: ['fireworks-kimi-k2-5-claude-code', 'fireworks-glm-5-claude-code']

5. Task Cards Loaded:
----------------------------------------
  • repo-auth-analysis
    - goal: identify auth flow, trust boundaries, and risky ed...

6. Protocol Surface Coverage:
----------------------------------------
  Anthropic surfaces:
    - Providers: ['fireworks']
    - Harnesses: ['claude-code']
  OpenAI surfaces:
    - Providers: ['openai']
    - Harnesses: ['openai-cli']

============================================================
All configs loaded successfully!
============================================================
```

## Validation Error Evidence

### Demo Script Execution

```bash
$ python scripts/validation_demo.py
```

**Output:**

```
============================================================
COE-302: Validation Error Evidence Demo
============================================================

1. Provider with empty name:
----------------------------------------
  Field-level error: 1 validation error for ProviderConfig
name
  Value error, must not be empty or whitespace [type=value_error, input_value='', input_type=str]
    For further information visit https://errors.pydantic.dev/2.12/v/value_error

2. Variant with missing benchmark tags:
----------------------------------------
  Field-level error: 1 validation error for Variant
  Value error, benchmark_tags must include: harness, model, provider [type=value_error, input_value={'name': 'test', 'provide...', 'benchmark_tags': {}}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.12/v/value_error

3. Task card with negative timebox:
----------------------------------------
  Field-level error: 1 validation error for TaskCard
session_timebox_minutes
  Value error, session_timebox_minutes must be positive [type=value_error, input_value=-5, input_type=str]
    For further information visit https://errors.pydantic.dev/2.12/v/value_error

============================================================
All validation errors caught with precise field-level messages!
============================================================
```

## Test Results

```bash
$ make test
```

**Output:**

```
============================== 58 passed in 0.20s ==============================
```

## Acceptance Criteria Verification

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Invalid configs fail with precise field-level errors | ✅ PASS | See Validation Error Evidence above |
| Valid configs load into typed objects | ✅ PASS | See Config Loading Evidence above |
| Examples cover Anthropic-surface harness profile | ✅ PASS | claude-code.yaml (anthropic_messages) |
| Examples cover OpenAI-surface harness profile | ✅ PASS | openai-cli.yaml (openai_responses) |

---

**Generated:** 2026-03-26T12:00:00Z
