# AGENTS.md

This file provides persistent context for AI agents working on this repository.

## Project Overview

<!-- Describe your project here. What does it do? What problem does it solve? -->

## Technology Stack

<!-- List your technologies: languages, frameworks, databases, etc. -->

- Language: <!-- e.g., Python 3.11, TypeScript 5.0 -->
- Framework: <!-- e.g., FastAPI, React, Next.js -->
- Database: <!-- e.g., PostgreSQL, SQLite -->
- Testing: <!-- e.g., pytest, vitest -->

## Coding Standards

### General

- Keep functions small and focused
- Write self-documenting code with clear names
- Add comments only for "why", not "what"
- Follow existing patterns in the codebase

### Formatting

<!-- Add your formatting commands -->

- Format command: `<!-- e.g., make format, npm run format -->`
- Lint command: `<!-- e.g., make lint, npm run lint -->`
- Type check: `<!-- e.g., make typecheck, npm run typecheck -->`

### Testing

<!-- Add your testing requirements -->

- Test command: `<!-- e.g., make test, npm test -->`
- Coverage requirement: <!-- e.g., 80%, 100% for critical paths -->
- Test location: `<!-- e.g., tests/, __tests__/ -->`

## Project Structure

```
<!-- Customize this structure for your project -->
.
├── src/                    # Source code
├── tests/                  # Test files
├── docs/                   # Documentation
├── configs/                # Configuration files
├── scripts/                # Utility scripts
├── AGENTS.md               # This file
├── WORKFLOW.md             # OpenSymphony configuration
└── README.md               # Project readme
```

## Key Directories

<!-- Document important directories -->

- `src/` - <!-- Main source code -->
- `tests/` - <!-- Test files -->
- `docs/` - <!-- Documentation -->

## Dependencies

### Runtime

<!-- List key runtime dependencies -->

### Development

<!-- List key dev dependencies -->

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `EXAMPLE_VAR` | <!-- Description --> | Yes/No |

## Local Development Setup

<!-- Steps to set up local development -->

```bash
# Example setup steps
# 1. Install dependencies
# 2. Configure environment
# 3. Run tests
```

## PR Requirements

Before submitting a PR:

1. All tests pass
2. Code is formatted
3. Lint checks pass
4. New code has tests
5. Documentation updated if needed

## Architecture Decisions

<!-- Document key architecture decisions -->

### Decision 1

- **Context**: <!-- Why this decision was needed -->
- **Decision**: <!-- What was decided -->
- **Consequences**: <!-- Impact and trade-offs -->

## Known Issues / Gotchas

<!-- Document any quirks or known issues -->

## References

<!-- Links to relevant external documentation -->

- [Framework Docs](https://example.com)
- [API Reference](https://example.com/api)

## Preserved Existing AGENTS.md

The following content was preserved from the repository's previous `AGENTS.md` during `opensymphony init`.

# AGENTS.md

## Project mission

Build a harness-agnostic benchmarking system that compares providers, models, harnesses, and harness configurations by routing all benchmark traffic through a local LiteLLM proxy and storing normalized benchmark records in a project-owned database.

The system is designed for interactive benchmark sessions. The project does not run a harness-specific automation engine in the core path. It registers sessions, issues proxy credentials, renders harness environment snippets, ingests telemetry, normalizes data, and serves reports.

## Non-negotiable architecture rules

1. LiteLLM is the single inference gateway.
2. Every benchmark session must have a benchmark-owned `session_id`.
3. Every session must be correlated to LiteLLM traffic through a session-scoped proxy credential and benchmark tags.
4. The benchmark database is the source of truth for reporting.
5. LiteLLM tables, logs, and Prometheus metrics are source inputs, not the reporting schema.
6. Prompt and response content are off by default.
7. The core code path must remain harness-agnostic.
8. Session creation must capture benchmark metadata before any harness traffic starts.
9. Collection and normalization jobs must be idempotent.
10. Any change that weakens correlation, reproducibility, or redaction is a design bug.

## What belongs in this repository

Build and maintain:

- infrastructure config for local LiteLLM, Postgres, Prometheus, and Grafana
- typed config schemas for providers, harness profiles, variants, experiments, and task cards
- benchmark session registry and lifecycle services
- session credential issuance and harness env rendering
- LiteLLM request collection and normalization
- Prometheus metric collection and rollups
- comparison queries, exports, and dashboards
- security controls around secrets, retention, and redaction

Do not build product-specific logic into the core path. If two harnesses need different environment variable names, solve that through harness profiles and rendering templates, not bespoke control flow.

## Canonical entities

Use the terms below consistently across code, docs, and schema:

- `provider`: upstream inference provider definition
- `harness_profile`: how a harness is configured to talk to the proxy
- `variant`: a benchmarkable combination of provider route, model, harness profile, and harness settings
- `experiment`: a named comparison grouping that contains one or more variants
- `task_card`: the benchmark task definition used for comparable sessions
- `session`: one interactive benchmark session under one variant and one task card
- `request`: one normalized LLM call observed through LiteLLM
- `metric_rollup`: derived latency, throughput, error, and cache metrics for a request, session, or comparison group
- `artifact`: exported report or raw benchmark bundle

## Required correlation keys

Every session must provide enough information to join all collected records. Preserve these keys whenever available:

- benchmark `session_id`
- benchmark `experiment_id`
- benchmark `variant_id`
- benchmark `task_card_id`
- LiteLLM virtual key ID and key alias
- request tags written by the session manager
- LiteLLM call ID or equivalent request ID
- upstream provider request ID when exposed
- timestamps in UTC

If a new collector does not preserve at least one stable request key and one stable session key, it is incomplete.

## Data handling rules

- Content capture is disabled by default.
- Store metadata, timings, counts, cache counters, request IDs, and routing fields.
- Any feature that persists prompts or responses must be guarded by an explicit config flag and redaction controls.
- Secrets must never be committed, logged, or copied into artifacts.
- Session credentials must be short-lived and scoped.

## Delivery rules

Every implementation change must:

- include typed config validation where applicable
- include unit tests for parsing, normalization, or aggregation logic
- include integration tests for service boundaries when practical
- update docs when behavior or contracts change
- preserve idempotent ingestion and deterministic rollups

## Repository conventions

Recommended module boundaries:

- `src/benchmark_core/`
  - config models
  - domain models
  - repositories
  - services
- `src/cli/`
  - operator commands
  - config validation
  - session lifecycle commands
  - export commands
- `src/collectors/`
  - LiteLLM collection
  - Prometheus collection
  - normalization jobs
  - rollup jobs
- `src/reporting/`
  - comparison services
  - serialization
  - dashboard query helpers
- `src/api/`
  - HTTP endpoints over the canonical query model

## Session lifecycle invariants

A valid session flow is:

1. operator chooses variant and task card
2. system creates a session row
3. system creates a session-scoped proxy credential and alias
4. system stores session metadata including repo path, git commit, and selected harness profile
5. system renders the harness env snippet
6. operator launches the harness manually
7. collectors ingest and normalize traffic
8. session is finalized with end time and summary rollups

Any shortcut that allows harness traffic before session registration breaks comparability.

## Definition of done

A sub-issue is done when:

- scope is implemented
- acceptance criteria pass
- tests are green
- docs are updated
- the change can be understood by another engineer without hidden local context

## Development environment

The project uses `uv` for dependency management and provides a Makefile for common tasks.

### Quick start

```bash
# Install all dependencies including dev tools
make install-dev

# Run full quality check (lint + type-check + test)
make quality

# Run individual checks
make lint         # Run ruff linter
make format       # Run ruff formatter
make type-check   # Run mypy type checker
make test         # Run all tests
```

### Available Makefile commands

- `make install` - Install production dependencies with uv
- `make install-dev` - Install all dependencies including dev tools
- `make sync` - Sync dependencies from pyproject.toml
- `make lint` - Run ruff linter
- `make format` - Run ruff formatter
- `make format-check` - Check formatting without modifying files
- `make type-check` - Run mypy type checker
- `make test` - Run all tests
- `make test-unit` - Run unit tests only
- `make test-integration` - Run integration tests only
- `make test-cov` - Run tests with coverage report
- `make quality` - Run full quality check (lint + type-check + test)
- `make clean` - Clean build artifacts and cache files
- `make dev-setup` - Complete setup for new development environment
- `make dev-check` - Quick check before committing

### Project structure

```
├── pyproject.toml          # Project configuration and dependencies
├── Makefile                # Development task runner
├── src/
│   ├── benchmark_core/     # Core domain (models, config, services, repositories)
│   ├── cli/                  # CLI commands using Typer
│   ├── collectors/           # LiteLLM and Prometheus data collection
│   ├── reporting/            # Comparison services and serialization
│   └── api/                  # FastAPI HTTP endpoints
└── tests/
    ├── unit/                 # Unit tests for each package
    └── integration/          # Integration tests
```

### Tooling configuration

- **Ruff**: Configured in `pyproject.toml` for linting and formatting (Python 3.11+ target)
- **mypy**: Type checking with strict settings (disallow_untyped_defs)
- **pytest**: Test discovery and execution with asyncio support
- **pytest-cov**: Coverage reporting

## Definition of ready for coding agents

Before starting a sub-issue, read:

- `README.md`
- this file
- the referenced docs listed in the sub-issue body

If the task depends on schema, config, or reporting behavior, also read the relevant contract document in `docs/` before coding.
