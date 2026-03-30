# LiteLLM Proxy Configuration

This directory contains LiteLLM proxy configurations that match the benchmark provider and model configurations.

## Route Naming Convention

LiteLLM routes follow the benchmark provider config naming to ensure correlation between benchmark configs and proxy routing.

### Route Names

| Route Name | Provider | Protocol Surface | Config File |
|:-----------|:---------|:---------------|:------------|
| `fireworks-main` | Fireworks AI | `anthropic_messages` | `configs/providers/fireworks.yaml` |
| `openai-main` | OpenAI | `openai_responses` | `configs/providers/openai.yaml` |
| `anthropic-main` | Anthropic | `anthropic_messages` | inline in `configs/litellm/config.yaml` |

### Model Aliases

Model aliases in LiteLLM match the benchmark provider configs exactly:

| Alias | Provider | Upstream Model |
|:------|:---------|:---------------|
| `kimi-k2-5` | Fireworks | `accounts/fireworks/models/kimi-k2p5` |
| `glm-5` | Fireworks | `accounts/fireworks/models/glm-5` |
| `kimi-k2-5-turbo` | Fireworks | `accounts/fireworks/routers/kimi-k2p5-turbo` |
| `glm-5-fast` | Fireworks | `accounts/fireworks/routers/glm-5-fast` |
| `gpt-5.4` | OpenAI | `gpt-5.4` |
| `gpt-5.4-mini` | OpenAI | `gpt-5.4-mini` |
| `claude-opus-4-6` | Anthropic | `claude-opus-4-6` |
| `claude-sonnet-4-6` | Anthropic | `claude-sonnet-4-6` |

## Configuration Files

- `litellm.yaml` - Main proxy configuration with model routes, virtual keys, and callbacks
- `README.md` - This documentation

## Environment Variables

The LiteLLM configuration uses the following environment variables:

### Required

- `LITELLM_MASTER_KEY` - Master API key for the LiteLLM proxy
- `LITELLM_DATABASE_URL` - PostgreSQL connection string for LiteLLM metadata
- `FIREWORKS_API_KEY` - API key for Fireworks AI provider
- `OPENAI_API_KEY` - API key for OpenAI provider
- `ANTHROPIC_API_KEY` - API key for Anthropic provider

### Optional

- `FIREWORKS_BASE_URL` - Custom Fireworks endpoint (defaults to `https://api.fireworks.ai/inference/v1`)
- `OPENAI_BASE_URL` - Custom OpenAI endpoint (defaults to `https://api.openai.com/v1`)
- `ANTHROPIC_BASE_URL` - Custom Anthropic endpoint (defaults to `https://api.anthropic.com`)
- `SESSION_AFFINITY_KEY` - Session affinity header for routing consistency
- `BENCHMARK_SESSION_ID` - Session identifier for virtual key metadata
- `BENCHMARK_EXPERIMENT` - Experiment name for virtual key metadata
- `BENCHMARK_VARIANT` - Variant name for virtual key metadata
- `BENCHMARK_HARNESS` - Harness profile for virtual key metadata
- `BENCHMARK_TASK_CARD` - Task card identifier for virtual key metadata
- `BENCHMARK_BUDGET_USD` - Daily budget in USD for session virtual keys (default: 10)
- `PROMETHEUS_PUSHGATEWAY_URL` - Prometheus pushgateway URL for metrics

## Starting the Proxy

### With Docker Compose (Recommended)

```bash
# Set required environment variables
export LITELLM_MASTER_KEY="sk-litellm-master-$(openssl rand -hex 16)"
export LITELLM_DATABASE_URL="postgresql://postgres:postgres@localhost:5432/litellm"
export FIREWORKS_API_KEY="your-fireworks-key"
export OPENAI_API_KEY="your-openai-key"
export ANTHROPIC_API_KEY="your-anthropic-key"

# Start the stack
docker-compose up -d litellm
```

### Standalone

```bash
# Install LiteLLM
pip install 'litellm[proxy]'

# Set environment variables and start
export LITELLM_MASTER_KEY="sk-litellm-master-$(openssl rand -hex 16)"
export FIREWORKS_API_KEY="your-fireworks-key"
export OPENAI_API_KEY="your-openai-key"
export ANTHROPIC_API_KEY="your-anthropic-key"

litellm --config configs/litellm/litellm.yaml
```

## Session Credentials

Benchmark sessions use LiteLLM virtual keys for isolation and correlation.

### Creating a Session Virtual Key

```bash
# Create a virtual key with session metadata
curl -X POST http://localhost:4000/key/generate \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "metadata": {
      "session_id": "session-abc123",
      "experiment": "fireworks-terminal-agents-comparison",
      "variant": "fireworks-kimi-k2-5-claude-code",
      "harness": "claude-code",
      "task_card": "repo-auth-analysis"
    },
    "budget_duration": "1d",
    "budget": 10
  }'
```

### Pointing a Harness at the Proxy

#### Claude Code

```bash
# Environment snippet from benchmark session manager
export ANTHROPIC_BASE_URL="http://localhost:4000"
export ANTHROPIC_API_KEY="${SESSION_VIRTUAL_KEY}"
export ANTHROPIC_MODEL="kimi-k2-5"
export ANTHROPIC_DEFAULT_SONNET_MODEL="kimi-k2-5"
export ANTHROPIC_DEFAULT_HAIKU_MODEL="kimi-k2-5"
export ANTHROPIC_DEFAULT_OPUS_MODEL="kimi-k2-5"
export CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS="1"

# Launch Claude Code
claude
```

`SESSION_VIRTUAL_KEY` is a generated LiteLLM virtual key for one benchmark session. It is not your provider API key and should not be invented manually.

#### OpenAI-Compatible CLI

```bash
# Environment snippet from benchmark session manager
export OPENAI_BASE_URL="http://localhost:4000"
export OPENAI_API_KEY="${SESSION_VIRTUAL_KEY}"
export OPENAI_MODEL="gpt-5.4-mini"
export OPENAI_TIMEOUT="120"

# Use with any OpenAI-compatible CLI
openai api responses.create -m gpt-5.4-mini
```

## Validation

Validate the LiteLLM configuration syntax:

```bash
# Basic YAML syntax validation
python -c "import yaml; yaml.safe_load(open('configs/litellm/litellm.yaml'))"
# Expected output: (no errors - exits 0)
```

### Runtime Validation Evidence

After YAML syntax validation passes, verify the config loads in LiteLLM:

```bash
# Install LiteLLM
pip install 'litellm[proxy]'

# Validate config schema (requires LiteLLM installed)
litellm --config configs/litellm/litellm.yaml --detection

# Or start the proxy (requires env vars)
export LITELLM_MASTER_KEY="sk-litellm-master-$(openssl rand -hex 16)"
export FIREWORKS_API_KEY="test-key"
export OPENAI_UPSTREAM_API_KEY="test-key"

# Config will be validated on startup
litellm --config configs/litellm/litellm.yaml
```

**Validation Checklist:**
- [x] YAML syntax passes (`yaml.safe_load`)
- [x] No invalid `virtual_key_metadata` blocks (removed - handled via API)
- [x] No duplicate `callback_settings` blocks (removed - handled in `litellm_settings`)
- [x] API key info redaction enabled (`redact_user_api_key_info: true`)
- [x] Config structure validated against LiteLLM schema
- [x] All model aliases match benchmark provider configs
- [x] Route names match benchmark provider configs

See [VALIDATION.md](VALIDATION.md) for full runtime evidence.

## Correlation with Benchmark Configs

The model aliases in `litellm.yaml` must exactly match the benchmark provider configs:

| Benchmark Config | Route Name | Model Alias |
|:---------------|:-----------|:------------|
| `configs/providers/fireworks.yaml` | `fireworks-main` | `kimi-k2-5`, `kimi-k2-5-turbo`, `glm-5`, `glm-5-fast` |
| `configs/providers/openai.yaml` | `openai-main` | `gpt-5.4`, `gpt-5.4-mini` |

When running a benchmark session, the harness profile renders environment variables that point to the LiteLLM proxy using the session-scoped virtual key. The model alias from the variant config is used as the model name in API requests.

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Harness       │────▶│   LiteLLM Proxy  │────▶│   Provider      │
│   (Claude Code, │     │   (this config)  │     │   (Fireworks,   │
│    OpenAI CLI)  │     │   :4000          │     │    OpenAI)      │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌──────────────────┐
                        │   Prometheus     │
                        │   Metrics        │
                        └──────────────────┘
                               │
                               ▼
                        ┌──────────────────┐
                        │   PostgreSQL     │
                        │   (LiteLLM +     │
                        │    Benchmark)    │
                        └──────────────────┘
```

## Troubleshooting

### Check LiteLLM is running

```bash
curl http://localhost:4000/health
```

### List available models

```bash
curl http://localhost:4000/models \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY"
```

### Check virtual key usage

```bash
curl http://localhost:4000/key/info \
  -H "Authorization: Bearer $SESSION_VIRTUAL_KEY"
```

## See Also

- [LiteLLM Proxy Documentation](https://docs.litellm.ai/docs/proxy/)
- [Benchmark Provider Configs](../configs/providers/)
- [Harness Profiles](../configs/harnesses/)
- [Variant Configs](../configs/variants/)
