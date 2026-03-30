# Launch Recipes

## Purpose

This document provides detailed, step-by-step launch instructions for each supported harness profile. Use this as a reference when setting up a harness for a benchmark session.

## Recipe Structure

Each recipe includes:
1. **Prerequisites**: Required tools and configuration
2. **Environment Variables**: Variables that must be set
3. **Launch Steps**: Exact commands to run
4. **Verification**: How to confirm correct setup
5. **Common Issues**: Troubleshooting for that harness

## Supported Harness Profiles

- [Claude Code](#claude-code) - Anthropic's terminal agent
- [OpenAI CLI](#openai-cli) - OpenAI-compatible command-line interface

---

## Claude Code

### Overview

Claude Code is Anthropic's terminal-based agent that uses the Anthropic Messages API. It requires specific environment variables to route through the LiteLLM proxy.

### Prerequisites

- [ ] Claude Code installed: `which claude`
- [ ] Anthropic API key (for direct use) or benchmark session virtual key
- [ ] Session created with `harness_profile: claude-code`

### Environment Variables

| Variable | Purpose | Benchmark Value |
|----------|---------|-----------------|
| `ANTHROPIC_BASE_URL` | API endpoint | `http://localhost:4000` |
| `ANTHROPIC_API_KEY` | Authentication key | Session virtual key |
| `ANTHROPIC_MODEL` | Default model | Variant's model_alias |
| `ANTHROPIC_DEFAULT_SONNET_MODEL` | Sonnet model alias | Variant's model_alias |
| `ANTHROPIC_DEFAULT_HAIKU_MODEL` | Haiku model alias | Variant's model_alias |
| `ANTHROPIC_DEFAULT_OPUS_MODEL` | Opus model alias | Variant's model_alias |
| `CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS` | Beta features flag | Variant-specific |

### Step-by-Step Launch

#### 1. Create Session

```bash
bench session create \
  --experiment <experiment-name> \
  --variant <variant-name> \
  --task-card <task-card-name> \
  --harness claude-code \
  --label "claude-code-session"
```

Record the returned `session_id`.

#### 2. Render Environment

```bash
bench session env <session-id>
```

Example output (your values will differ):
```bash
export ANTHROPIC_BASE_URL="http://localhost:4000"
export ANTHROPIC_API_KEY="sk-benchmark-abc123..."
export ANTHROPIC_MODEL="kimi-k2-5"
export ANTHROPIC_DEFAULT_SONNET_MODEL="kimi-k2-5"
export ANTHROPIC_DEFAULT_HAIKU_MODEL="kimi-k2-5"
export ANTHROPIC_DEFAULT_OPUS_MODEL="kimi-k2-5"
export CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS="1"
```

#### 3. Apply Environment

**Option A: Copy-Paste**
```bash
# Copy each export line from the output and paste into your terminal
export ANTHROPIC_BASE_URL="http://localhost:4000"
export ANTHROPIC_API_KEY="sk-benchmark-abc123..."
# ... (other exports)
```

**Option B: Eval**
```bash
eval "$(bench session env <session-id>)"
```

#### 4. Verify Routing

Before launching, confirm the environment:

```bash
# Check base URL
echo $ANTHROPIC_BASE_URL
# Expected: http://localhost:4000

# Check API key is session key
echo $ANTHROPIC_API_KEY
# Expected: sk-benchmark-<session-id>

# Test the key
curl http://localhost:4000/key/info \
  -H "Authorization: Bearer $ANTHROPIC_API_KEY"
# Expected: JSON with key info including your session metadata
```

#### 5. Launch Claude Code

```bash
claude
```

Claude Code will now route all requests through the local LiteLLM proxy.

#### 6. Verify Proxy Traffic

After the first request, check that traffic is flowing through the proxy:

```bash
# Check LiteLLM logs
docker-compose logs litellm --tail 20

# Check Prometheus metrics
curl http://localhost:4000/metrics | grep litellm_request_total_latency_metric
```

### Harness Profile Config Reference

Claude Code harness profile (`configs/harnesses/claude-code.yaml`):

```yaml
name: claude-code
protocol_surface: anthropic_messages
base_url_env: ANTHROPIC_BASE_URL
api_key_env: ANTHROPIC_API_KEY
model_env: ANTHROPIC_MODEL
extra_env:
  ANTHROPIC_DEFAULT_SONNET_MODEL: "{{ model_alias }}"
  ANTHROPIC_DEFAULT_HAIKU_MODEL: "{{ model_alias }}"
  ANTHROPIC_DEFAULT_OPUS_MODEL: "{{ model_alias }}"
render_format: shell
launch_checks:
  - base URL points to local LiteLLM
  - session API key is present
```

### Variant Config Reference

Example variant for Claude Code (`configs/variants/fireworks-kimi-k2-5-claude-code.yaml`):

```yaml
name: fireworks-kimi-k2-5-claude-code
provider: fireworks
provider_route: fireworks-main
model_alias: kimi-k2-5
harness_profile: claude-code
harness_env_overrides:
  CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS: "1"
benchmark_tags:
  harness: claude-code
  provider: fireworks
  model: kimi-k2-5
  config: beta-off
```

### Common Issues

#### Issue: Claude Code Uses Direct Anthropic Endpoint

**Symptom**: Requests don't appear in LiteLLM logs.

**Cause**: Environment variables not applied or overridden by config file.

**Solution**:
```bash
# Check for config file
cat ~/.claude/config.json

# If it contains base_url, temporarily rename it
mv ~/.claude/config.json ~/.claude/config.json.backup

# Re-apply environment
eval "$(bench session env <session-id>)"

# Launch again
claude
```

#### Issue: Authentication Errors

**Symptom**: `401 Unauthorized` or `invalid_api_key`.

**Cause**: Session virtual key not set or expired.

**Solution**:
```bash
# Verify key is set
echo $ANTHROPIC_API_KEY

# If empty, re-apply environment
eval "$(bench session env <session-id>)"

# Test the key
curl http://localhost:4000/key/info \
  -H "Authorization: Bearer $ANTHROPIC_API_KEY"
```

#### Issue: Wrong Model

**Symptom**: Claude Code uses a different model than expected.

**Cause**: Model environment variables not set or variant mismatch.

**Solution**:
```bash
# Check model variables
echo $ANTHROPIC_MODEL
echo $ANTHROPIC_DEFAULT_SONNET_MODEL

# Verify variant config
cat configs/variants/<variant-name>.yaml | grep model_alias

# Re-apply environment
eval "$(bench session env <session-id>)"
```

---

## OpenAI CLI

### Overview

The OpenAI CLI (or any OpenAI-compatible CLI tool) uses the OpenAI Responses API format. It requires base URL, API key, and model to be set.

### Prerequisites

- [ ] OpenAI CLI or compatible tool installed
- [ ] OpenAI API key (for direct use) or benchmark session virtual key
- [ ] Session created with `harness_profile: openai-cli`

### Environment Variables

| Variable | Purpose | Benchmark Value |
|----------|---------|-----------------|
| `OPENAI_BASE_URL` | API endpoint | `http://localhost:4000` |
| `OPENAI_API_KEY` | Authentication key | Session virtual key |
| `OPENAI_MODEL` | Default model | Variant's model_alias |
| `OPENAI_TIMEOUT` | Request timeout | Variant-specific |

### Step-by-Step Launch

#### 1. Create Session

```bash
bench session create \
  --experiment <experiment-name> \
  --variant <variant-name> \
  --task-card <task-card-name> \
  --harness openai-cli \
  --label "openai-cli-session"
```

Record the returned `session_id`.

#### 2. Render Environment

```bash
bench session env <session-id>
```

Example output (your values will differ):
```bash
export OPENAI_BASE_URL="http://localhost:4000"
export OPENAI_API_KEY="sk-benchmark-def456..."
export OPENAI_MODEL="gpt-4o"
export OPENAI_TIMEOUT="120"
```

#### 3. Apply Environment

**Option A: Copy-Paste**
```bash
# Copy each export line from the output and paste into your terminal
export OPENAI_BASE_URL="http://localhost:4000"
export OPENAI_API_KEY="sk-benchmark-def456..."
# ... (other exports)
```

**Option B: Eval**
```bash
eval "$(bench session env <session-id>)"
```

#### 4. Verify Routing

Before launching, confirm the environment:

```bash
# Check base URL
echo $OPENAI_BASE_URL
# Expected: http://localhost:4000

# Check API key is session key
echo $OPENAI_API_KEY
# Expected: sk-benchmark-<session-id>

# Test the key
curl http://localhost:4000/key/info \
  -H "Authorization: Bearer $OPENAI_API_KEY"
# Expected: JSON with key info including your session metadata
```

#### 5. Launch OpenAI CLI

```bash
# For official OpenAI CLI
openai api chat.completions.create -m $OPENAI_MODEL

# For any OpenAI-compatible tool with environment variable support
your-tool --model $OPENAI_MODEL
```

The tool will now route all requests through the local LiteLLM proxy.

#### 6. Verify Proxy Traffic

After the first request, check that traffic is flowing through the proxy:

```bash
# Check LiteLLM logs
docker-compose logs litellm --tail 20

# Check Prometheus metrics
curl http://localhost:4000/metrics | grep litellm_request_total_latency_metric
```

### Harness Profile Config Reference

OpenAI CLI harness profile (`configs/harnesses/openai-cli.yaml`):

```yaml
name: openai-cli
protocol_surface: openai_responses
base_url_env: OPENAI_BASE_URL
api_key_env: OPENAI_API_KEY
model_env: OPENAI_MODEL
extra_env: {}
render_format: shell
launch_checks:
  - base URL points to local LiteLLM
  - session API key is present
```

### Variant Config Reference

Example variant for OpenAI CLI (`configs/variants/openai-gpt-4o-cli.yaml`):

```yaml
name: openai-gpt-4o-cli
provider: openai
provider_route: openai-main
model_alias: gpt-4o
harness_profile: openai-cli
harness_env_overrides: {}
benchmark_tags:
  harness: openai-cli
  provider: openai
  model: gpt-4o
  config: default
```

### Common Issues

#### Issue: Tool Uses Direct OpenAI Endpoint

**Symptom**: Requests don't appear in LiteLLM logs.

**Cause**: Environment variables not applied or tool has hardcoded base URL.

**Solution**:
```bash
# Check tool documentation for base URL configuration
# For tools that don't respect OPENAI_BASE_URL, use command-line flag

# Example for tools that support --base-url
your-tool --base-url http://localhost:4000 --api-key $OPENAI_API_KEY

# Or set in tool config file if supported
```

#### Issue: Authentication Errors

**Symptom**: `401 Unauthorized` or `invalid_api_key`.

**Cause**: Session virtual key not set or expired.

**Solution**:
```bash
# Verify key is set
echo $OPENAI_API_KEY

# If empty, re-apply environment
eval "$(bench session env <session-id>)"

# Test the key
curl http://localhost:4000/key/info \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

#### Issue: Model Not Found

**Symptom**: `model not found` error from LiteLLM.

**Cause**: Model alias doesn't match a configured route in LiteLLM.

**Solution**:
```bash
# Check LiteLLM config for available models
curl http://localhost:4000/models \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY"

# Verify variant's model_alias matches a LiteLLM model
cat configs/variants/<variant-name>.yaml | grep model_alias
```

---

## Generic OpenAI-Compatible Tools

Many tools support the OpenAI API format. The general pattern is:

### Environment Variable Pattern

Most tools respect:
- `OPENAI_BASE_URL` or `OPENAI_API_BASE`
- `OPENAI_API_KEY`
- `OPENAI_MODEL` or similar

### Command-Line Flag Pattern

Many tools accept:
- `--base-url` or `--api-base`
- `--api-key`
- `--model`

### Configuration File Pattern

Some tools use config files:
- `~/.config/<tool>/config.json`
- `~/.<tool>rc`
- `./.env` files

### Launch Steps

1. **Check tool documentation** for how to set base URL and API key
2. **Create session** with appropriate harness profile (or create a custom one)
3. **Render environment** with `bench session env`
4. **Apply via the tool's supported method** (env vars, flags, or config)
5. **Verify routing** through the proxy

---

## Creating Custom Harness Profiles

If your tool isn't covered by existing profiles, create a custom one.

### Profile Structure

Create `configs/harnesses/<your-tool>.yaml`:

```yaml
name: <your-tool>
protocol_surface: <anthropic_messages | openai_responses>
base_url_env: <ENV_VAR_FOR_BASE_URL>
api_key_env: <ENV_VAR_FOR_API_KEY>
model_env: <ENV_VAR_FOR_MODEL>
extra_env:
  <OPTIONAL_VAR_1>: "{{ template_var_1 }}"
  <OPTIONAL_VAR_2>: "{{ template_var_2 }}"
render_format: shell
launch_checks:
  - base URL points to local LiteLLM
  - session API key is present
```

### Protocol Surfaces

- `anthropic_messages`: For tools using Anthropic Messages API format
- `openai_responses`: For tools using OpenAI Chat Completions/Responses API format

### Template Variables

Available for use in `extra_env`:
- `{{ model_alias }}`: From variant's `model_alias` field
- Variant's `harness_env_overrides` are merged automatically

### Example Custom Profile

```yaml
name: custom-agent
protocol_surface: openai_responses
base_url_env: CUSTOM_AGENT_API_BASE
api_key_env: CUSTOM_AGENT_API_KEY
model_env: CUSTOM_AGENT_MODEL
extra_env:
  CUSTOM_AGENT_TIMEOUT: "120"
  CUSTOM_AGENT_LOG_LEVEL: "info"
render_format: shell
launch_checks:
  - base URL points to local LiteLLM
  - session API key is present
```

---

## Verification Checklist

Before starting any session, verify:

```bash
# 1. Infrastructure is healthy
docker-compose ps
curl http://localhost:4000/health

# 2. Session is created
bench session show <session-id>

# 3. Environment is applied
env | grep -E '(ANTHROPIC|OPENAI)_BASE_URL'
env | grep -E '(ANTHROPIC|OPENAI)_API_KEY'
env | grep -E '(ANTHROPIC|OPENAI)_MODEL'

# 4. Base URL is local proxy
echo $ANTHROPIC_BASE_URL  # Should be http://localhost:4000
echo $OPENAI_BASE_URL     # Should be http://localhost:4000

# 5. API key is session virtual key
echo $ANTHROPIC_API_KEY | grep sk-benchmark
echo $OPENAI_API_KEY | grep sk-benchmark

# 6. Virtual key is valid
curl http://localhost:4000/key/info \
  -H "Authorization: Bearer $ANTHROPIC_API_KEY"
```

---

## See Also

- [docs/operator-workflow.md](operator-workflow.md) - Complete session lifecycle guide
- [docs/config-and-contracts.md](config-and-contracts.md) - Config schema reference
- [configs/harnesses/](../configs/harnesses/) - Harness profile definitions
- [configs/variants/](../configs/variants/) - Variant configurations