# Sessionless Usage Metrics Implementation Plan

## Purpose

This file defines a development task plan for adding a sessionless usage-observability mode to StackPerf.

The new mode should let operators route traffic through LiteLLM and measure usage and performance over time, broken down by API key and model, without requiring an experiment, variant, task card, or benchmark session to be created first.

The plan follows the repository's implementation-plan task style and is suitable for conversion into Linear parent issues and sub-issues.

## Product Goal

StackPerf should support two complementary operating modes:

- Benchmark mode: session-first comparisons across experiments, variants, harnesses, providers, and task cards.
- Usage mode: long-running API-key and model accounting for request volume, token usage, spend, latency, TTFT, errors, and cache behavior.

Usage mode must not weaken the benchmark-session invariants. Benchmark sessions remain the stricter comparison workflow. Sessionless traffic should still be observable, attributable, redacted, and queryable.

## Current State Summary

- `requests.session_id` is required, so normalized request rows must belong to a benchmark session.
- `proxy_credentials` are session-scoped and one-to-one with `sessions`.
- LiteLLM spend-log collection and normalization commands require a `session_id`.
- Request rows already capture model, provider, latency, TTFT, prompt tokens, completion tokens, errors, and cache hits.
- Dashboards already contain some live Prometheus panels grouped by `requested_model`.
- API and reporting surfaces filter by session, provider, and model, but not by API key, key alias, LiteLLM key ID, team, customer, or owner.
- The current credential implementation is split between a placeholder service and the fuller `services_abc.CredentialService`; the CLI path does not consistently issue real LiteLLM virtual keys for sessions.

## Recommended Architecture

Add usage-observability tables and services beside the existing benchmark-session schema.

Do not make the existing `requests` table sessionless as the first step. Instead:

- Keep `requests` as the benchmark-session request table.
- Add a first-class proxy/API key registry for both session and non-session keys.
- Add a `usage_requests` table for all LiteLLM traffic, with optional benchmark session linkage.
- Build shared normalization helpers so session request ingestion and usage request ingestion do not diverge.
- Add rollups and query surfaces grouped by API key, key alias, model, provider, and time bucket.

This lets usage mode land without breaking existing benchmark reports, while still allowing future consolidation once the shape is proven.

## Non-Negotiable Constraints

- LiteLLM remains the single inference gateway.
- Raw API key secrets must never be stored in the benchmark database, logs, exports, or dashboards.
- Prompt and response content remain off by default.
- Usage records must preserve stable request IDs and stable key attribution when LiteLLM exposes them.
- Collection and rollup jobs must be idempotent.
- Sessionless mode must not allow benchmark traffic to bypass session creation when the operator is intentionally running a benchmark comparison.
- If traffic contains benchmark session metadata, usage mode must preserve it and make it joinable back to benchmark sessions.
- Usage mode must work even when session metadata is absent.

## Conversion Rules

- Local planning IDs such as `SESSIONLESS-001` are document-scoped identifiers.
- They are not issue IDs and must not be copied into created Linear issue titles.
- Create parent issues first.
- Create sub-issues second.
- Apply blockers using actual Linear issue IDs after issue creation.
- After issue creation, rewrite issue bodies so document-scoped blockers are replaced with created Linear issue IDs or canonical Linear URLs.

## Task Schema

```yaml
id: string
parent_issue: string
issue_type: parent_issue|sub_issue
title: string
priority: P0|P1|P2|P3
estimate_points: integer
blockers: [local planning ids]
labels: [strings]
repo_areas: [paths or modules]
docs: [repo docs to read before implementation]
definition_of_ready:
  - concrete prerequisite
scope:
  in_scope:
    - item
  out_of_scope:
    - item
deliverables:
  - artifact
acceptance_criteria:
  - testable statement
test_plan:
  unit:
    - test
  integration:
    - test
  manual:
    - check
notes:
  - implementation note
```

## Parent Issue Summary

| Parent issue | Goal | Priority |
|---|---|---|
| Sessionless Usage Architecture and Contracts | Define the sessionless usage mode, source fields, invariants, and operator workflows. | P0 |
| API Key Registry and Credential Operations | Make LiteLLM virtual keys first-class, non-secret accounting entities independent of sessions. | P0 |
| Usage Ingestion and Normalization | Ingest all-key LiteLLM usage records idempotently, with optional session linkage. | P0 |
| Usage Rollups, API, and Exports | Provide queryable usage/performance summaries by API key, model, and time window. | P1 |
| Usage Dashboards, Security, and Operations | Add Grafana dashboards, redaction controls, retention rules, and end-to-end docs. | P1 |

## Parent Issues

### Sessionless Usage Architecture and Contracts

```yaml
title: Sessionless Usage Architecture and Contracts
issue_type: parent_issue
priority: P0
labels: [usage, architecture, contracts]
docs:
  - AGENTS.md
  - README.md
  - docs/architecture.md
  - docs/config-and-contracts.md
  - docs/data-model-and-observability.md
goal:
  - define usage mode as a sibling to benchmark mode
  - document key attribution fields and source-of-truth boundaries
  - preserve existing benchmark-session invariants
```

### API Key Registry and Credential Operations

```yaml
title: API Key Registry and Credential Operations
issue_type: parent_issue
priority: P0
labels: [usage, credentials, litellm]
docs:
  - AGENTS.md
  - docs/config-and-contracts.md
  - docs/security-and-operations.md
goal:
  - create persistent non-secret metadata for LiteLLM virtual keys
  - support sessionless key creation, listing, revocation, and environment rendering
  - make benchmark session credentials use the same underlying key service
```

### Usage Ingestion and Normalization

```yaml
title: Usage Ingestion and Normalization
issue_type: parent_issue
priority: P0
labels: [usage, collectors, normalization]
docs:
  - AGENTS.md
  - docs/data-model-and-observability.md
  - docs/security-and-operations.md
goal:
  - collect LiteLLM spend logs across all keys
  - normalize records into sessionless usage rows
  - preserve optional joins to benchmark sessions
```

### Usage Rollups, API, and Exports

```yaml
title: Usage Rollups, API, and Exports
issue_type: parent_issue
priority: P1
labels: [usage, reporting, api, exports]
docs:
  - README.md
  - docs/data-model-and-observability.md
  - docs/operator-workflow.md
goal:
  - summarize usage by API key, model, provider, and time bucket
  - expose usage metrics through CLI, API, and exports
  - keep historical usage queries independent from live Prometheus label availability
```

### Usage Dashboards, Security, and Operations

```yaml
title: Usage Dashboards, Security, and Operations
issue_type: parent_issue
priority: P1
labels: [usage, grafana, security, operations]
docs:
  - AGENTS.md
  - docs/security-and-operations.md
  - configs/grafana/provisioning/
goal:
  - provide practical usage dashboards
  - enforce redaction and retention for key metadata and usage artifacts
  - document sessionless operator workflows end to end
```

## Sub-Issues

## SESSIONLESS-001

```yaml
id: SESSIONLESS-001
parent_issue: Sessionless Usage Architecture and Contracts
issue_type: sub_issue
title: Define sessionless usage mode contracts and ADRs
priority: P0
estimate_points: 3
blockers: []
labels: [usage, architecture, docs]
repo_areas:
  - docs/architecture.md
  - docs/config-and-contracts.md
  - docs/data-model-and-observability.md
  - docs/decisions/
docs:
  - AGENTS.md
  - docs/architecture.md
  - docs/config-and-contracts.md
  - docs/data-model-and-observability.md
definition_of_ready:
  - Existing benchmark-session invariants are understood and preserved.
  - The distinction between benchmark mode and usage mode is written down.
scope:
  in_scope:
    - Document usage mode as a sibling workflow to benchmark sessions.
    - Define canonical terms for proxy key, key alias, usage request, usage rollup, owner, team, customer, and time bucket.
    - Add an ADR choosing a separate usage table over making benchmark `requests.session_id` nullable in the first iteration.
    - Document how session metadata remains optional usage metadata, not a prerequisite.
  out_of_scope:
    - Database migrations.
    - CLI or API implementation.
deliverables:
  - Updated architecture and data model docs.
  - ADR for sessionless usage storage strategy.
  - ADR or contract section for API key attribution and redaction.
acceptance_criteria:
  - Docs explicitly state that usage mode works without experiment, variant, task card, or session.
  - Docs explicitly state that benchmark mode still requires session creation before harness traffic.
  - Docs identify the stable joins between usage rows, proxy keys, LiteLLM logs, and optional benchmark sessions.
test_plan:
  unit: []
  integration: []
  manual:
    - Review docs for consistency with AGENTS.md non-negotiable rules.
    - Confirm a future coding agent can identify all required schema fields from the docs alone.
notes:
  - This is a planning and contract task; it should land before schema work.
```

## SESSIONLESS-002

```yaml
id: SESSIONLESS-002
parent_issue: Sessionless Usage Architecture and Contracts
issue_type: sub_issue
title: Inventory LiteLLM spend log fields and Prometheus labels for API key attribution
priority: P0
estimate_points: 3
blockers: [SESSIONLESS-001]
labels: [usage, litellm, research]
repo_areas:
  - src/collectors/litellm_collector.py
  - src/collectors/prometheus_collector.py
  - configs/grafana/provisioning/dashboards/
  - configs/prometheus/prometheus.yml
docs:
  - README.md
  - docs/data-model-and-observability.md
  - configs/litellm/README.md
definition_of_ready:
  - Local LiteLLM stack can be started or representative spend-log fixtures are available.
scope:
  in_scope:
    - Capture representative `/spend/logs` records for successful, failed, streaming, and cached requests.
    - Identify fields for request ID, key ID, key alias, hashed user API key, model, requested model, provider, cost, token counts, latency, TTFT, status, and errors.
    - Identify which Prometheus labels are available for model, key, route, status, and provider.
    - Create sanitized fixtures for unit tests.
  out_of_scope:
    - Implementing the collector.
    - Persisting new records.
deliverables:
  - Sanitized spend-log fixture files under tests or docs.
  - Field mapping notes in docs/data-model-and-observability.md or a dedicated docs reference.
  - A gap list for fields LiteLLM does not expose reliably.
acceptance_criteria:
  - Field mapping distinguishes stable required fields from best-effort optional fields.
  - Sensitive fields are redacted or synthetic in committed fixtures.
  - The plan identifies whether API-key-level live Prometheus dashboards are possible or whether Postgres must be used for key breakdowns.
test_plan:
  unit:
    - Fixture loading smoke test if fixtures are placed under tests.
  integration:
    - Optional local call to `/spend/logs` against running LiteLLM.
  manual:
    - Verify no real API keys or prompt/response content are committed.
notes:
  - Bias toward using LiteLLM key IDs or aliases instead of raw key hashes when available.
```

## SESSIONLESS-003

```yaml
id: SESSIONLESS-003
parent_issue: Sessionless Usage Architecture and Contracts
issue_type: sub_issue
title: Add usage-mode config contracts for proxy keys and default usage policies
priority: P1
estimate_points: 3
blockers: [SESSIONLESS-001]
labels: [usage, config]
repo_areas:
  - src/benchmark_core/config.py
  - src/benchmark_core/config_loader.py
  - configs/
  - tests/unit/test_config.py
docs:
  - docs/config-and-contracts.md
  - docs/security-and-operations.md
definition_of_ready:
  - Usage-mode terminology is defined.
scope:
  in_scope:
    - Define optional config for named proxy key profiles or usage policies.
    - Include allowed models, budget defaults, TTL defaults, owner labels, team/customer metadata, and redaction/retention policy references.
    - Validate that raw API key secrets are not accepted in tracked config.
  out_of_scope:
    - LiteLLM key creation.
    - Database persistence.
deliverables:
  - Typed config models and loader support.
  - Example config files or documented config snippets.
  - Unit tests for valid and invalid usage policy config.
acceptance_criteria:
  - Config validation rejects secrets in usage policy files.
  - Config validation accepts policy metadata needed for sessionless key creation.
  - Existing provider, variant, experiment, and task-card config loading remains compatible.
test_plan:
  unit:
    - `make test-unit` for config tests.
    - Add tests for missing required usage policy fields and secret-like values.
  integration:
    - `uv run benchmark config validate` covers usage config if examples are added.
  manual:
    - Inspect generated docs for operator clarity.
notes:
  - Keep usage policy config optional so current benchmark workflows do not require migration.
```

## SESSIONLESS-004

```yaml
id: SESSIONLESS-004
parent_issue: API Key Registry and Credential Operations
issue_type: sub_issue
title: Add proxy key registry schema, migrations, repositories, and domain models
priority: P0
estimate_points: 5
blockers: [SESSIONLESS-001, SESSIONLESS-002]
labels: [usage, database, credentials]
repo_areas:
  - src/benchmark_core/db/models.py
  - migrations/versions/
  - src/benchmark_core/models.py
  - src/benchmark_core/repositories/
  - tests/unit/test_repositories.py
  - tests/validation/test_migrations.py
docs:
  - docs/data-model-and-observability.md
  - docs/security-and-operations.md
definition_of_ready:
  - Key attribution fields from LiteLLM are mapped.
  - Redaction boundary for proxy key metadata is documented.
scope:
  in_scope:
    - Add a non-secret `proxy_keys` or equivalent table for LiteLLM virtual key metadata.
    - Store LiteLLM key ID, key alias, owner label, team/customer metadata, purpose, allowed models, budget fields, status, created/revoked/expires timestamps, and metadata JSON.
    - Support optional links to benchmark session credentials for session-created keys.
    - Add indexes for key alias, LiteLLM key ID, owner/team/customer, and active status.
  out_of_scope:
    - Storing raw API key values.
    - Usage request storage.
deliverables:
  - Alembic migration.
  - SQLAlchemy model.
  - Pydantic/domain model.
  - Repository CRUD and lookup helpers.
  - Migration and repository tests.
acceptance_criteria:
  - Raw API key secret is not present in any ORM/domain persistence field.
  - Key alias and LiteLLM key ID lookups are covered by tests.
  - Existing `proxy_credentials` and session tests remain green.
test_plan:
  unit:
    - Repository create/get/list/revoke tests.
    - Domain model redaction tests if serialization is added.
  integration:
    - Migration validation test creates and rolls forward schema.
  manual:
    - Inspect generated migration for indexes and no secret columns.
notes:
  - Consider retaining existing `proxy_credentials` for session-specific metadata while linking to the new key registry.
```

## SESSIONLESS-005

```yaml
id: SESSIONLESS-005
parent_issue: API Key Registry and Credential Operations
issue_type: sub_issue
title: Implement sessionless LiteLLM key creation, listing, revocation, and info commands
priority: P0
estimate_points: 5
blockers: [SESSIONLESS-003, SESSIONLESS-004]
labels: [usage, cli, credentials, litellm]
repo_areas:
  - src/benchmark_core/services/credential_service.py
  - src/benchmark_core/services_abc.py
  - src/cli/commands/
  - tests/unit/test_credential_service.py
  - tests/unit/test_cli.py
docs:
  - docs/config-and-contracts.md
  - docs/operator-workflow.md
  - docs/security-and-operations.md
definition_of_ready:
  - Proxy key registry schema is available.
  - Usage policy config fields are available or an explicit CLI-only fallback is chosen.
scope:
  in_scope:
    - Add `benchmark key create`, `benchmark key list`, `benchmark key info`, and `benchmark key revoke` commands.
    - Create LiteLLM virtual keys with stable aliases and metadata without requiring a session.
    - Persist only non-secret key metadata locally.
    - Render generic OpenAI-compatible and harness-profile-based environment snippets for sessionless keys.
  out_of_scope:
    - Benchmark session creation changes except shared service extraction.
    - Usage ingestion.
deliverables:
  - Credential service implementation for sessionless keys.
  - CLI commands and tests.
  - Respx/httpx tests for LiteLLM API success and failure paths.
acceptance_criteria:
  - A key can be created with owner/team/customer metadata and optional model allow-list.
  - The returned key secret is displayed once and never persisted.
  - Listing keys shows alias, owner/team/customer, status, allowed models, creation, expiration, and revocation state.
  - Revocation marks local metadata inactive and attempts LiteLLM deletion.
test_plan:
  unit:
    - Mock LiteLLM `/key/generate`, `/key/info`, and `/key/delete` tests.
    - CLI command tests with synthetic metadata.
  integration:
    - Optional local stack smoke test creates and revokes a test key.
  manual:
    - Confirm no command prints hidden stored secrets after creation.
notes:
  - Unify the placeholder `benchmark_core/services/credential_service.py` with the fuller service currently exported from `services_abc.py`.
```

## SESSIONLESS-006

```yaml
id: SESSIONLESS-006
parent_issue: API Key Registry and Credential Operations
issue_type: sub_issue
title: Wire benchmark session creation to real LiteLLM credential issuance
priority: P1
estimate_points: 5
blockers: [SESSIONLESS-004, SESSIONLESS-005]
labels: [sessions, credentials, litellm]
repo_areas:
  - src/cli/commands/session.py
  - src/benchmark_core/services/session_service.py
  - src/benchmark_core/services/credential_service.py
  - src/benchmark_core/db/models.py
  - tests/unit/test_session_commands.py
  - tests/unit/test_services.py
docs:
  - docs/operator-workflow.md
  - docs/config-and-contracts.md
definition_of_ready:
  - Shared credential service supports non-secret persistence.
scope:
  in_scope:
    - Ensure `benchmark session create` can issue a real LiteLLM virtual key when configured with a master key.
    - Persist key alias and LiteLLM key ID through the shared proxy key registry and existing session credential reference.
    - Make `benchmark session env` render the actual newly issued session key during creation or provide a secure one-time output path.
    - Keep a dry-run or no-LiteLLM fallback explicit and labeled as non-routable.
  out_of_scope:
    - Changing benchmark task-card or variant semantics.
    - Sessionless usage ingestion.
deliverables:
  - Updated session creation workflow.
  - Tests covering successful issuance, LiteLLM failures, and explicit fallback behavior.
  - Updated operator docs.
acceptance_criteria:
  - Session credentials are not silently invented as `sk-benchmark-{session_id}` when real issuance is expected.
  - Session metadata is attached to the LiteLLM virtual key.
  - Existing benchmark session creation tests pass with updated expectations.
test_plan:
  unit:
    - Mocked LiteLLM session credential issuance tests.
    - CLI tests for missing master key and explicit fallback.
  integration:
    - Optional local stack session creation smoke test.
  manual:
    - Create a session and verify `/key/info` recognizes the rendered key.
notes:
  - This task improves existing benchmark correctness and reduces divergence with sessionless key handling.
```

## SESSIONLESS-007

```yaml
id: SESSIONLESS-007
parent_issue: Usage Ingestion and Normalization
issue_type: sub_issue
title: Add usage request schema, migration, repositories, and indexes
priority: P0
estimate_points: 8
blockers: [SESSIONLESS-002, SESSIONLESS-004]
labels: [usage, database, normalization]
repo_areas:
  - src/benchmark_core/db/models.py
  - migrations/versions/
  - src/benchmark_core/models.py
  - src/benchmark_core/repositories/
  - tests/unit/test_repositories.py
  - tests/validation/test_migrations.py
docs:
  - docs/data-model-and-observability.md
  - docs/security-and-operations.md
definition_of_ready:
  - LiteLLM spend-log fields have been mapped.
  - Proxy key registry exists.
scope:
  in_scope:
    - Add `usage_requests` or equivalent table for all LiteLLM traffic.
    - Include request/log ID, timestamp, key alias, LiteLLM key ID, optional proxy key FK, optional benchmark session ID, provider, route, requested model, resolved model, token fields, cached token fields, cost/spend, latency, TTFT, status/error fields, cache flags, and safe metadata.
    - Add uniqueness and idempotency constraints around stable request/log IDs.
    - Add indexes for time, key alias/key ID, model, provider, optional session ID, and error state.
  out_of_scope:
    - Collector implementation.
    - API endpoints.
deliverables:
  - Alembic migration.
  - ORM and domain model.
  - Repository create-many idempotent helper.
  - Tests for duplicate handling and optional session linkage.
acceptance_criteria:
  - Usage rows can be persisted without a benchmark session.
  - Usage rows can optionally link to a benchmark session when metadata is present.
  - Duplicate LiteLLM request IDs do not create duplicate usage rows.
  - No prompt/response content fields are stored by default.
test_plan:
  unit:
    - Repository create/get/list by key/model/time tests.
    - Idempotent insert tests.
  integration:
    - Migration validation test.
  manual:
    - Inspect table definition for indexes and redaction boundary.
notes:
  - Use Postgres-friendly types and avoid JSON-only storage for fields needed by common filters.
```

## SESSIONLESS-008

```yaml
id: SESSIONLESS-008
parent_issue: Usage Ingestion and Normalization
issue_type: sub_issue
title: Implement sessionless LiteLLM usage collector and normalizer
priority: P0
estimate_points: 8
blockers: [SESSIONLESS-002, SESSIONLESS-007]
labels: [usage, collectors, litellm]
repo_areas:
  - src/collectors/litellm_collector.py
  - src/collectors/normalize_requests.py
  - src/collectors/
  - tests/unit/test_collectors.py
  - tests/unit/test_normalize_requests.py
docs:
  - docs/data-model-and-observability.md
  - docs/security-and-operations.md
definition_of_ready:
  - Usage request schema exists.
  - Sanitized spend-log fixtures are available.
scope:
  in_scope:
    - Add a collector path that fetches LiteLLM spend logs without requiring a session ID.
    - Normalize all usage fields into `usage_requests`.
    - Resolve key attribution to the proxy key registry when possible.
    - Preserve optional benchmark metadata such as benchmark session ID, experiment ID, variant ID, task-card ID, and harness profile.
    - Produce reconciliation diagnostics for unmapped or partially mapped rows.
  out_of_scope:
    - Time-window rollups.
    - Grafana dashboards.
deliverables:
  - Usage normalizer.
  - Usage collector service.
  - Reconciliation report for all-key collection.
  - Fixture-driven unit tests.
acceptance_criteria:
  - Normalizer maps key alias or key ID, model, tokens, cost, latency, TTFT, errors, and timestamps from fixtures.
  - Records missing stable request IDs are skipped with diagnostics.
  - Records without session metadata are still accepted.
  - Records with session metadata preserve join fields.
test_plan:
  unit:
    - Fixture tests for success, failure, cached, streaming, and missing-field records.
    - Redaction tests for metadata.
  integration:
    - Optional local stack collection dry run against `/spend/logs`.
  manual:
    - Review diagnostics output for actionable field names.
notes:
  - Prefer shared extraction helpers for latency, tokens, cache, and error fields so benchmark request normalization stays consistent.
```

## SESSIONLESS-009

```yaml
id: SESSIONLESS-009
parent_issue: Usage Ingestion and Normalization
issue_type: sub_issue
title: Add usage ingestion watermarks and CLI collection commands
priority: P0
estimate_points: 5
blockers: [SESSIONLESS-008]
labels: [usage, cli, collectors]
repo_areas:
  - src/cli/commands/collect.py
  - src/cli/main.py
  - src/benchmark_core/db/models.py
  - src/benchmark_core/repositories/
  - tests/unit/test_cli.py
  - tests/unit/test_collectors.py
docs:
  - docs/operator-workflow.md
  - docs/data-model-and-observability.md
definition_of_ready:
  - Sessionless usage collector can normalize and persist rows.
scope:
  in_scope:
    - Add `benchmark collect usage` or equivalent command with start/end/lookback options.
    - Add persistent ingest watermarks keyed by source and collection scope.
    - Support dry-run and reconciliation report output.
    - Ensure repeated collection does not duplicate usage rows.
  out_of_scope:
    - Scheduled daemon or automation.
    - Dashboards.
deliverables:
  - CLI command.
  - Watermark persistence model or repository.
  - Unit tests for dry-run, lookback, and idempotency behavior.
acceptance_criteria:
  - Operators can collect all-key usage for a time window without supplying a session ID.
  - Re-running the same time window is idempotent.
  - Dry-run reports mapped/unmapped counts without writing rows.
  - Command errors clearly distinguish LiteLLM connectivity, auth, and normalization problems.
test_plan:
  unit:
    - CLI command tests with mocked collector.
    - Watermark update tests.
  integration:
    - Optional local stack collect command against test traffic.
  manual:
    - Run dry-run with no traffic and verify empty windows are handled gracefully.
notes:
  - Keep the existing `collect litellm <session_id>` command available for benchmark mode.
```

## SESSIONLESS-010

```yaml
id: SESSIONLESS-010
parent_issue: Usage Ingestion and Normalization
issue_type: sub_issue
title: Reconcile benchmark request ingestion with sessionless usage ingestion
priority: P1
estimate_points: 5
blockers: [SESSIONLESS-008, SESSIONLESS-009]
labels: [usage, sessions, normalization]
repo_areas:
  - src/collectors/litellm_collector.py
  - src/collectors/normalize_requests.py
  - src/benchmark_core/repositories/request_repository.py
  - tests/unit/test_collectors.py
  - tests/unit/test_normalize_requests.py
docs:
  - docs/data-model-and-observability.md
  - docs/benchmark-methodology.md
definition_of_ready:
  - Both session and usage ingestion paths exist.
scope:
  in_scope:
    - Share normalization helpers for timestamps, model/provider fields, latency, TTFT, tokens, cache, and errors.
    - Define whether benchmark session collection also writes usage rows, or whether all-key usage collection is responsible for the usage table.
    - Ensure request IDs and optional session IDs let operators reconcile the two tables.
    - Add consistency tests for the same fixture normalized through both paths.
  out_of_scope:
    - Removing the existing benchmark `requests` table.
    - Large-scale data backfill.
deliverables:
  - Shared normalization helpers.
  - Consistency tests.
  - Documentation of dual-write or single-source behavior.
acceptance_criteria:
  - The same raw request produces equivalent metric fields in benchmark and usage records.
  - Existing benchmark collectors remain compatible.
  - A usage row with benchmark metadata can be joined back to its session.
test_plan:
  unit:
    - Shared helper tests.
    - Cross-normalizer fixture tests.
  integration:
    - Run benchmark collection tests and usage collection tests together.
  manual:
    - Inspect docs for clear operator expectations.
notes:
  - This task prevents quiet drift between "benchmark metrics" and "usage metrics."
```

## SESSIONLESS-011

```yaml
id: SESSIONLESS-011
parent_issue: Usage Rollups, API, and Exports
issue_type: sub_issue
title: Implement usage rollups by API key, model, provider, and time bucket
priority: P1
estimate_points: 8
blockers: [SESSIONLESS-007, SESSIONLESS-009]
labels: [usage, rollups, reporting]
repo_areas:
  - src/collectors/rollup_job.py
  - src/collectors/metric_catalog.py
  - src/benchmark_core/repositories/rollup_repository.py
  - src/reporting/
  - tests/unit/test_rollup_repository.py
  - tests/unit/test_reporting.py
docs:
  - docs/data-model-and-observability.md
definition_of_ready:
  - Usage requests are persisted with indexed key, model, and timestamp fields.
scope:
  in_scope:
    - Compute rollups for key+model+time_bucket and key-only/model-only summaries.
    - Include request count, error count/rate, prompt/completion/total tokens, cost, cache counts, p50/p95/p99 latency, p50/p95 TTFT, and output tokens/sec where derivable.
    - Store rollups in a way that distinguishes usage dimensions from benchmark session/variant/experiment dimensions.
    - Make rollup computation idempotent for a fixed window.
  out_of_scope:
    - Grafana dashboard JSON.
    - External billing reconciliation against provider invoices.
deliverables:
  - Rollup job implementation.
  - Repository helpers for usage rollups.
  - Unit tests for aggregation math and idempotency.
acceptance_criteria:
  - Rollups can be recomputed for the same time bucket without duplicate or contradictory rows.
  - Empty windows do not corrupt aggregates.
  - Percentiles and token totals are tested with deterministic fixture data.
test_plan:
  unit:
    - Aggregation tests for multiple keys and models.
    - Error-rate, cost, and percentile tests.
  integration:
    - End-to-end from fixture usage rows to persisted rollups.
  manual:
    - Compare sample SQL aggregates against rollup output.
notes:
  - If extending `rollups`, add dimension names such as `usage_key_model_hour`; otherwise consider a dedicated usage rollup table.
```

## SESSIONLESS-012

```yaml
id: SESSIONLESS-012
parent_issue: Usage Rollups, API, and Exports
issue_type: sub_issue
title: Add usage reporting service and API endpoints
priority: P1
estimate_points: 5
blockers: [SESSIONLESS-011]
labels: [usage, api, reporting]
repo_areas:
  - src/api/main.py
  - src/api/schemas.py
  - src/reporting/
  - tests/unit/test_api.py
  - tests/unit/test_reporting.py
docs:
  - docs/data-model-and-observability.md
  - README.md
definition_of_ready:
  - Usage rollups or query helpers are available.
scope:
  in_scope:
    - Add endpoints for usage summaries by key, model, provider, and time range.
    - Add detail endpoint for usage requests with filters for key alias, model, provider, error, session ID, and time range.
    - Return totals, rates, latency/TTFT summaries, token counts, and cost fields where available.
    - Use parameterized SQLAlchemy queries only.
  out_of_scope:
    - Authentication for hosted multi-user deployment.
    - Grafana dashboards.
deliverables:
  - Pydantic schemas.
  - API routes.
  - Reporting query helpers.
  - API and reporting tests.
acceptance_criteria:
  - API can answer "usage by API key and model for a time range."
  - API can list raw usage requests without exposing secrets or content.
  - Invalid filters return clear errors.
  - Existing session/request/rollup endpoints remain compatible.
test_plan:
  unit:
    - FastAPI endpoint tests using seeded usage rows.
    - Query helper tests for filters and ordering.
  integration:
    - Optional local API smoke test after seeded data.
  manual:
    - Inspect OpenAPI schema for usable field descriptions.
notes:
  - Prefer stable external IDs and key aliases in responses; avoid exposing raw LiteLLM internals unless needed.
```

## SESSIONLESS-013

```yaml
id: SESSIONLESS-013
parent_issue: Usage Rollups, API, and Exports
issue_type: sub_issue
title: Add usage CLI summaries and exports
priority: P1
estimate_points: 5
blockers: [SESSIONLESS-011]
labels: [usage, cli, exports]
repo_areas:
  - src/cli/commands/
  - src/reporting/export_service.py
  - tests/unit/test_export_commands.py
  - tests/unit/test_export_service.py
docs:
  - docs/operator-workflow.md
  - docs/security-and-operations.md
definition_of_ready:
  - Usage reporting service or query helpers are available.
scope:
  in_scope:
    - Add `benchmark usage summary` with filters for start, end, key alias, model, provider, and grouping.
    - Add `benchmark usage export` for CSV and JSON.
    - Include redaction by default for sensitive key metadata.
    - Include machine-readable output suitable for billing or cost review workflows.
  out_of_scope:
    - Provider invoice reconciliation.
    - Interactive terminal UI.
deliverables:
  - CLI commands.
  - Export service additions.
  - Tests for CLI output and redaction.
acceptance_criteria:
  - CLI can print usage by API key and model for a requested window.
  - Exported files include token totals, request counts, errors, latency summaries, and cost when available.
  - Sensitive fields are redacted by default and require explicit opt-in where allowed.
test_plan:
  unit:
    - CLI command tests with seeded usage rows.
    - Export serialization tests.
  integration:
    - Optional local command against fixture data.
  manual:
    - Validate CSV headers are stable and documented.
notes:
  - Keep output names distinct from benchmark session export names to avoid confusion.
```

## SESSIONLESS-014

```yaml
id: SESSIONLESS-014
parent_issue: Usage Dashboards, Security, and Operations
issue_type: sub_issue
title: Add Grafana dashboards for usage by API key and model
priority: P1
estimate_points: 5
blockers: [SESSIONLESS-011, SESSIONLESS-012]
labels: [usage, grafana, dashboards]
repo_areas:
  - configs/grafana/provisioning/dashboards/
  - configs/grafana/provisioning/datasources/
  - scripts/
  - tests/validation/
docs:
  - README.md
  - docs/data-model-and-observability.md
definition_of_ready:
  - Usage tables and rollups have stable query fields.
scope:
  in_scope:
    - Add a Postgres-backed usage dashboard grouped by key alias and model.
    - Include request rate, token totals, cost, error rate, latency percentiles, TTFT percentiles, and recent failures.
    - Add dashboard variables for key alias, owner/team/customer, provider, model, and time range.
    - Add seed data or validation script for local dashboard verification.
  out_of_scope:
    - Hosted Grafana auth.
    - Real-time key-level Prometheus panels if LiteLLM does not expose key labels.
deliverables:
  - Dashboard JSON.
  - Optional seed script or validation fixtures.
  - Dashboard documentation.
acceptance_criteria:
  - Dashboard loads from provisioning in the local stack.
  - Panels show non-empty data with seeded usage rows.
  - No panel exposes raw key secrets or prompt/response content.
test_plan:
  unit: []
  integration:
    - Dashboard JSON validation if an existing validation pattern is available.
    - Optional local Grafana provisioning smoke test.
  manual:
    - Open Grafana and verify filters, panels, and seeded data.
notes:
  - Use Postgres for key-level historical breakdowns unless SESSIONLESS-002 proves Prometheus labels are sufficient.
```

## SESSIONLESS-015

```yaml
id: SESSIONLESS-015
parent_issue: Usage Dashboards, Security, and Operations
issue_type: sub_issue
title: Add security, redaction, and retention controls for usage mode
priority: P1
estimate_points: 5
blockers: [SESSIONLESS-004, SESSIONLESS-007, SESSIONLESS-013]
labels: [usage, security, retention]
repo_areas:
  - src/benchmark_core/security.py
  - src/collectors/retention_cleanup.py
  - src/reporting/export_service.py
  - tests/unit/test_security.py
  - tests/unit/test_retention_cleanup.py
docs:
  - docs/security-and-operations.md
definition_of_ready:
  - Usage schema and exports are implemented.
scope:
  in_scope:
    - Extend redaction filters to usage metadata and key metadata.
    - Add retention cleanup support for usage requests and usage rollups.
    - Document which fields are safe, sensitive, or forbidden.
    - Ensure exports and API responses do not expose raw keys or captured content.
  out_of_scope:
    - Hosted multi-tenant authorization.
    - Deleting LiteLLM's own upstream logs.
deliverables:
  - Redaction and retention implementation.
  - Tests for usage metadata redaction.
  - Updated security and operations docs.
acceptance_criteria:
  - Secret-like values in usage metadata are redacted before persistence or export.
  - Retention cleanup can remove usage records by age without affecting benchmark sessions unless explicitly requested.
  - Export tests prove sensitive fields are absent by default.
test_plan:
  unit:
    - Redaction tests for API keys, bearer tokens, database URLs, and nested metadata.
    - Retention cleanup tests for usage tables.
  integration:
    - Optional dry-run retention command against seeded usage data.
  manual:
    - Review docs and sample exports for secret leakage.
notes:
  - Keep deletion behavior explicit; usage retention should not surprise benchmark operators.
```

## SESSIONLESS-016

```yaml
id: SESSIONLESS-016
parent_issue: Usage Dashboards, Security, and Operations
issue_type: sub_issue
title: Document and verify the end-to-end sessionless usage workflow
priority: P1
estimate_points: 5
blockers: [SESSIONLESS-005, SESSIONLESS-009, SESSIONLESS-012, SESSIONLESS-013, SESSIONLESS-014, SESSIONLESS-015]
labels: [usage, docs, validation]
repo_areas:
  - README.md
  - docs/operator-workflow.md
  - docs/launch-recipes.md
  - docs/security-and-operations.md
  - tests/integration/
  - scripts/
docs:
  - AGENTS.md
  - README.md
  - docs/operator-workflow.md
definition_of_ready:
  - Core sessionless usage workflow is implemented.
scope:
  in_scope:
    - Add quick-start docs for creating a sessionless proxy key, routing traffic, collecting usage, summarizing usage, exporting data, and opening dashboards.
    - Add troubleshooting for missing key attribution, missing model labels, empty spend logs, and LiteLLM auth failures.
    - Add an end-to-end smoke test or validation script using synthetic or mocked LiteLLM logs.
    - Update README documentation map.
  out_of_scope:
    - Production deployment guide beyond local-first usage.
    - Provider billing reconciliation.
deliverables:
  - Updated README and operator docs.
  - Validation script or integration test.
  - Documented example commands.
acceptance_criteria:
  - A new operator can follow docs to use StackPerf without creating a benchmark session.
  - The validation path proves key+model usage summaries are produced.
  - Existing benchmark quick start remains accurate.
test_plan:
  unit: []
  integration:
    - End-to-end smoke test or validation script.
    - `make quality` when feasible.
  manual:
    - Follow the documented quick start from a local stack.
notes:
  - This task is the release gate for calling sessionless usage mode operator-ready.
```

## Milestones

### M1: Contracts and Source Field Discovery

Goal: Make the design explicit and remove uncertainty around LiteLLM key attribution.

Tasks:

- SESSIONLESS-001
- SESSIONLESS-002
- SESSIONLESS-003

### M2: Key Registry and Credential Operations

Goal: Make API keys first-class non-secret accounting entities independent of sessions.

Tasks:

- SESSIONLESS-004
- SESSIONLESS-005
- SESSIONLESS-006

### M3: Sessionless Usage Ingestion

Goal: Persist all-key LiteLLM usage records with optional benchmark session linkage.

Tasks:

- SESSIONLESS-007
- SESSIONLESS-008
- SESSIONLESS-009
- SESSIONLESS-010

### M4: Usage Metrics Surfaces

Goal: Summarize and expose usage by API key, model, provider, and time range.

Tasks:

- SESSIONLESS-011
- SESSIONLESS-012
- SESSIONLESS-013

### M5: Dashboards, Security, and Release Readiness

Goal: Make the feature safe, visible, documented, and operator-ready.

Tasks:

- SESSIONLESS-014
- SESSIONLESS-015
- SESSIONLESS-016

## Critical Path

```text
SESSIONLESS-001
  -> SESSIONLESS-002
  -> SESSIONLESS-004
  -> SESSIONLESS-007
  -> SESSIONLESS-008
  -> SESSIONLESS-009
  -> SESSIONLESS-011
  -> SESSIONLESS-012
  -> SESSIONLESS-016
```

Parallelizable work:

- SESSIONLESS-003 can proceed after SESSIONLESS-001.
- SESSIONLESS-005 can proceed after SESSIONLESS-003 and SESSIONLESS-004.
- SESSIONLESS-006 can proceed after SESSIONLESS-005.
- SESSIONLESS-013 can proceed after SESSIONLESS-011.
- SESSIONLESS-014 can proceed after SESSIONLESS-011 and SESSIONLESS-012.
- SESSIONLESS-015 can proceed after schema, ingestion, and export surfaces exist.

## Definition of Done for the Initiative

- A sessionless proxy key can be created without creating a benchmark session.
- Traffic through that key can be collected from LiteLLM spend logs.
- Usage records persist without a session ID and are attributed to an API key and model.
- Usage summaries are available by API key, model, provider, and time window.
- Latency, TTFT, request count, token counts, cost/spend when available, error rate, and cache metrics are exposed.
- Benchmark session workflows still require session creation and continue to pass existing tests.
- No raw API keys, prompts, or responses are stored or exported by default.
- Dashboards and docs cover the sessionless workflow end to end.

