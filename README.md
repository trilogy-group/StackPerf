# LiteLLM Benchmarking System

This project provides a local-first benchmarking system for comparing provider, model, harness, and harness-configuration performance through a shared LiteLLM proxy.

The system is built for interactive terminal agents and IDE agents that can be pointed at a custom inference base URL. The benchmark application does not own the harness runtime. It owns session registration, correlation, collection, normalization, storage, reporting, and dashboards.

## Quick Start

Run this first:

```bash
make install-dev
```

Then start the local stack:

```bash
export LITELLM_MASTER_KEY="sk-litellm-master-$(openssl rand -hex 16)"
export FIREWORKS_API_KEY="your-fireworks-key"
export OPENAI_API_KEY="your-openai-key"
export ANTHROPIC_API_KEY="your-anthropic-key"

docker compose up -d --force-recreate
```

Useful local URLs:

- LiteLLM health: `http://localhost:4000/health/liveliness`
- LiteLLM metrics: `http://localhost:4000/metrics`
- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3000` (`admin` / `admin`)

Open Grafana first and inspect the `Benchmark` folder:

- `Live Request Latency`
- `Live TTFT Metrics`
- `Live Error Rate`
- `Experiment Summary`

Use Grafana for dashboards and Prometheus for raw metric/debug queries.

## What This Helps Answer

The completed system should make it easy to answer questions such as:

- Which provider and model combination is fastest for the same task card and harness?
- How does Claude Code compare with Codex, OpenCode, OpenHands, Gemini-oriented clients, or other agent harnesses when routed through the same local proxy?
- Does a harness configuration change improve TTFT, total latency, output throughput, error rate, or cache behavior?
- Does a provider-specific routing change improve session-level performance?
- How much variance exists between repeated sessions of the same benchmark variant?

## Core design choices

1. LiteLLM is the single shared proxy and routing layer.
2. Every interactive benchmark session gets a benchmark-owned session ID.
3. Session correlation is built around a session-scoped proxy credential plus benchmark tags.
4. The project stores canonical benchmark records in a project-owned database.
5. LiteLLM and Prometheus are telemetry sources, not the canonical query model.
6. Prompt and response content are disabled by default.
7. The benchmark application stays harness-agnostic in its core path.

## Primary workflow

1. Define providers, harness profiles, variants, experiments, and task cards in versioned config files.
2. Create a benchmark session for a chosen variant and task card.
3. The session manager issues a session-scoped proxy credential and renders the exact environment snippet for the selected harness.
4. Launch the harness manually and use it interactively against the local LiteLLM proxy.
5. LiteLLM emits request data and Prometheus metrics while the benchmark app captures benchmark metadata.
6. Collectors normalize request- and session-level data into the project database.
7. Reports and dashboards compare sessions, variants, providers, models, and harnesses.

## Documentation map

- `README.md`: quick start and operator workflow
- `configs/litellm/README.md`: proxy routes, model aliases, and harness env examples
- `docs/operator-workflow.md`: detailed session lifecycle guidance
- `docs/launch-recipes.md`: harness-specific launch instructions
- `docs/architecture.md` and `docs/data-model-and-observability.md`: deeper implementation details

## Observability

- LiteLLM exposes raw metrics at `http://localhost:4000/metrics`
- Prometheus stores those metrics at `http://localhost:9090`
- Grafana visualizes live Prometheus data and historical PostgreSQL data at `http://localhost:3000`

Example Prometheus queries:

```promql
litellm_proxy_total_requests_metric_total
```

```promql
histogram_quantile(0.50, sum(rate(litellm_request_total_latency_metric_bucket[5m])) by (le))
```

```promql
histogram_quantile(0.50, sum(rate(litellm_llm_api_time_to_first_token_metric_bucket[5m])) by (le))
```

## Quick Start: Running Your First Benchmark Session

This section guides a new operator through a complete benchmark session from start to finish.

### Prerequisites Checklist

Before starting, ensure you have:

- [ ] Docker and Docker Compose installed
- [ ] `uv` package manager installed (for the benchmark application)
- [ ] API keys for your target providers (e.g., `FIREWORKS_API_KEY`, `OPENAI_API_KEY`)
- [ ] A terminal agent or CLI harness installed (e.g., Claude Code, OpenAI CLI)
- [ ] A repository to benchmark against (can be any codebase)

### Step-by-Step: First Session

#### 1. Install and Start the Infrastructure Stack

```bash
# Install benchmark application dependencies
make install-dev

# Set required environment variables
export LITELLM_MASTER_KEY="sk-litellm-master-$(openssl rand -hex 16)"
export FIREWORKS_API_KEY="your-fireworks-key"
export OPENAI_API_KEY="your-openai-key"
export ANTHROPIC_API_KEY="your-anthropic-key"

# Start infrastructure services
docker compose up -d --force-recreate

# Verify services are healthy
docker compose ps
curl http://localhost:4000/health/liveliness
```

Expected output: all services show healthy status and LiteLLM returns `"I'm alive!"`.

#### 2. Validate Configuration

```bash
# Validate all config files (providers, harnesses, variants, experiments, task cards)
uv run benchmark config validate
```

Current status: this command exists but is not fully implemented yet. It is safe to skip for now if it prints `Validation not fully implemented yet`.

#### 3. Create a Benchmark Session

Choose an experiment, variant, and task card from the available configs:

```bash
# List available experiments
uv run benchmark experiment list

# List available variants
uv run benchmark variant list

# List available task cards
uv run benchmark task-card list

# Create a session
uv run benchmark session create \
  --experiment fireworks-terminal-agents-comparison \
  --variant fireworks-kimi-k2-5-claude-code \
  --task-card repo-auth-analysis \
  --harness claude-code \
  --label "first-session" \
  --notes "Initial benchmark run"
```

Expected output: Session created with a unique `session_id` (UUID). Git metadata (branch, commit, dirty state) is captured automatically.

#### 4. Render and Apply Harness Environment

```bash
# Render the environment snippet for your session
uv run benchmark session env <session-id>
```

Copy the output and apply it in your terminal.

Important:

- `sk-benchmark-<session-id>` in the example below is a placeholder for a generated LiteLLM virtual key, not your Fireworks, OpenAI, or Anthropic provider key.
- You do not make up this value by hand. The benchmark session manager should generate it for the session and print it in `uv run benchmark session env <session-id>`.
- The session ID and the session virtual key are different things. The session ID identifies the benchmark run in the benchmark database. The session virtual key is the proxy credential the harness uses when talking to LiteLLM.
- Per-session segmentation is done by issuing a different virtual key for each benchmark session, usually with session metadata attached.

```bash
# Example output for claude-code harness:
export ANTHROPIC_BASE_URL="http://localhost:4000"
export ANTHROPIC_API_KEY="sk-benchmark-<session-id>"
export ANTHROPIC_MODEL="kimi-k2-5"
export ANTHROPIC_DEFAULT_SONNET_MODEL="kimi-k2-5"
export ANTHROPIC_DEFAULT_HAIKU_MODEL="kimi-k2-5"
export ANTHROPIC_DEFAULT_OPUS_MODEL="kimi-k2-5"
export CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS="1"
```

If you are setting up a harness manually before the session-manager flow is complete, generate a proxy key yourself:

```bash
curl -s -X POST http://localhost:4000/key/generate \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "metadata": {
      "session_id": "manual-dev-session",
      "harness": "claude-code"
    },
    "duration": "1h"
  }'
```

Use the returned `key` value as the harness-facing `ANTHROPIC_API_KEY` or `OPENAI_API_KEY`.

#### 5. Launch the Harness

With the environment set, launch your harness:

```bash
# For Claude Code
claude

# For an OpenAI-compatible CLI
openai api responses.create -m gpt-5.4-mini
```

The harness now routes all traffic through the local LiteLLM proxy with session correlation.

#### 5a. Choosing a Harness and Model

The harness talks to LiteLLM using a protocol surface, and LiteLLM maps the requested model alias to a real upstream provider route.

Current built-in model aliases:

- Fireworks: `kimi-k2-5`, `kimi-k2-5-turbo`, `glm-5`, `glm-5-fast`
- OpenAI: `gpt-5.4`, `gpt-5.4-mini`
- Anthropic: `claude-opus-4-6`, `claude-sonnet-4-6`

You can see the current aliases with:

```bash
curl -s http://localhost:4000/models -H "Authorization: Bearer $LITELLM_MASTER_KEY"
```

Use those aliases as the model names your harness sends to the proxy.

Examples:

- Claude Code uses Anthropic-style env vars, but it can still target Fireworks or OpenAI routes through LiteLLM by setting `ANTHROPIC_MODEL` to a LiteLLM alias such as `kimi-k2-5` or `gpt-5.4-mini`.
- OpenAI-compatible harnesses such as Codex, OpenCode, or OpenHands should generally use `OPENAI_BASE_URL=http://localhost:4000`, `OPENAI_API_KEY=<session virtual key>`, and whichever model alias you want to benchmark.
- Anthropic-compatible harnesses should use `ANTHROPIC_BASE_URL=http://localhost:4000`, `ANTHROPIC_API_KEY=<session virtual key>`, and whichever model alias you want to benchmark.

Examples by harness style:

```bash
# Claude Code against Fireworks Kimi K2.5
export ANTHROPIC_BASE_URL="http://localhost:4000"
export ANTHROPIC_API_KEY="$SESSION_VIRTUAL_KEY"
export ANTHROPIC_MODEL="kimi-k2-5"
export ANTHROPIC_DEFAULT_SONNET_MODEL="kimi-k2-5"
export ANTHROPIC_DEFAULT_HAIKU_MODEL="kimi-k2-5"
export ANTHROPIC_DEFAULT_OPUS_MODEL="kimi-k2-5"
```

```bash
# OpenAI-compatible client against OpenAI GPT-5.4 Mini
export OPENAI_BASE_URL="http://localhost:4000"
export OPENAI_API_KEY="$SESSION_VIRTUAL_KEY"
export OPENAI_MODEL="gpt-5.4-mini"
```

```bash
# OpenAI-compatible client against Fireworks GLM-5 Fast
export OPENAI_BASE_URL="http://localhost:4000"
export OPENAI_API_KEY="$SESSION_VIRTUAL_KEY"
export OPENAI_MODEL="glm-5-fast"
```

To add more models later, add a new LiteLLM alias in `configs/litellm/config.yaml` and keep the provider config in `configs/providers/` in sync.

#### 6. Work on the Task

Follow the task card instructions. The benchmark system automatically captures:

- Request latencies and TTFT
- Token counts (input, output, cached)
- Error rates and status codes
- Cache hit behavior

#### 7. Finalize the Session

When done, finalize the session:

```bash
uv run benchmark session finalize <session-id> --status completed
```

Expected output: Session status updated, end time recorded.

#### 8. View Metrics and Reports

```bash
# Open Grafana dashboards
open http://localhost:3000

# Export comparison reports
uv run benchmark export sessions --format csv --output sessions.csv
```

## Local operator workflow

For a complete walkthrough of running a benchmark session, see [configs/litellm/README.md](configs/litellm/README.md). The quick version:

1. Start the infrastructure stack (LiteLLM, PostgreSQL, Prometheus, Grafana)
2. Optionally run `uv run benchmark config validate` (currently a stub)
3. Create a session: `uv run benchmark session create --experiment <name> --variant <name> --task-card <name> --harness <name>`
4. Copy the rendered environment snippet and launch your harness interactively
5. Work on the task; the proxy captures all traffic with session correlation
6. Finalize the session: `uv run benchmark session finalize --session-id <id> --status completed`
7. View metrics in Grafana and export comparison reports

## Troubleshooting

This section covers common setup failures and their solutions.

### Infrastructure Issues

#### Docker Compose Services Not Starting

**Symptom**: `docker compose up -d` fails or services show unhealthy status.

**Diagnosis**:
```bash
# Check service status
docker compose ps

# Check service logs
docker compose logs litellm
docker compose logs postgres
docker compose logs prometheus
```

**Common Causes and Solutions**:

1. **Port conflicts**: Another service is using port 4000, 5432, 9090, or 3000.
   ```bash
   # Find process using port
   lsof -i :4000
   # Kill the process or change port in docker-compose.yml
   ```

2. **Missing environment variables**: LiteLLM master key or database URL not set.
   ```bash
   # Verify environment variables
   echo $LITELLM_MASTER_KEY
   echo $LITELLM_DATABASE_URL
   ```

3. **Docker not running**: Ensure Docker daemon is active.
   ```bash
   # Check Docker status
   docker info
   ```

#### LiteLLM Health Check Fails

**Symptom**: `curl http://localhost:4000/health/liveliness` returns error or timeout.

**Diagnosis**:
```bash
# Check if LiteLLM container is running
docker compose ps litellm

# Check LiteLLM logs
docker compose logs litellm --tail 100
```

**Common Causes and Solutions**:

1. **Config syntax error**: LiteLLM config has invalid YAML.
   ```bash
   # Validate YAML syntax
    python -c "import yaml; yaml.safe_load(open('configs/litellm/config.yaml'))"
   ```

2. **Missing provider keys**: Required API keys not set.
   ```bash
   # Verify provider keys
   echo $FIREWORKS_API_KEY
   echo $OPENAI_API_KEY
   ```

3. **Database connection failure**: PostgreSQL not ready or connection string incorrect.
   ```bash
   # Check PostgreSQL status
docker compose ps postgres
   # Test connection
   psql $LITELLM_DATABASE_URL -c "SELECT 1"
   ```

### Session Creation Issues

#### Session Create Command Fails

**Symptom**: `uv run benchmark session create` returns error.

**Diagnosis**:
```bash
# Check if database is accessible
uv run benchmark health check

# Verify configs exist
ls configs/experiments/
ls configs/variants/
ls configs/task-cards/
```

**Common Causes and Solutions**:

1. **Invalid experiment/variant/task-card name**: Name doesn't match config file.
   ```bash
   # List available configs
    uv run benchmark experiment list
    uv run benchmark variant list
    uv run benchmark task-card list
   ```

2. **Database not initialized**: Benchmark database tables don't exist.
   ```bash
   # Run migrations
   make db-migrate
   ```

3. **Not in a git repository**: Git metadata capture fails.
   ```bash
   # Check if in git repo
   git rev-parse --is-inside-work-tree
   # If not, session will proceed with warning (non-blocking)
   ```

#### Session Env Returns Wrong Environment

**Symptom**: `uv run benchmark session env` shows incorrect environment variables.

**Diagnosis**:
```bash
# Check harness profile config
cat configs/harnesses/claude-code.yaml

# Verify variant config
cat configs/variants/fireworks-kimi-k2-5-claude-code.yaml
```

**Common Causes and Solutions**:

1. **Wrong harness profile**: Session created with wrong harness.
   ```bash
   # Check session details
    uv run benchmark session show <session-id>
   ```

2. **Harness profile mismatch**: Variant specifies different harness than session.
   ```bash
   # Verify variant's harness_profile field
   grep harness_profile configs/variants/<variant-name>.yaml
   ```

### Harness Launch Issues

#### Harness Not Routing Through Proxy

**Symptom**: Harness sends requests directly to provider, not through LiteLLM.

**Diagnosis**:
```bash
# Check environment variables are set
env | grep ANTHROPIC
env | grep OPENAI

# Verify base URL points to proxy
echo $ANTHROPIC_BASE_URL  # Should be http://localhost:4000
echo $OPENAI_BASE_URL     # Should be http://localhost:4000
```

**Common Causes and Solutions**:

1. **Environment not sourced**: Environment snippet not applied to current shell.
   ```bash
   # Re-apply the environment snippet
    eval "$(uv run benchmark session env <session-id>)"
   # Or copy-paste the exports manually
   ```

2. **Existing environment overrides**: Previous environment variables take precedence.
   ```bash
   # Unset old variables
   unset ANTHROPIC_BASE_URL ANTHROPIC_API_KEY
   unset OPENAI_BASE_URL OPENAI_API_KEY
   # Re-apply session environment
   uv run benchmark session env <session-id>
   ```

3. **Harness config file override**: Harness has hardcoded base URL in config.
   ```bash
   # Check harness config files
   cat ~/.claude/config.json  # For Claude Code
   # Temporarily remove or rename config to use environment variables
   ```

#### Harness Authentication Fails

**Symptom**: Harness reports 401 Unauthorized or invalid API key.

**Diagnosis**:
```bash
# Test session virtual key
curl http://localhost:4000/key/info \
  -H "Authorization: Bearer $ANTHROPIC_API_KEY"

# Check if session exists
uv run benchmark session show <session-id>
```

**Common Causes and Solutions**:

1. **Session not created**: Session ID doesn't exist.
   ```bash
   # List sessions to find correct ID
   uv run benchmark session list
   ```

2. **Virtual key expired**: Session key has time or budget limit.
   ```bash
   # Create new session or check key info
   curl http://localhost:4000/key/info \
     -H "Authorization: Bearer $SESSION_VIRTUAL_KEY"
   ```

### Data Collection Issues

#### No Metrics in Grafana

**Symptom**: Grafana dashboards show "No data".

**Diagnosis**:
```bash
# Check Prometheus targets
curl http://localhost:9090/api/v1/targets

# Verify LiteLLM is emitting metrics
curl http://localhost:4000/metrics | grep litellm
```

**Common Causes and Solutions**:

1. **Prometheus not scraping LiteLLM**: Scrape config missing or misconfigured.
   ```bash
   # Check Prometheus config
   cat configs/prometheus/prometheus.yml
   # Restart Prometheus
    docker compose restart prometheus
   ```

2. **No traffic yet**: No requests have been sent through the proxy.
   ```bash
   # Send test request
   curl http://localhost:4000/v1/chat/completions \
     -H "Authorization: Bearer $SESSION_VIRTUAL_KEY" \
     -H "Content-Type: application/json" \
     -d '{"model": "kimi-k2-5", "messages": [{"role": "user", "content": "test"}]}'
   ```

3. **Time range mismatch**: Grafana time picker is outside session time.
   ```bash
   # In Grafana, adjust time range to "Last 1 hour" or session time
   ```

#### Session Data Not in Database

**Symptom**: Session queries return no data after session is finalized.

**Diagnosis**:
```bash
# Check if session exists
uv run benchmark session show <session-id>

# Check request count
uv run benchmark session show <session-id> | grep request
```

**Common Causes and Solutions**:

1. **Collection not run**: Normalization job not executed.
   ```bash
   # Run collection manually
    uv run benchmark normalize litellm --session-id <session-id>
   ```

2. **LiteLLM logging disabled**: Request logs not being written.
   ```bash
   # Check LiteLLM config for logging settings
    grep -A5 "litellm_settings" configs/litellm/config.yaml
   ```

### Getting Help

If issues persist after following troubleshooting steps:

1. **Check logs**: Review all service logs for error messages.
   ```bash
    docker compose logs --tail 200
   ```

2. **Verify versions**: Ensure you're using compatible versions.
   ```bash
    docker compose version
   uv --version
   python --version
   ```

3. **Clean slate**: Reset the environment and start fresh.
   ```bash
   # Stop and remove containers, volumes, and networks
    docker compose down -v
   # Remove local database (if applicable)
   rm -f benchmark.db
   # Restart from Step 1
    docker compose up -d
   ```

4. **File an issue**: Report bugs or documentation gaps at the project repository.
