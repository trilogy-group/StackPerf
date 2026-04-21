# Implementation Plan

## Purpose

This file defines a markdown task plan that can be converted into Linear parent issues and sub-issues.

## Conversion rules

- Local planning IDs such as `BENCH-001` are document-scoped identifiers.
- They are not issue IDs and must never be copied into created Linear issue titles, descriptions, dependency fields, or related-issue text.
- Create parent issues first.
- Create sub-issues second.
- Apply blockers through Linear blocker metadata using the created Linear issue IDs.
- After issue creation, rewrite all issue bodies so any local planning-ID references are replaced with the actual created Linear issue IDs or canonical Linear URLs.
- Use `parent issue` and `sub-issue` terminology only.

## Task schema

```yaml
id: string                    # local planning ID only
parent_issue: string          # exact parent issue title
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

## Parent issue summary

| Parent issue | Goal | Priority |
|---|---|---|
| Repository and Local Stack Foundation | Establish the local stack, repository skeleton, and typed configuration basis. | P0 |
| Canonical Data Store and Collection Pipeline | Build the benchmark database, collectors, normalization, and rollups. | P0 |
| Session Management and Harness Profiles | Create session lifecycle, session-scoped credentials, and harness env rendering. | P0 |
| Query API, Exports, and Dashboards | Provide comparison queries, exports, and dashboards over canonical data. | P1 |
| Security, Operations, and Delivery Quality | Add redaction, retention, CI checks, and operational safeguards. | P1 |

## Parent issues

### Repository and Local Stack Foundation

```yaml
title: Repository and Local Stack Foundation
issue_type: parent_issue
priority: P0
labels: [foundation, infra, config]
docs:
  - README.md
  - AGENTS.md
  - docs/architecture.md
  - docs/config-and-contracts.md
goal:
  - create a reproducible local benchmarking stack
  - establish typed config contracts for providers, harness profiles, variants, experiments, and task cards
```

### Canonical Data Store and Collection Pipeline

```yaml
title: Canonical Data Store and Collection Pipeline
issue_type: parent_issue
priority: P0
labels: [database, collectors, observability]
docs:
  - AGENTS.md
  - docs/architecture.md
  - docs/data-model-and-observability.md
goal:
  - create canonical benchmark storage
  - ingest and normalize LiteLLM and Prometheus data
  - compute request-, session-, variant-, and experiment-level metrics
```

### Session Management and Harness Profiles

```yaml
title: Session Management and Harness Profiles
issue_type: parent_issue
priority: P0
labels: [sessions, harnesses, cli]
docs:
  - AGENTS.md
  - docs/architecture.md
  - docs/config-and-contracts.md
  - docs/benchmark-methodology.md
goal:
  - create session lifecycle commands and services
  - issue session-scoped proxy credentials
  - render harness-specific environment snippets from harness profiles
```

### Query API, Exports, and Dashboards

```yaml
title: Query API, Exports, and Dashboards
issue_type: parent_issue
priority: P1
labels: [reporting, dashboards, api]
docs:
  - README.md
  - docs/architecture.md
  - docs/data-model-and-observability.md
goal:
  - expose historical benchmark results
  - provide comparison reports and dashboards
  - support structured exports for external analysis
```

### Security, Operations, and Delivery Quality

```yaml
title: Security, Operations, and Delivery Quality
issue_type: parent_issue
priority: P1
labels: [security, ci, operations]
docs:
  - AGENTS.md
  - docs/security-and-operations.md
goal:
  - enforce redaction and secret safety
  - add CI checks and operator safeguards
  - keep the stack reproducible and auditable
```

## Sub-issues

## BENCH-001

```yaml
id: BENCH-001
parent_issue: Repository and Local Stack Foundation
issue_type: sub_issue
title: Bootstrap repository, tooling, and package skeleton
priority: P0
estimate_points: 3
blockers: []
labels: [foundation, python, devex]
repo_areas: [pyproject.toml, src/, tests/, Makefile]
docs:
  - README.md
  - AGENTS.md
  - docs/architecture.md
definition_of_ready:
  - repository name is chosen
  - Python version is agreed
scope:
  in_scope:
    - create uv-managed Python project
    - add linting, typing, testing, and formatting tooling
    - create top-level package layout for core modules
    - add Makefile or task runner commands
  out_of_scope:
    - benchmark business logic
deliverables:
  - pyproject.toml
  - src package skeleton
  - tests skeleton
  - developer command set
acceptance_criteria:
  - fresh clone can sync dependencies successfully
  - lint, type-check, and test commands run locally
  - package layout matches documented architecture
test_plan:
  unit:
    - import smoke tests for each top-level package
  integration:
    - run full quality command locally or in CI
  manual:
    - verify onboarding commands from a clean checkout
notes:
  - keep project config minimal but strict
```

## BENCH-002

```yaml
id: BENCH-002
parent_issue: Repository and Local Stack Foundation
issue_type: sub_issue
title: Create local Docker Compose stack for LiteLLM, Postgres, Prometheus, and Grafana
priority: P0
estimate_points: 5
blockers: [BENCH-001]
labels: [infra, docker, observability]
repo_areas: [docker-compose.yml, configs/litellm/, configs/prometheus/, configs/grafana/]
docs:
  - README.md
  - docs/architecture.md
  - docs/security-and-operations.md
definition_of_ready:
  - local ports and bind policy are agreed
  - service versions are selected
scope:
  in_scope:
    - compose services for LiteLLM, Postgres, Prometheus, and Grafana
    - local persistence volumes
    - healthchecks
    - local-only defaults
  out_of_scope:
    - benchmark application logic
deliverables:
  - docker-compose.yml
  - example env file
  - Prometheus scrape config
  - Grafana provisioning stubs
acceptance_criteria:
  - one command starts the local stack
  - LiteLLM is healthy
  - Prometheus scrapes LiteLLM metrics
  - Grafana starts with a working datasource
test_plan:
  unit:
    - validate config files when templated
  integration:
    - compose up smoke test
  manual:
    - open Grafana and verify datasource health
notes:
  - keep the benchmark app outside Compose so it can inspect the local filesystem directly
```

## BENCH-003

```yaml
id: BENCH-003
parent_issue: Repository and Local Stack Foundation
issue_type: sub_issue
title: Implement typed config schemas and validation for providers, harness profiles, variants, experiments, and task cards
priority: P0
estimate_points: 5
blockers: [BENCH-001]
labels: [config, pydantic]
repo_areas: [src/benchmark_core/config/, configs/providers/, configs/harnesses/, configs/variants/, configs/experiments/, configs/task-cards/]
docs:
  - AGENTS.md
  - docs/config-and-contracts.md
  - docs/benchmark-methodology.md
definition_of_ready:
  - canonical config fields are approved
scope:
  in_scope:
    - typed config models
    - YAML loading and validation
    - deterministic precedence rules
    - actionable validation errors
  out_of_scope:
    - session creation and runtime services
deliverables:
  - config models
  - config loader
  - example config files
acceptance_criteria:
  - invalid configs fail with precise field-level errors
  - valid configs load into typed objects
  - examples cover at least one Anthropic-surface harness profile and one OpenAI-surface harness profile
test_plan:
  unit:
    - parse valid fixtures for every config type
    - reject invalid enum, duplicate-name, and missing-field cases
  integration:
    - CLI validate command over the config tree
  manual:
    - review example configs for readability
notes:
  - use harness profiles instead of harness-specific code paths
```

## BENCH-004

```yaml
id: BENCH-004
parent_issue: Repository and Local Stack Foundation
issue_type: sub_issue
title: Add example LiteLLM route configuration and local operator docs
priority: P0
estimate_points: 3
blockers: [BENCH-002, BENCH-003]
labels: [litellm, config, docs]
repo_areas: [configs/litellm/, README.md, docs/config-and-contracts.md]
docs:
  - README.md
  - docs/config-and-contracts.md
  - docs/security-and-operations.md
definition_of_ready:
  - at least one provider route and two model aliases are chosen for examples
scope:
  in_scope:
    - LiteLLM config examples for provider routes and model aliases
    - local operator instructions for bootstrapping provider secrets
    - example route names that line up with variant configs
  out_of_scope:
    - dynamic provider discovery
deliverables:
  - example LiteLLM config files
  - documented route naming convention
acceptance_criteria:
  - example configs load in LiteLLM without syntax errors
  - route names and model aliases match benchmark config examples
  - docs show how to point a harness at the proxy using session credentials
test_plan:
  unit:
    - config file lint or schema validation if available
  integration:
    - start LiteLLM with example route config
  manual:
    - inspect route names and model aliases for consistency
notes:
  - use stable route names because they become comparison dimensions
```

## BENCH-005

```yaml
id: BENCH-005
parent_issue: Canonical Data Store and Collection Pipeline
issue_type: sub_issue
title: Create benchmark database schema and migration system
priority: P0
estimate_points: 5
blockers: [BENCH-001, BENCH-003]
labels: [database, migrations, storage]
repo_areas: [src/benchmark_core/db/, migrations/]
docs:
  - AGENTS.md
  - docs/data-model-and-observability.md
  - docs/architecture.md
definition_of_ready:
  - canonical entities and required joins are approved
scope:
  in_scope:
    - ORM models or equivalent schema layer
    - migrations
    - separate canonical schema from LiteLLM-owned storage
  out_of_scope:
    - collectors and rollups
deliverables:
  - migration baseline
  - schema models
  - database session utilities
acceptance_criteria:
  - schema can be created from scratch
  - schema can be migrated forward consistently
  - required tables exist for providers, harness profiles, variants, experiments, task cards, sessions, requests, rollups, and artifacts
test_plan:
  unit:
    - model constraint and enum tests
  integration:
    - migration up/down smoke test against local Postgres
  manual:
    - inspect created schema and indexes
notes:
  - keep raw-source reference columns from the start
```

## BENCH-006

```yaml
id: BENCH-006
parent_issue: Canonical Data Store and Collection Pipeline
issue_type: sub_issue
title: Implement repository layer and benchmark metadata services
priority: P0
estimate_points: 5
blockers: [BENCH-005]
labels: [domain, storage]
repo_areas: [src/benchmark_core/repositories/, src/benchmark_core/services/]
docs:
  - AGENTS.md
  - docs/data-model-and-observability.md
  - docs/architecture.md
definition_of_ready:
  - database schema is merged
scope:
  in_scope:
    - repository methods for canonical entities
    - create, read, update, and finalize session workflows
    - experiment, variant, and task-card lookup services
  out_of_scope:
    - collection jobs
deliverables:
  - repository classes or data access layer
  - service layer for benchmark metadata
acceptance_criteria:
  - services can create and finalize sessions safely
  - repository methods preserve referential integrity
  - duplicate session identifiers are rejected
test_plan:
  unit:
    - repository and service tests with transaction rollbacks
  integration:
    - service tests against local Postgres
  manual:
    - create and inspect a sample session row
notes:
  - session lifecycle methods must be idempotent where retry is plausible
```

## BENCH-007

```yaml
id: BENCH-007
parent_issue: Canonical Data Store and Collection Pipeline
issue_type: sub_issue
title: Build LiteLLM collection job for raw request records and correlation keys
priority: P0
estimate_points: 5
blockers: [BENCH-002, BENCH-005, BENCH-006]
labels: [collectors, litellm, ingestion]
repo_areas: [src/collectors/litellm.py, src/benchmark_core/services/]
docs:
  - AGENTS.md
  - docs/architecture.md
  - docs/data-model-and-observability.md
definition_of_ready:
  - chosen LiteLLM ingestion source is documented
  - required raw fields are listed
scope:
  in_scope:
    - collection from LiteLLM request data source
    - capture of key alias, request IDs, routing fields, timings, token counts, and status
    - idempotent ingest cursor or watermark handling
  out_of_scope:
    - normalization into reporting tables
deliverables:
  - raw collection job
  - raw-ingest watermark tracking
  - collection diagnostics
acceptance_criteria:
  - collector ingests raw request records without duplication
  - collected rows preserve session correlation keys when present
  - collector exposes clear diagnostics for missing fields
test_plan:
  unit:
    - raw-record parser tests with success and error fixtures
  integration:
    - ingest sample LiteLLM records into local Postgres
  manual:
    - inspect one collected request end to end
notes:
  - do not assume prompt or response content is present
```

## BENCH-008

```yaml
id: BENCH-008
parent_issue: Canonical Data Store and Collection Pipeline
issue_type: sub_issue
title: Normalize LiteLLM request data into canonical request tables
priority: P0
estimate_points: 5
blockers: [BENCH-005, BENCH-006, BENCH-007]
labels: [normalization, requests, storage]
repo_areas: [src/collectors/normalize_requests.py, src/benchmark_core/services/]
docs:
  - AGENTS.md
  - docs/config-and-contracts.md
  - docs/data-model-and-observability.md
definition_of_ready:
  - canonical request contract is frozen for MVP
scope:
  in_scope:
    - mapping raw LiteLLM fields into canonical requests
    - correlation to sessions, variants, experiments, and harness profiles
    - error handling for missing or partial correlation metadata
  out_of_scope:
    - Prometheus rollups
deliverables:
  - request normalizer job
  - normalized request write path
  - reconciliation report for unmapped rows
acceptance_criteria:
  - normalized requests contain required canonical fields
  - requests join cleanly to sessions and variants
  - unmapped rows are surfaced with actionable diagnostics
test_plan:
  unit:
    - normalization fixtures across multiple protocol surfaces
  integration:
    - raw-to-canonical normalization smoke test against local DB
  manual:
    - inspect one session's normalized requests
notes:
  - missing session correlation should fail loudly in diagnostics, not silently disappear
```

## BENCH-009

```yaml
id: BENCH-009
parent_issue: Canonical Data Store and Collection Pipeline
issue_type: sub_issue
title: Add Prometheus collection and derived metric rollups
priority: P0
estimate_points: 5
blockers: [BENCH-002, BENCH-005, BENCH-006]
labels: [prometheus, metrics, rollups]
repo_areas: [src/collectors/prometheus.py, src/collectors/rollups.py]
docs:
  - docs/data-model-and-observability.md
  - docs/benchmark-methodology.md
  - docs/architecture.md
definition_of_ready:
  - required metric names and rollup formulas are agreed
scope:
  in_scope:
    - Prometheus query layer or scrape snapshot collection
    - computation of request, session, variant, and experiment rollups
    - storage of derived metrics in canonical rollup tables
  out_of_scope:
    - dashboard implementation
deliverables:
  - Prometheus collector
  - rollup job
  - rollup metric catalog
acceptance_criteria:
  - rollups compute median and p95 latency statistics correctly
  - session and variant summaries are queryable from canonical storage
  - collector handles empty windows without corrupting aggregates
test_plan:
  unit:
    - rollup math tests with deterministic fixtures
  integration:
    - Prometheus-backed summary generation against local stack
  manual:
    - compare a sample session summary with raw request rows
notes:
  - document which metrics come from LiteLLM raw data versus Prometheus-derived calculations
```

## BENCH-010

```yaml
id: BENCH-010
parent_issue: Session Management and Harness Profiles
issue_type: sub_issue
title: Implement session manager service and CLI commands
priority: P0
estimate_points: 5
blockers: [BENCH-003, BENCH-005, BENCH-006]
labels: [sessions, cli, lifecycle]
repo_areas: [src/cli/, src/benchmark_core/services/]
docs:
  - AGENTS.md
  - docs/config-and-contracts.md
  - docs/benchmark-methodology.md
definition_of_ready:
  - canonical session lifecycle states are approved
scope:
  in_scope:
    - session create command
    - session finalize command
    - capture of repo root, git branch, commit SHA, and dirty state
    - operator-facing session status output
  out_of_scope:
    - request ingestion
deliverables:
  - session lifecycle service
  - CLI commands for session creation and finalization
acceptance_criteria:
  - session creation writes benchmark metadata before harness launch
  - session finalization records status and end time
  - git metadata is captured from the active repository
test_plan:
  unit:
    - service tests for valid and invalid lifecycle transitions
  integration:
    - CLI create/finalize flow against local DB
  manual:
    - create a session inside a git repo and verify captured metadata
notes:
  - session creation must not require the harness to be running already
```

## BENCH-011

```yaml
id: BENCH-011
parent_issue: Session Management and Harness Profiles
issue_type: sub_issue
title: Implement session-scoped proxy credential issuance and aliasing
priority: P0
estimate_points: 5
blockers: [BENCH-002, BENCH-006, BENCH-010]
labels: [sessions, auth, litellm]
repo_areas: [src/benchmark_core/services/, src/cli/]
docs:
  - AGENTS.md
  - docs/architecture.md
  - docs/security-and-operations.md
definition_of_ready:
  - chosen credential issuance path is documented
scope:
  in_scope:
    - create one proxy credential per session
    - assign stable key alias and metadata tags
    - persist correlation metadata in the benchmark DB
    - expire or deactivate credentials on session finalization when appropriate
  out_of_scope:
    - harness env rendering
deliverables:
  - credential issuance service
  - key aliasing convention
  - session credential persistence
acceptance_criteria:
  - every created session gets a unique proxy credential or equivalent session-isolated credential path
  - key alias and metadata can be joined back to the session
  - secrets are not persisted in plaintext beyond the intended storage boundary
test_plan:
  unit:
    - credential metadata builder tests
  integration:
    - create and revoke a session credential against local LiteLLM configuration
  manual:
    - verify the session credential works against the proxy
notes:
  - prefer the most universal correlation path across harnesses
```

## BENCH-012

```yaml
id: BENCH-012
parent_issue: Session Management and Harness Profiles
issue_type: sub_issue
title: Render harness-specific environment snippets from harness profiles
priority: P0
estimate_points: 5
blockers: [BENCH-003, BENCH-010, BENCH-011]
labels: [harnesses, config, cli]
repo_areas: [src/benchmark_core/services/rendering.py, src/cli/]
docs:
  - docs/config-and-contracts.md
  - docs/architecture.md
  - docs/security-and-operations.md
definition_of_ready:
  - at least one Anthropic-surface and one OpenAI-surface harness profile are defined
scope:
  in_scope:
    - shell export rendering
    - dotenv rendering
    - application of variant env overrides
    - rendering of model alias and proxy base URL
  out_of_scope:
    - launching harness processes
deliverables:
  - env rendering service
  - shell and dotenv renderers
  - profile validation checks
acceptance_criteria:
  - rendered output uses the correct variable names for each harness profile
  - variant overrides are included deterministically
  - rendered output never writes secrets into tracked files
test_plan:
  unit:
    - rendering tests for multiple harness profiles
  integration:
    - session create command emits usable shell and dotenv outputs
  manual:
    - source a rendered snippet and confirm a harness can reach the proxy
notes:
  - keep harness differences declarative in profile configs
```

## BENCH-013

```yaml
id: BENCH-013
parent_issue: Session Management and Harness Profiles
issue_type: sub_issue
title: Add session notes, outcome states, and artifact registry
priority: P1
estimate_points: 3
blockers: [BENCH-006, BENCH-010]
labels: [sessions, metadata, artifacts]
repo_areas: [src/benchmark_core/services/, src/cli/, src/reporting/]
docs:
  - docs/data-model-and-observability.md
  - docs/benchmark-methodology.md
  - docs/security-and-operations.md
definition_of_ready:
  - outcome-state vocabulary is approved
scope:
  in_scope:
    - session notes support
    - explicit completion, aborted, and invalid states
    - artifact registration for exports and session bundles
  out_of_scope:
    - dashboard rendering
deliverables:
  - session note fields and CLI hooks
  - artifact registry service
acceptance_criteria:
  - operators can finalize a session with a valid outcome state
  - exports can be attached to a session or experiment as artifacts
  - invalid sessions remain visible for audit but can be excluded from comparisons
test_plan:
  unit:
    - outcome-state validation tests
  integration:
    - session finalize with note and artifact registration
  manual:
    - inspect stored notes and artifact entries
notes:
  - keep note storage concise and safe for internal use
```

## BENCH-014

```yaml
id: BENCH-014
parent_issue: Query API, Exports, and Dashboards
issue_type: sub_issue
title: Build query API for experiments, variants, sessions, requests, and rollups
priority: P1
estimate_points: 5
blockers: [BENCH-006, BENCH-008, BENCH-009]
labels: [api, queries, reporting]
repo_areas: [src/api/, src/reporting/]
docs:
  - docs/data-model-and-observability.md
  - docs/architecture.md
  - AGENTS.md
definition_of_ready:
  - query shapes for primary views are approved
scope:
  in_scope:
    - list and detail endpoints or service methods for experiments, variants, sessions, requests, and rollups
    - filtering by provider, model, harness, task card, and time window
    - stable serialization contracts
  out_of_scope:
    - UI implementation
deliverables:
  - query API implementation
  - response schemas
acceptance_criteria:
  - core benchmark entities are queryable by ID and by filter
  - request and session views expose canonical fields consistently
  - API contracts are documented and test-covered
test_plan:
  unit:
    - response-schema and filtering tests
  integration:
    - end-to-end query tests against seeded local DB
  manual:
    - inspect session detail and request list responses
notes:
  - optimize for stable machine-readable output
```

## BENCH-015

```yaml
id: BENCH-015
parent_issue: Query API, Exports, and Dashboards
issue_type: sub_issue
title: Implement comparison service and experiment summary views
priority: P1
estimate_points: 5
blockers: [BENCH-009, BENCH-013, BENCH-014]
labels: [reporting, comparisons, summaries]
repo_areas: [src/reporting/]
docs:
  - docs/benchmark-methodology.md
  - docs/data-model-and-observability.md
  - docs/architecture.md
definition_of_ready:
  - summary metrics and comparison dimensions are approved
scope:
  in_scope:
    - experiment-level comparison queries
    - summary views by provider, model, harness profile, and variant
    - exclusion of invalid sessions from comparison results
  out_of_scope:
    - dashboard provisioning
deliverables:
  - comparison service
  - summary queries or materialized views
acceptance_criteria:
  - users can compare variants inside one experiment across key latency and error metrics
  - summary views exclude invalid sessions correctly
  - result ordering and filtering are deterministic
test_plan:
  unit:
    - summary math tests
  integration:
    - compare seeded variants with repeated sessions
  manual:
    - verify one experiment comparison table against raw session data
notes:
  - preserve session counts and exclusion counts in every summary result
```

## BENCH-016

```yaml
id: BENCH-016
parent_issue: Query API, Exports, and Dashboards
issue_type: sub_issue
title: Add structured export commands for session and experiment data
priority: P1
estimate_points: 3
blockers: [BENCH-013, BENCH-014, BENCH-015]
labels: [exports, cli, data]
repo_areas: [src/cli/, src/reporting/]
docs:
  - docs/data-model-and-observability.md
  - docs/security-and-operations.md
  - README.md
definition_of_ready:
  - export formats and artifact naming convention are approved
scope:
  in_scope:
    - CSV export
    - JSON export
    - Parquet export if the dependency footprint is acceptable
    - artifact registry integration
  out_of_scope:
    - notebook templates
deliverables:
  - export commands
  - artifact write path
acceptance_criteria:
  - session and experiment exports contain stable canonical fields
  - exported artifacts are registered in the benchmark database
  - exports exclude secrets and respect redaction defaults
test_plan:
  unit:
    - export serialization tests
  integration:
    - export a seeded experiment and verify artifact registration
  manual:
    - open exported files and verify field names
notes:
  - keep column names friendly for downstream analysis tools
```

## BENCH-017

```yaml
id: BENCH-017
parent_issue: Query API, Exports, and Dashboards
issue_type: sub_issue
title: Provision Grafana dashboards for live and historical benchmark views
priority: P1
estimate_points: 5
blockers: [BENCH-002, BENCH-009, BENCH-015]
labels: [grafana, dashboards, observability]
repo_areas: [dashboards/, configs/grafana/]
docs:
  - README.md
  - docs/architecture.md
  - docs/data-model-and-observability.md
definition_of_ready:
  - core dashboard panels are agreed
scope:
  in_scope:
    - live request latency panels
    - TTFT panels
    - error-rate panels
    - experiment summary panels backed by canonical data or exported snapshots
  out_of_scope:
    - hosted multi-user dashboard deployment
deliverables:
  - provisioned Grafana dashboards
  - datasource configuration
acceptance_criteria:
  - Grafana loads benchmark dashboards on startup
  - dashboards show live LiteLLM metrics and historical benchmark summaries
  - panel labels and variable selectors match canonical benchmark dimensions
test_plan:
  unit:
    - dashboard JSON lint or schema validation if available
  integration:
    - dashboard provisioning smoke test in local stack
  manual:
    - open panels and verify data appears for seeded sessions
notes:
  - prioritize readability over panel count
```

## BENCH-018

```yaml
id: BENCH-018
parent_issue: Query API, Exports, and Dashboards
issue_type: sub_issue
title: Write operator workflow documentation and harness launch recipes
priority: P1
estimate_points: 3
blockers: [BENCH-004, BENCH-010, BENCH-012, BENCH-017]
labels: [docs, operator-workflow, harnesses]
repo_areas: [README.md, docs/benchmark-methodology.md, docs/config-and-contracts.md]
docs:
  - README.md
  - docs/benchmark-methodology.md
  - docs/config-and-contracts.md
  - AGENTS.md
definition_of_ready:
  - supported harness profiles for MVP are selected
scope:
  in_scope:
    - operator quickstart
    - session start and finalize workflow docs
    - launch recipes for supported harness profiles
    - troubleshooting guidance for missing correlation and mispointed base URLs
  out_of_scope:
    - harness feature documentation beyond connection setup
deliverables:
  - updated README quickstart
  - operator workflow section
  - launch recipe examples
acceptance_criteria:
  - a new operator can run a benchmark session by following the docs only
  - launch recipes are consistent with harness profile rendering
  - troubleshooting steps cover common setup failures
test_plan:
  unit:
    - not applicable
  integration:
    - doc-driven smoke test by following the quickstart in a clean environment
  manual:
    - verify each launch recipe against the local stack
notes:
  - keep docs command-focused and reproducible
```

## BENCH-019

```yaml
id: BENCH-019
parent_issue: Security, Operations, and Delivery Quality
issue_type: sub_issue
title: Enforce redaction defaults, secret handling, and retention controls
priority: P1
estimate_points: 5
blockers: [BENCH-005, BENCH-007, BENCH-008, BENCH-011]
labels: [security, privacy, retention]
repo_areas: [src/benchmark_core/, src/collectors/, docs/security-and-operations.md]
docs:
  - AGENTS.md
  - docs/security-and-operations.md
  - docs/data-model-and-observability.md
definition_of_ready:
  - content-capture policy is approved
scope:
  in_scope:
    - default-off content capture
    - secret redaction in logs and exports
    - retention settings for raw ingest, normalized rows, and artifacts
  out_of_scope:
    - external secret manager integration
deliverables:
  - redaction layer or filters
  - retention settings and cleanup jobs
  - security-focused tests
acceptance_criteria:
  - prompts and responses are not persisted by default
  - logs and exports do not leak secrets
  - retention settings are documented and enforceable
test_plan:
  unit:
    - redaction tests with synthetic secrets
  integration:
    - retention cleanup against local DB fixtures
  manual:
    - inspect logs and exports for accidental secret leakage
notes:
  - use synthetic secrets in fixtures, never real ones
```

## BENCH-020

```yaml
id: BENCH-020
parent_issue: Security, Operations, and Delivery Quality
issue_type: sub_issue
title: Add CI checks for config validation, migrations, collectors, and dashboard assets
priority: P1
estimate_points: 3
blockers: [BENCH-002, BENCH-003, BENCH-005, BENCH-008, BENCH-017]
labels: [ci, quality, testing]
repo_areas: [.github/, Makefile, tests/]
docs:
  - AGENTS.md
  - README.md
  - docs/implementation-plan.md
definition_of_ready:
  - required CI gates are agreed
scope:
  in_scope:
    - lint, type, and test gates
    - config validation checks
    - migration smoke tests
    - collector and rollup smoke tests
    - dashboard asset validation if available
  out_of_scope:
    - hosted preview environments
deliverables:
  - CI workflow definitions
  - reusable test commands
acceptance_criteria:
  - CI blocks merges on failed quality or contract checks
  - config, migration, and collector regressions are caught automatically
  - local and CI commands are aligned
test_plan:
  unit:
    - not applicable beyond CI config validation
  integration:
    - run the full CI workflow on a test branch or local runner
  manual:
    - verify failure messages are actionable
notes:
  - keep CI output concise and diagnosable
```

## BENCH-021

```yaml
id: BENCH-021
parent_issue: Security, Operations, and Delivery Quality
issue_type: sub_issue
title: Add operator safeguards, health checks, and environment diagnostics
priority: P1
estimate_points: 3
blockers: [BENCH-002, BENCH-010, BENCH-011, BENCH-012]
labels: [operations, cli, diagnostics]
repo_areas: [src/cli/, src/benchmark_core/services/]
docs:
  - docs/security-and-operations.md
  - README.md
  - docs/architecture.md
definition_of_ready:
  - expected local failure modes are documented
scope:
  in_scope:
    - stack health command
    - environment diagnostics for session launch
    - warnings for wrong base URL, missing credential, missing model alias, or unhealthy proxy
  out_of_scope:
    - remote fleet management
deliverables:
  - health check command
  - environment diagnostics command
  - operator-facing error messages
acceptance_criteria:
  - operators can verify stack health before launching a session
  - obvious misconfigurations are surfaced before benchmark traffic starts
  - diagnostics point directly to the failing configuration or service
test_plan:
  unit:
    - diagnostic message tests
  integration:
    - run diagnostics against healthy and unhealthy local stack scenarios
  manual:
    - verify warnings for intentionally broken environment snippets
notes:
  - prefer prevention over post-hoc troubleshooting
```

## Recommended implementation sequence

1. BENCH-001 through BENCH-004
2. BENCH-005 and BENCH-006
3. BENCH-010 through BENCH-012
4. BENCH-007 through BENCH-009
5. BENCH-013 through BENCH-017
6. BENCH-018 through BENCH-021
