# LiteLLM Benchmarking System

## Purpose

This project provides a local-first benchmarking system for comparing provider, model, harness, and harness-configuration performance through a shared LiteLLM proxy.

The system is built for interactive terminal agents and IDE agents that can be pointed at a custom inference base URL. The benchmark application does not own the harness runtime. It owns session registration, correlation, collection, normalization, storage, reporting, and dashboards.

## What the system answers

The completed system should make it easy to answer questions such as:

- Which provider and model combination is fastest for the same task card and harness?
- How does Claude Code compare with Codex, OpenCode, OpenHands, Gemini-oriented clients, or other agent harnesses when routed through the same local proxy?
- Does a harness configuration change improve TTFT, total latency, output throughput, error rate, or cache behavior?
- Does a provider-specific routing change improve session-level performance?
- How much variance exists between repeated sessions of the same benchmark variant?

## Recommended local stack

Use Docker Compose for infrastructure and `uv` for the benchmark application.

Infrastructure services:

- LiteLLM proxy
- PostgreSQL
- Prometheus
- Grafana

Benchmark application capabilities:

- config loading and validation
- experiment, variant, and session registry
- session credential issuance
- harness env rendering
- LiteLLM request collection and normalization
- Prometheus metric collection and rollups
- query API and exports
- dashboards and reports

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

## Repository layout

```text
.
├── AGENTS.md
├── README.md
├── pyproject.toml
├── Makefile
├── docker-compose.yml
├── .env.example
├── configs/
│   ├── litellm/
│   ├── prometheus/
│   ├── grafana/
│   ├── providers/
│   ├── harnesses/
│   ├── variants/
│   ├── experiments/
│   └── task-cards/
├── dashboards/
├── docs/
│   ├── architecture.md
│   ├── benchmark-methodology.md
│   ├── config-and-contracts.md
│   ├── data-model-and-observability.md
│   ├── implementation-plan.md
│   ├── references.md
│   └── security-and-operations.md
├── skills/
│   └── convert-tasks-to-linear/
│       └── SKILL.md
├── src/
│   ├── benchmark_core/
│   ├── cli/
│   ├── collectors/
│   ├── reporting/
│   └── api/
└── tests/
```

## Documentation map

- `AGENTS.md`
  - persistent project context for coding agents
  - architectural invariants
  - delivery and testing rules
- `README.md`
  - project overview and purpose
  - quick start guide for first benchmark session
  - troubleshooting for common issues
- `docs/architecture.md`
  - system components
  - data flow
  - deployment boundaries
- `docs/benchmark-methodology.md`
  - how to run comparable interactive benchmark sessions
  - metric definitions and confounder controls
- `docs/config-and-contracts.md`
  - config schemas
  - session and CLI contracts
  - normalization contracts
- `docs/operator-workflow.md`
  - comprehensive session lifecycle guide
  - decision flow for variant selection
  - best practices for operators
  - common benchmark patterns
- `docs/launch-recipes.md`
  - detailed harness setup instructions
  - step-by-step launch procedures
  - troubleshooting for each harness
  - custom harness profile creation
- `docs/data-model-and-observability.md`
  - canonical entities
  - storage model
  - derived metrics
- `docs/security-and-operations.md`
  - local security posture
  - redaction, retention, and secrets
  - operator safeguards
- `docs/implementation-plan.md`
  - parent issues and sub-issues
  - Definition of Ready information
  - acceptance criteria and test plans
- `docs/references.md`
  - external references that shaped the design
- `skills/convert-tasks-to-linear/SKILL.md`
  - reusable instructions for converting a markdown implementation plan into Linear parent issues and sub-issues
- `configs/litellm/README.md`
  - LiteLLM proxy configuration
  - route naming convention
  - local operator instructions for session credentials
  - harness environment setup

## Observability Quick Start

The local observability stack combines LiteLLM, Prometheus, Grafana, and PostgreSQL:

- LiteLLM exposes raw metrics at `http://localhost:4000/metrics`
- Prometheus scrapes and stores those metrics at `http://localhost:9090`
- Grafana reads from Prometheus and PostgreSQL and renders dashboards at `http://localhost:3000`
- PostgreSQL stores historical benchmark data used by the experiment summary dashboard

The easiest way to think about them:

- Prometheus is the metric collection, storage, and query engine
- Grafana is the visualization UI
- Grafana does not collect metrics itself
- Prometheus does not provide the benchmark dashboards by itself

In this repository:

- live dashboards use Prometheus data
- historical benchmark dashboards use PostgreSQL data

### Local URLs

- Grafana: `http://localhost:3000`
- Prometheus: `http://localhost:9090`
- LiteLLM metrics endpoint: `http://localhost:4000/metrics`

Default Grafana credentials:

- username: `admin`
- password: `admin`

### What To Open First

After `docker compose up -d`, open Grafana and inspect the `Benchmark` folder:

- `Live Request Latency`
- `Live TTFT Metrics`
- `Live Error Rate`
- `Experiment Summary`

For historical seeded local validation, choose the `demo-grafana-validation` experiment in `Experiment Summary`.

### When To Use Which Tool

- Use Grafana when you want to inspect dashboards and visualizations
- Use Prometheus when you want to inspect raw metric names or test PromQL queries directly

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
export LITELLM_DATABASE_URL="postgresql://postgres:postgres@localhost:5432/litellm"
export FIREWORKS_API_KEY="your-fireworks-key"
export OPENAI_API_KEY="your-openai-key"
export ANTHROPIC_API_KEY="your-anthropic-key"

# Start infrastructure services
docker-compose up -d

# Verify services are healthy
docker-compose ps
curl http://localhost:4000/health
```

Expected output: All services show "healthy" status, and LiteLLM health check returns `{"status": "healthy"}`.

#### 2. Validate Configuration

```bash
# Validate all config files (providers, harnesses, variants, experiments, task cards)
bench config validate
```

Expected output: All config files pass validation with no errors.

#### 3. Create a Benchmark Session

Choose an experiment, variant, and task card from the available configs:

```bash
# List available experiments
bench experiment list

# List available variants
bench variant list

# List available task cards
bench task-card list

# Create a session
bench session create \
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
bench session env <session-id>
```

Copy the output and apply it in your terminal:

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

#### 5. Launch the Harness

With the environment set, launch your harness:

```bash
# For Claude Code
claude

# For OpenAI CLI
openai api chat.completions.create -m gpt-4o
```

The harness now routes all traffic through the local LiteLLM proxy with session correlation.

#### 6. Work on the Task

Follow the task card instructions. The benchmark system automatically captures:

- Request latencies and TTFT
- Token counts (input, output, cached)
- Error rates and status codes
- Cache hit behavior

#### 7. Finalize the Session

When done, finalize the session:

```bash
bench session finalize <session-id> --status completed
```

Expected output: Session status updated, end time recorded.

#### 8. View Metrics and Reports

```bash
# Open Grafana dashboards
open http://localhost:3000

# Export comparison reports
bench export sessions --format csv --output sessions.csv
```

### Next Steps

- **Detailed Workflow**: See [docs/operator-workflow.md](docs/operator-workflow.md) for comprehensive session lifecycle guidance.
- **Launch Recipes**: See [docs/launch-recipes.md](docs/launch-recipes.md) for detailed harness-specific setup instructions.
- **Troubleshooting**: See [Troubleshooting](#troubleshooting) section below for common issues.

## Local operator workflow

For a complete walkthrough of running a benchmark session, see [configs/litellm/README.md](configs/litellm/README.md). The quick version:

1. Start the infrastructure stack (LiteLLM, PostgreSQL, Prometheus, Grafana)
2. Validate configs: `bench config validate`
3. Create a session: `bench session create --experiment <name> --variant <name> --task-card <name> --harness <name>`
4. Copy the rendered environment snippet and launch your harness interactively
5. Work on the task; the proxy captures all traffic with session correlation
6. Finalize the session: `bench session finalize --session-id <id> --status completed`
7. View metrics in Grafana and export comparison reports

## MVP success criteria

The MVP is complete when a developer can:

1. start LiteLLM, Postgres, Prometheus, and Grafana locally with one command
2. validate provider, harness profile, variant, experiment, and task-card configs
3. create a session for a specific benchmark variant
4. receive a session-specific environment snippet for a chosen harness
5. run the harness interactively against the proxy
6. collect and normalize request- and session-level data into the benchmark database
7. view live metrics in Grafana and historical comparisons in the benchmark app
8. export structured comparison results for providers, models, harnesses, and harness configurations

## Troubleshooting

This section covers common setup failures and their solutions.

### Infrastructure Issues

#### Docker Compose Services Not Starting

**Symptom**: `docker-compose up -d` fails or services show unhealthy status.

**Diagnosis**:
```bash
# Check service status
docker-compose ps

# Check service logs
docker-compose logs litellm
docker-compose logs postgres
docker-compose logs prometheus
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

**Symptom**: `curl http://localhost:4000/health` returns error or timeout.

**Diagnosis**:
```bash
# Check if LiteLLM container is running
docker-compose ps litellm

# Check LiteLLM logs
docker-compose logs litellm --tail 100
```

**Common Causes and Solutions**:

1. **Config syntax error**: LiteLLM config has invalid YAML.
   ```bash
   # Validate YAML syntax
   python -c "import yaml; yaml.safe_load(open('configs/litellm/litellm.yaml'))"
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
   docker-compose ps postgres
   # Test connection
   psql $LITELLM_DATABASE_URL -c "SELECT 1"
   ```

### Session Creation Issues

#### Session Create Command Fails

**Symptom**: `bench session create` returns error.

**Diagnosis**:
```bash
# Check if database is accessible
bench health check

# Verify configs exist
ls configs/experiments/
ls configs/variants/
ls configs/task-cards/
```

**Common Causes and Solutions**:

1. **Invalid experiment/variant/task-card name**: Name doesn't match config file.
   ```bash
   # List available configs
   bench experiment list
   bench variant list
   bench task-card list
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

**Symptom**: `bench session env` shows incorrect environment variables.

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
   bench session show <session-id>
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
   eval "$(bench session env <session-id>)"
   # Or copy-paste the exports manually
   ```

2. **Existing environment overrides**: Previous environment variables take precedence.
   ```bash
   # Unset old variables
   unset ANTHROPIC_BASE_URL ANTHROPIC_API_KEY
   unset OPENAI_BASE_URL OPENAI_API_KEY
   # Re-apply session environment
   bench session env <session-id>
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
bench session show <session-id>
```

**Common Causes and Solutions**:

1. **Session not created**: Session ID doesn't exist.
   ```bash
   # List sessions to find correct ID
   bench session list
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
   docker-compose restart prometheus
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
bench session show <session-id>

# Check request count
bench session show <session-id> | grep request
```

**Common Causes and Solutions**:

1. **Collection not run**: Normalization job not executed.
   ```bash
   # Run collection manually
   bench normalize litellm --session-id <session-id>
   ```

2. **LiteLLM logging disabled**: Request logs not being written.
   ```bash
   # Check LiteLLM config for logging settings
   grep -A5 "litellm_settings" configs/litellm/litellm.yaml
   ```

### Getting Help

If issues persist after following troubleshooting steps:

1. **Check logs**: Review all service logs for error messages.
   ```bash
   docker-compose logs --tail 200
   ```

2. **Verify versions**: Ensure you're using compatible versions.
   ```bash
   docker-compose --version
   uv --version
   python --version
   ```

3. **Clean slate**: Reset the environment and start fresh.
   ```bash
   # Stop and remove containers, volumes, and networks
   docker-compose down -v
   # Remove local database (if applicable)
   rm -f benchmark.db
   # Restart from Step 1
   docker-compose up -d
   ```

4. **File an issue**: Report bugs or documentation gaps at the project repository.
