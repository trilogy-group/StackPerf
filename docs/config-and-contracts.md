# Config and Contracts

## Operating modes

StackPerf supports two complementary operating modes.

### Benchmark mode

Benchmark mode is the session-first comparison workflow. It requires:

- an `experiment`
- a `variant`
- a `task_card`
- a `harness_profile`

Every benchmark session must be created before harness traffic starts. The system issues a session-scoped proxy credential, renders a harness environment snippet, and normalizes all traffic into `requests` rows that belong to the session.

### Usage mode

Usage mode is the sessionless observability workflow. It works **without** experiment, variant, task card, or session. The operator creates a usage-mode proxy key (with `key_alias`, `owner`, `team`, `customer`), routes traffic through LiteLLM, and the system normalizes all traffic into `usage_requests` rows.

Usage mode does not weaken benchmark invariants. Benchmark mode still requires session creation before harness traffic.

## Canonical terms

| Term | Definition |
|------|------------|
| **Proxy key** | A LiteLLM virtual key (the actual secret string) issued by the LiteLLM proxy. Example: `sk-litellm-abc123def456` (secret, never stored in the benchmark database). |
| **Key alias** | A human-readable identifier assigned to a proxy key at creation time (e.g., `team-alpha-gpt4o`). Aliases are non-secret, unique, and stored in the benchmark registry. |
| **Proxy key ID** | The stable surrogate identifier in the benchmark registry for a proxy key (auto-increment or UUID, e.g., `pk-550e8400-e29b-41d4-a716-446655440000`). This is non-secret and is the canonical foreign key for usage rows. |
| **LiteLLM virtual key ID** | The LiteLLM-internal identifier for a virtual key (e.g., a UUID `550e8400-e29b-41d4-a716-446655440000` or an internal hash distinct from the bearer token). This is a secret or sensitive identifier and must not be persisted in the benchmark database. |
| **Usage request** | One normalized LLM call observed through LiteLLM, stored in `usage_requests`. |
| **Usage rollup** | A derived summary of usage requests grouped by one or more dimensions (e.g., proxy_key_id, key_alias, model, time bucket). |
| **Owner** | The entity responsible for a proxy key (e.g., a person, service account, or team). |
| **Team** | An organizational grouping that owns one or more proxy keys. |
| **Customer** | An external billing or cost-center label attached to a proxy key for charge-back. |
| **Time bucket** | A fixed time interval (e.g., hour, day) used to aggregate usage rollups. |

## Config directories

```text
configs/
├── providers/
├── harnesses/
├── variants/
├── experiments/
└── task-cards/
```

## Provider config

A provider config defines an upstream endpoint, route metadata, secret references, and model aliases exposed through LiteLLM.

### Example

```yaml
name: fireworks
route_name: fireworks-main
protocol_surface: anthropic_messages
upstream_base_url_env: FIREWORKS_BASE_URL
api_key_env: FIREWORKS_API_KEY
models:
  - alias: kimi-k2-5
    upstream_model: accounts/fireworks/models/kimi-k2p5
  - alias: glm-5
    upstream_model: accounts/fireworks/models/glm-5
routing_defaults:
  timeout_seconds: 180
  extra_headers:
    x-session-affinity: "{{ session_affinity_key }}"
```

## Harness profile config

A harness profile describes how to point a harness at the local LiteLLM proxy.

### Example: Claude Code

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

### Example: OpenAI-compatible harness

```yaml
name: openai-compatible-cli
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

## Variant config

A variant combines provider, model, harness profile, and harness-specific configuration values.

### Example

```yaml
name: fireworks-kimi-k2-5-claude-beta-off
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

## Experiment config

An experiment groups comparable variants.

### Example

```yaml
name: fireworks-openhands-model-comparison
variants:
  - fireworks-kimi-k2-5-openhands
  - fireworks-glm-5-openhands
```

## Task-card config

A task card defines the interactive work and stop conditions.

### Example

```yaml
name: repo-auth-analysis
repo_path: /path/to/repo
goal: identify auth flow, trust boundaries, and risky edge cases
starting_prompt: |
  Analyze the authentication architecture in this repository.
stop_condition: produce a written summary with file references and identified risks
session_timebox_minutes: 30
notes:
  - work from the current git commit only
  - do not install new dependencies
```

## Session creation contract

The session manager must accept:

- experiment name
- variant name
- task-card name
- harness profile name
- operator label if provided

It must produce:

- benchmark `session_id`
- session-scoped proxy credential
- proxy key alias
- rendered environment snippet
- rendered dotenv file if requested
- captured repository metadata

## Session credentials and proxy routing

### LiteLLM virtual keys for session isolation

Benchmark sessions use LiteLLM virtual keys to:
1. Isolate session traffic for billing and correlation
2. Attach metadata (experiment, variant, harness, task-card) to all requests
3. Enforce session-scoped rate limits and budgets

### Creating a session virtual key

When a session is created, the benchmark app generates a LiteLLM virtual key:

```bash
curl -X POST http://localhost:4000/key/generate \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "metadata": {
      "session_id": "session-uuid",
      "experiment": "experiment-name",
      "variant": "variant-name",
      "harness": "harness-profile",
      "task_card": "task-card-name"
    },
    "budget_duration": "1d",
    "budget": 10
  }'
```

The returned `key` becomes the `SESSION_VIRTUAL_KEY` for the harness environment.

### Pointing a harness at the proxy

Harness profiles specify which environment variables to set. The benchmark app renders the exact values:

#### Example: Claude Code environment

```yaml
# Harness profile: configs/harnesses/claude-code.yaml
name: claude-code
protocol_surface: anthropic_messages
base_url_env: ANTHROPIC_BASE_URL
api_key_env: ANTHROPIC_API_KEY
model_env: ANTHROPIC_MODEL
```

Rendered environment snippet:

```bash
export ANTHROPIC_BASE_URL="http://localhost:4000"
export ANTHROPIC_API_KEY="sk-litellm-session-uuid"
export ANTHROPIC_MODEL="kimi-k2-5"
export ANTHROPIC_DEFAULT_SONNET_MODEL="kimi-k2-5"
export ANTHROPIC_DEFAULT_HAIKU_MODEL="kimi-k2-5"
export ANTHROPIC_DEFAULT_OPUS_MODEL="kimi-k2-5"
export CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS="1"
```

#### Example: OpenAI-compatible CLI environment

```yaml
# Harness profile: configs/harnesses/openai-cli.yaml
name: openai-cli
protocol_surface: openai_responses
base_url_env: OPENAI_BASE_URL
api_key_env: OPENAI_API_KEY
model_env: OPENAI_MODEL
```

Rendered environment snippet:

```bash
export OPENAI_BASE_URL="http://localhost:4000"
export OPENAI_API_KEY="sk-litellm-session-uuid"
export OPENAI_MODEL="gpt-4o"
export OPENAI_TIMEOUT="120"
```

### Route and model resolution

When a harness sends a request:

1. The `base_url` points to the LiteLLM proxy (`http://localhost:4000`)
2. The `api_key` is the session-scoped virtual key
3. The `model` is the alias from the variant config (e.g., `kimi-k2-5`, `gpt-4o`)
4. LiteLLM routes to the correct provider based on the model alias
5. LiteLLM attaches session metadata from the virtual key to the request log

The request log includes:
- `session_id` from virtual key metadata
- `route_name` from model config (e.g., `fireworks-main`, `openai-main`)
- `model` alias (e.g., `kimi-k2-5`)
- `provider` (e.g., `fireworks`, `openai`)

### Verification checklist

Before running a harness:

- [ ] LiteLLM proxy is running on `http://localhost:4000`
- [ ] Health check passes: `curl http://localhost:4000/health`
- [ ] Virtual key is valid: `curl http://localhost:4000/key/info -H "Authorization: Bearer $SESSION_VIRTUAL_KEY"`
- [ ] Base URL environment variable is set to `http://localhost:4000`
- [ ] API key environment variable is set to the session virtual key
- [ ] Model environment variable is set to the variant's model alias

## Usage-mode proxy key contract

### Creating a usage-mode proxy key

Usage-mode keys are independent of benchmark sessions. They are created through the CLI or API:

```bash
bench key create \
  --alias team-alpha-gpt4o \
  --owner alice \
  --team platform \
  --customer acme-corp \
  --description "Platform team GPT-4o key" \
  --budget-duration 30d \
  --budget-amount 1000
```

The command must produce:

- a `proxy_key_id` — stable surrogate primary key, non-secret
- a `key_alias` (human-readable, unique, non-secret)
- a LiteLLM virtual key secret (displayed once to the operator, never stored in the benchmark database)
- a registry entry in `proxy_keys` containing only non-secret metadata

### Proxy key registry (`proxy_keys`)

Stored fields (all non-secret):

- `proxy_key_id` — stable surrogate primary key (UUID or auto-increment), non-secret
- `key_alias` — human-readable identifier, unique, non-secret
- `owner` — attribution owner
- `team` — team grouping
- `customer` — customer or cost-center
- `description` — human note
- `budget_duration` — budget interval
- `budget_amount` — budget limit
- `created_at` — creation timestamp
- `revoked_at` — revocation timestamp (nullable)
- `expires_at` — expiration timestamp (nullable)
- `metadata` — JSONB key-value tags (nullable)

### Redaction rules

1. The benchmark database **never** stores raw LiteLLM virtual key secrets (`sk-...`).
2. The benchmark database **never** stores upstream provider API key secrets.
3. Collectors must resolve raw LiteLLM virtual key IDs in LiteLLM logs to the stable `proxy_key_id` (and denormalized `key_alias`) from the `proxy_keys` registry before writing `usage_requests` rows. The raw `sk-...` value is never stored.
4. Exports and API responses must include only `proxy_key_id` and `key_alias`, never the raw LiteLLM virtual key ID.
5. Application logs must log `proxy_key_id` or `key_alias`, never the secret.
6. Benchmark-mode sessions follow the same redaction rules: `proxy_key_alias` is the non-secret alias stored on the `sessions` record; the raw session virtual key secret is never stored, logged, or exported.

## CLI contract

### Benchmark commands

```text
bench config validate
bench experiment list
bench variant list
bench task-card list
bench session create --experiment <name> --variant <name> --task-card <name> --harness <name>
bench session finalize --session-id <id> --status <completed|aborted|invalid>
bench collect litellm
bench collect prometheus
bench rollup sessions
bench report compare --experiment <name>
bench export sessions --format <csv|json|parquet>
```

### Usage-mode commands

```text
bench key create --alias <alias> --owner <owner> --team <team> --customer <customer>
bench key list
bench key revoke --alias <alias>
bench usage collect
bench usage rollup --by proxy_key_id --by key_alias --by model --by day
bench usage report --proxy-key-id <id> --from <date> --to <date>
bench usage report --key-alias <alias> --from <date> --to <date>
bench usage export --format <csv|json|parquet>
```

## Normalization contract

Every normalized request row must contain:

- `request_id`
- `session_id`
- `variant_id`
- `experiment_id`
- `provider`
- `provider_route`
- `model`
- `harness_profile`
- `request_started_at`
- `request_finished_at`
- `latency_ms`
- `ttft_ms` when available
- `input_tokens`
- `output_tokens`
- `cached_input_tokens` when available
- `cache_write_tokens` when available
- `status`
- `litellm_call_id` when available
- `provider_request_id` when available

## Rendering rules

Harness env rendering must:

- resolve the correct base URL variable name for the harness
- resolve the correct API key variable name for the harness
- resolve the correct model variable name for the harness
- apply the variant's env overrides
- render benchmark tags if supported
- never write secrets into committed files

## Validation rules

Config validation must reject:

- missing provider or harness references
- unsupported protocol surface combinations
- duplicate names within the same config type
- unresolved template variables
- task cards missing stop conditions
- variants missing benchmark tags for provider, model, and harness
