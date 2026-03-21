# Benchmark Core

A harness-agnostic benchmarking system for comparing providers, models, and harnesses through a local LiteLLM proxy.

## Architecture

- **LiteLLM as single inference gateway** - All benchmarks route through local proxy
- **Session-scoped correlation** - Every session has unique correlation keys for traffic matching
- **Canonical data model** - Normalized storage for cross-harness comparisons

## Project Structure

```
src/
├── benchmark_core/          # Core domain logic
│   ├── models.py           # Canonical domain models
│   ├── config.py           # Pydantic settings
│   ├── db/
│   │   ├── connection.py   # SQLAlchemy async engine
│   │   └── models.py       # ORM models with FKs
│   ├── repositories/       # Data access layer (9 repositories)
│   └── services/           # Business logic layer
├── collectors/             # Data ingestion
│   ├── litellm_collector.py
│   ├── normalizer.py
│   ├── rollups.py
│   └── prometheus_collector.py
migrations/                 # Alembic migrations
tests/                     # Unit and integration tests
```

## Canonical Entities

- `provider` - Upstream inference provider definition
- `harness_profile` - How a harness is configured to talk to the proxy
- `variant` - Benchmarkable combination of provider/model/harness
- `experiment` - Named comparison grouping
- `task_card` - Benchmark task definition
- `session` - Interactive benchmark execution
- `request` - Normalized LLM call
- `metric_rollup` - Derived latency/throughput metrics

## Quick Start

```bash
# Install dependencies
pip install -e ".[dev]"

# Run migrations
alembic upgrade head

# Run tests
pytest tests/ -v
```

## Database Schema

All tables use UUID primary keys with proper foreign key relationships:

- `providers` - Inference providers
- `harness_profiles` - Harness connection configs
- `variants` - Provider + model + harness combinations
- `experiments` - Named comparison groups
- `task_cards` - Benchmark work definitions
- `sessions` - Interactive execution records
- `requests` - Normalized LLM calls
- `metric_rollups` - Aggregated statistics
- `artifacts` - Exported bundles

## Collectors

### LiteLLM Collector

Ingests raw request records from LiteLLM:
- Duplicate detection via `litellm_call_id`
- Correlation key extraction from tags
- Missing field diagnostics

### Request Normalizer

Maps raw requests to canonical format:
- Session/variant joining
- Canonical field validation
- Unmapped row surfacing

### Metric Rollups

Computes aggregated statistics:
- Request-level: latency, ttft, tokens/sec
- Session-level: request_count, success_rate, median/p95 latency
- Variant-level: session_count, session_success_rate
- Experiment-level: variant comparison

## Configuration

See `docs/config-and-contracts.md` for configuration schema.

## License

Internal use only.
