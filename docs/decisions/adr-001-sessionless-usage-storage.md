# ADR-001: Sessionless Usage Storage Strategy

## Status

Accepted

## Context

StackPerf supports two complementary operating modes:

- **Benchmark mode**: session-first comparisons across experiments, variants, harnesses, providers, and task cards. Every normalized request row must belong to a benchmark `session`.
- **Usage mode**: long-running API-key and model accounting for request volume, token usage, spend, latency, TTFT, errors, and cache behavior—without requiring an experiment, variant, task card, or session.

The benchmark database already has a `requests` table where `session_id` is a required foreign key. Traffic that does not go through a benchmark session has no `session_id`, and therefore cannot be stored in `requests` without a schema change.

We needed to decide how to store sessionless usage records.

## Options Considered

### Option A: Make `requests.session_id` nullable

Allow `requests` rows to exist without a `session_id`, and distinguish benchmark requests from usage requests by the presence or absence of that key.

Pros:
- One table for all traffic simplifies queries that span both modes.
- Fewer migrations and fewer normalization code paths.

Cons:
- Every existing benchmark query, rollup, and report assumes `session_id` is non-null. Making it nullable weakens a core invariant without proving the new shape first.
- Nullable `session_id` complicates join logic for benchmark comparisons because `variant_id`, `experiment_id`, and `task_card_id` are also session-derived and would need similar nullability changes.
- Sessionless traffic does not carry experiment, variant, or task-card context, so most benchmark comparison dimensions would be `NULL` for usage rows, polluting comparison queries.
- A single table makes it harder to evolve usage-specific fields (e.g., `owner`, `team`, `customer`, `key_alias`) without affecting benchmark schema stability.

### Option B: Add a separate `usage_requests` table

Keep `requests` as the benchmark-session request table. Add a new `usage_requests` table for all LiteLLM traffic that does not belong to a benchmark session. Optionally link usage rows back to benchmark sessions when session metadata is present in LiteLLM tags.

Pros:
- Preserves the benchmark-session invariant (`requests.session_id` remains required).
- Allows usage-specific fields to evolve independently.
- Keeps benchmark comparison queries fast and simple because they never scan usage rows.
- Makes it easy to add usage-only rollups and dashboards without affecting benchmark reports.
- Provides a clean migration path: once both shapes are proven, a future iteration can consolidate if desired.

Cons:
- Two tables require two ingestion code paths. The real risk is not the extra path -- it is ensuring both paths stay semantically aligned over time. Shared normalization helpers must be the single source of field extraction logic, with only the destination table varying, so semantic drift is structurally prevented.
- Queries that need both benchmark and usage traffic must union or join across tables.

## Decision

Adopt **Option B**: add a separate `usage_requests` table beside the existing `requests` table.

## Consequences

- `requests` remains the benchmark-session request table. `session_id` stays required.
- `usage_requests` stores all LiteLLM traffic, including traffic that carries optional benchmark session metadata.
- Shared normalization helpers extract the same fields from LiteLLM source records for both tables, so ingestion logic does not diverge in meaning.
- If LiteLLM tags contain a benchmark `session_id`, `usage_requests` can store it as an optional `benchmark_session_id` for cross-table joins.
- Future work can consider unifying the tables once the usage shape is stable.

## Related

- `docs/architecture.md` — operating modes
- `docs/data-model-and-observability.md` — `usage_requests` schema fields
- `docs/config-and-contracts.md` — canonical terms
