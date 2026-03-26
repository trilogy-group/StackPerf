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
