# Security and Operations

## Local-first operating posture

The system is designed for local use on a developer workstation or controlled internal environment.

Default posture:

- services bind to local interfaces unless explicitly configured otherwise
- dashboards are local-only by default
- benchmark content capture is off by default
- secrets are injected through environment variables or uncommitted env files

## Secrets

Secrets include:

- upstream provider API keys
- LiteLLM master key
- session-scoped proxy credentials
- Grafana admin credentials
- database connection strings

Rules:

- never commit secrets
- never place secrets in sample config values unless clearly fake
- never log session credentials in plaintext after creation output
- use short TTLs for session-scoped proxy credentials

## Redaction

Default benchmark storage should capture metadata and metrics, not content.

Allowed by default:

- request IDs
- timing metrics
- token counts
- cache counters
- routing metadata
- status and error class

Disabled by default:

- prompt text
- response text
- tool payload bodies

## Retention

Retention policy should apply to:

- raw LiteLLM ingestion records
- normalized request rows
- exported artifacts
- session credentials

Recommended defaults:

- session credentials expire quickly
- raw ingestion rows have a shorter retention window than normalized summaries
- exported artifacts include creation timestamps and explicit ownership metadata

## Operator safeguards

The CLI should provide:

- explicit confirmation when deleting benchmark data
- clear status output when a session has not been finalized
- validation before creating a session that would overwrite local artifacts
- visibility into the exact base URL, model alias, and harness profile selected

## Upgrade and pinning policy

Pin versions for:

- LiteLLM
- benchmark application dependencies
- Prometheus
- Grafana

Each benchmark result should record the versions in use so regressions can be linked to stack changes.

## Service health

Operators need quick checks for:

- LiteLLM health endpoint
- Postgres availability
- Prometheus scrape success
- Grafana datasource health
- benchmark database migration state

## Failure handling

The system must fail clearly when:

- the proxy is unreachable
- the benchmark database is unavailable
- the chosen provider route is not configured
- the requested harness profile is invalid
- the session credential cannot be created

Silent fallback to a different provider, model, or endpoint is not acceptable.

## Local filesystem hygiene

The benchmark application may inspect the local repository and write exports.

Rules:

- store generated env snippets and exports in ignored paths
- do not write secrets into tracked files
- include a clear cleanup command for generated session artifacts

## Auditability

A benchmark result must be auditable after the session ends.

Store enough metadata to answer:

- which config files defined the session
- which repository commit was used
- which provider route and model were selected
- which harness profile was rendered
- when the session ran
- which requests were observed
