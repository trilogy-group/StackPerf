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

## Definition of ready for coding agents

Before starting a sub-issue, read:

- `README.md`
- this file
- the referenced docs listed in the sub-issue body

If the task depends on schema, config, or reporting behavior, also read the relevant contract document in `docs/` before coding.
