# Operator Workflow Guide

## Purpose

This document provides comprehensive guidance for operators running interactive benchmark sessions. It covers the complete session lifecycle, decision points, and best practices for running comparable, reproducible benchmarks.

## Who Should Read This

- **Operators**: Anyone running benchmark sessions using this system
- **Benchmark Designers**: Those defining experiments, variants, and task cards
- **Reviewers**: Those interpreting benchmark results

## Session Lifecycle Overview

A benchmark session follows this lifecycle:

```
┌─────────────┐
│   Setup     │  Install dependencies, configure providers, start services
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Plan      │  Choose experiment, variant, task card, and harness
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Register   │  Create session, capture git metadata, get credentials
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Launch    │  Apply environment, start harness, verify routing
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Execute   │  Work on task, capture telemetry automatically
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Finalize    │  Record outcome, run collection, verify data
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Report    │  View dashboards, export results, compare sessions
└─────────────┘
```

## Phase 1: Setup

### Prerequisites Verification

Before any benchmark session, verify your environment:

```bash
# 1. Check Docker is running
docker info

# 2. Check required tools
which uv
which python3

# 3. Verify API keys are set
env | grep -E '(FIREWORKS|OPENAI|ANTHROPIC)_API_KEY'

# 4. Verify repository state
git status
```

### Infrastructure Startup

Start the observability stack:

```bash
# Set master key (only needed once per session)
export LITELLM_MASTER_KEY="sk-litellm-master-$(openssl rand -hex 16)"

# Start services
docker-compose up -d

# Wait for services to be healthy
sleep 10

# Verify all services
docker-compose ps
curl http://localhost:4000/health
```

### Database Initialization

If this is your first run or after schema changes:

```bash
# Run migrations
make db-migrate

# Verify database is ready
bench health check
```

## Phase 2: Plan

### Choosing an Experiment

Experiments group comparable variants around a question. Review available experiments:

```bash
bench experiment list
```

For each experiment, understand:
- **Question**: What is the experiment trying to answer?
- **Variants**: Which provider/model/harness combinations are included?
- **Task Cards**: What tasks are intended for comparison?

### Choosing a Variant

Variants define the benchmarkable configuration:

```bash
bench variant list
bench variant show <variant-name>
```

Key variant attributes:
- **Provider**: Upstream inference provider (e.g., Fireworks, OpenAI)
- **Model**: Specific model alias (e.g., kimi-k2-5, gpt-4o)
- **Harness Profile**: How to point the harness at the proxy
- **Configuration**: Harness-specific settings (e.g., beta features on/off)

### Choosing a Task Card

Task cards define the work to be done:

```bash
bench task-card list
bench task-card show <task-card-name>
```

Task card requirements:
- **Goal**: Clear objective statement
- **Repository**: Target codebase path
- **Starting Instructions**: What to do first
- **Stop Condition**: When to stop working
- **Time Box**: Maximum session duration

### Session Mode Selection

Choose based on your objective:

**Bounded Benchmark Session** (for comparisons):
- Fixed task card
- Fixed repository commit
- Explicit stop condition
- Used for variant comparisons

**Exploratory Session** (for understanding):
- Same metadata capture rules
- Clear purpose notes
- Marked as exploratory in analysis
- Not used for direct comparisons

## Phase 3: Register

### Creating the Session

Create a session with full metadata capture:

```bash
bench session create \
  --experiment <experiment-name> \
  --variant <variant-name> \
  --task-card <task-card-name> \
  --harness <harness-profile-name> \
  --label "operator-label" \
  --notes "Session purpose and context"
```

### What Gets Captured

The session creation command automatically captures:

1. **Git Metadata**:
   - Current branch
   - Current commit SHA
   - Dirty state (uncommitted changes)
   - Repository path

2. **Benchmark Metadata**:
   - Experiment ID
   - Variant ID
   - Task card ID
   - Harness profile

3. **Session Credentials**:
   - Session-scoped virtual key
   - Key alias for correlation

### Session ID

The returned `session_id` (UUID) is used for:
- All subsequent CLI commands
- Correlation in LiteLLM logs
- Prometheus metric labels
- Report generation

**Important**: Save this ID for the entire session lifecycle.

## Phase 4: Launch

### Rendering the Environment

Get the harness-specific environment snippet:

```bash
bench session env <session-id>
```

This outputs shell exports tailored to your harness profile.

### Applying the Environment

**Option 1: Direct Copy-Paste**
```bash
# Copy the output lines and paste them into your terminal
export ANTHROPIC_BASE_URL="http://localhost:4000"
export ANTHROPIC_API_KEY="sk-benchmark-<session-id>"
# ... (other exports)
```

**Option 2: Eval**
```bash
eval "$(bench session env <session-id>)"
```

### Verification Checklist

Before launching the harness, verify:

```bash
# 1. Base URL points to local proxy
echo $ANTHROPIC_BASE_URL  # Should be http://localhost:4000
echo $OPENAI_BASE_URL     # Should be http://localhost:4000

# 2. API key is the session virtual key
echo $ANTHROPIC_API_KEY   # Should start with sk-benchmark-
echo $OPENAI_API_KEY      # Should start with sk-benchmark-

# 3. Model is set correctly
echo $ANTHROPIC_MODEL     # Should match variant's model_alias
echo $OPENAI_MODEL        # Should match variant's model_alias

# 4. Test the virtual key
curl http://localhost:4000/key/info \
  -H "Authorization: Bearer $ANTHROPIC_API_KEY"
```

### Launching the Harness

Start your harness according to its documentation:

```bash
# Claude Code
claude

# OpenAI CLI
openai api chat.completions.create -m $OPENAI_MODEL
```

The harness will now route all inference traffic through the local LiteLLM proxy with session correlation tags.

## Phase 5: Execute

### Working on the Task

Follow the task card instructions. The system automatically captures:

- **Request-level**:
  - Latency (total, provider, proxy overhead)
  - TTFT (time to first token)
  - Token counts (input, output, cached, cache write)
  - Status codes and errors
  - Model and provider routing

- **Session-level**:
  - Duration
  - Request count and success rate
  - Aggregate throughput
  - Cache behavior

### Operator Responsibilities

During execution, the operator should:

1. **Follow the Task Card**: Stick to the defined objective and instructions
2. **Avoid Interventions**: Unless allowed by the task card
3. **Note Deviations**: Record any deviations from the plan
4. **Monitor Progress**: Check Grafana for unexpected patterns

### Adding Session Notes

Add notes during or after the session:

```bash
# Append notes
bench session add-notes <session-id> \
  --notes "Encountered unexpected error at step 3" \
  --append

# Replace notes
bench session add-notes <session-id> \
  --notes "Complete rewrite of session notes"
```

### Handling Errors

If the harness encounters errors:

1. **Check Proxy Logs**: 
   ```bash
   docker-compose logs litellm --tail 100
   ```

2. **Check Session Key**:
   ```bash
   curl http://localhost:4000/key/info \
     -H "Authorization: Bearer $SESSION_VIRTUAL_KEY"
   ```

3. **Check Provider Status**: Verify upstream provider is operational

4. **Record in Notes**: Document the error for later analysis

## Phase 6: Finalize

### Ending the Session

When the task is complete or the stop condition is reached:

```bash
bench session finalize <session-id> \
  --status completed \
  --outcome valid
```

### Status Values

- **completed**: Session finished normally
- **failed**: Session encountered unrecoverable errors
- **cancelled**: Session was manually terminated

### Outcome States

- **valid**: Session data is valid for comparisons (default for completed)
- **invalid**: Session completed but data should be excluded (e.g., operator deviated from task)
- **aborted**: Session was terminated before completion

When to mark as invalid:
- Repository state changed during session (not part of task)
- Harness was misconfigured (wrong base URL, key, or model)
- Operator deviated significantly from task card
- External interruptions affected the session

### Running Collection

If collection is not automatic:

```bash
# Collect LiteLLM request data
bench normalize litellm --session-id <session-id>

# Collect Prometheus metrics
bench normalize prometheus --session-id <session-id>

# Generate session rollups
bench rollup sessions --session-id <session-id>
```

### Verification

Verify data was captured correctly:

```bash
# Check session details
bench session show <session-id>

# View in Grafana
open http://localhost:3000
# Navigate to Benchmark folder > Experiment Summary
# Select your experiment and session
```

## Phase 7: Report

### Viewing Dashboards

Open Grafana to view live and historical metrics:

```bash
open http://localhost:3000
```

Key dashboards:
- **Live Request Latency**: Real-time request performance
- **Live TTFT Metrics**: Time to first token streaming
- **Live Error Rate**: Current error patterns
- **Experiment Summary**: Historical session comparisons

### Exporting Data

Export session data for external analysis:

```bash
# CSV format
bench export sessions \
  --experiment <experiment-name> \
  --format csv \
  --output sessions.csv

# JSON format
bench export sessions \
  --experiment <experiment-name> \
  --format json \
  --output sessions.json

# Parquet format (for data science tools)
bench export sessions \
  --experiment <experiment-name> \
  --format parquet \
  --output sessions.parquet
```

### Comparing Sessions

Generate comparison reports:

```bash
bench report compare \
  --experiment <experiment-name> \
  --output comparison.md
```

The report includes:
- Session counts per variant
- Latency statistics (median, p95)
- TTFT statistics
- Token counts and throughput
- Error rates
- Cache behavior

## Best Practices

### For Comparability

1. **Fix the Repository**: Use the same commit for all compared sessions
2. **Fix the Task Card**: Use the same task for all compared sessions
3. **Same Operator**: When possible, have the same operator run compared sessions
4. **Same Machine**: Run sessions on the same hardware and network
5. **Alternating Order**: Alternate variants to avoid time-of-day effects

### For Reproducibility

1. **Commit Configs**: Version control all config files
2. **Note Deviations**: Record anything that deviates from the plan
3. **Save Session IDs**: Keep a log of session IDs with context
4. **Export Data**: Export session data before cleaning up

### For Quality

1. **Validate Configs**: Always run `bench config validate` before sessions
2. **Verify Routing**: Confirm harness is routing through proxy before starting work
3. **Check Health**: Run `bench health check` periodically
4. **Review Early**: Check Grafana after the first few requests to catch issues early

## Session Workflow Checklist

### Before Session

- [ ] Docker and dependencies installed
- [ ] API keys configured
- [ ] Repository at correct commit
- [ ] Infrastructure services healthy
- [ ] Configs validated
- [ ] Experiment, variant, and task card selected

### During Session

- [ ] Session created with correct parameters
- [ ] Git metadata captured
- [ ] Environment applied to shell
- [ ] Harness routing verified through proxy
- [ ] Task card instructions followed
- [ ] Deviations recorded in notes
- [ ] Errors documented

### After Session

- [ ] Session finalized with correct status and outcome
- [ ] Collection and rollup completed
- [ ] Data verified in database
- [ ] Dashboards reviewed
- [ ] Data exported for analysis
- [ ] Session ID logged with context

## Common Patterns

### Quick Provider Comparison

Compare two providers on the same task:

```bash
# Session 1: Provider A
bench session create --experiment provider-comparison \
  --variant provider-a-model-x --task-card quick-task \
  --harness claude-code

# ... run session 1 ...

# Session 2: Provider B
bench session create --experiment provider-comparison \
  --variant provider-b-model-y --task-card quick-task \
  --harness claude-code

# ... run session 2 ...

# Compare
bench report compare --experiment provider-comparison
```

### Configuration Tuning

Test harness configuration changes:

```bash
# Session 1: Beta features off
bench session create --experiment beta-impact \
  --variant model-beta-off --task-card standard-task \
  --harness claude-code

# Session 2: Beta features on
bench session create --experiment beta-impact \
  --variant model-beta-on --task-card standard-task \
  --harness claude-code
```

### Multi-Session Reliability Test

Run multiple sessions per variant for variance analysis:

```bash
for i in {1..5}; do
  bench session create --experiment reliability-test \
    --variant standard-variant --task-card standard-task \
    --harness claude-code --label "run-$i"
  # ... run session ...
done
```

## See Also

- [docs/benchmark-methodology.md](benchmark-methodology.md) - Methodology for comparable sessions
- [docs/launch-recipes.md](launch-recipes.md) - Detailed harness setup instructions
- [docs/config-and-contracts.md](config-and-contracts.md) - Config schema reference
- [configs/litellm/README.md](../configs/litellm/README.md) - LiteLLM proxy configuration