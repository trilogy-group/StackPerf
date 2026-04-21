# Data Model and Observability

## Canonical entities

### Provider

Represents an upstream inference provider and route metadata.

Core fields:

- `provider_id`
- `name`
- `route_name`
- `protocol_surface`
- `upstream_base_url`
- `created_at`

### Harness profile

Represents a harness connection profile.

Core fields:

- `harness_profile_id`
- `name`
- `protocol_surface`
- `base_url_env`
- `api_key_env`
- `model_env`
- `created_at`

### Variant

Represents one benchmarkable configuration.

Core fields:

- `variant_id`
- `name`
- `provider_id`
- `model_alias`
- `harness_profile_id`
- `config_fingerprint`
- `created_at`

### Experiment

Represents a named comparison set.

Core fields:

- `experiment_id`
- `name`
- `description`
- `created_at`

### Task card

Represents benchmark work definition.

Core fields:

- `task_card_id`
- `name`
- `repo_path`
- `goal`
- `stop_condition`
- `session_timebox_minutes`

### Session

Represents one interactive benchmark execution.

Core fields:

- `session_id`
- `experiment_id`
- `variant_id`
- `task_card_id`
- `harness_profile_id`
- `status`
- `started_at`
- `ended_at`
- `operator_label`
- `repo_root`
- `git_branch`
- `git_commit_sha`
- `git_dirty`
- `proxy_key_alias`
- `proxy_virtual_key_id` when available

### Request

Represents one normalized LLM call.

Core fields:

- `request_id`
- `session_id`
- `experiment_id`
- `variant_id`
- `provider_id`
- `provider_route`
- `model`
- `harness_profile_id`
- `litellm_call_id`
- `provider_request_id`
- `started_at`
- `finished_at`
- `latency_ms`
- `ttft_ms`
- `proxy_overhead_ms`
- `provider_latency_ms`
- `input_tokens`
- `output_tokens`
- `cached_input_tokens`
- `cache_write_tokens`
- `status`
- `error_code`

### Metric rollup

Represents derived summaries.

Core fields:

- `rollup_id`
- `scope_type` with values `request`, `session`, `variant`, `experiment`
- `scope_id`
- `metric_name`
- `metric_value`
- `computed_at`
- `window_start`
- `window_end`

### Proxy key

Represents a non-secret registry entry for a LiteLLM virtual key.

Core fields:

- `key_alias` — primary key, human-readable, unique, non-secret
- `owner`
- `team`
- `customer`
- `description`
- `budget_duration`
- `budget_amount`
- `created_at`
- `revoked_at`
- `expires_at`
- `metadata`

### Usage request

Represents one normalized LLM call in usage mode, stored in `usage_requests`.

Core fields:

- `usage_request_id`
- `key_alias` — FK → `proxy_keys.key_alias` (nullable if key not in registry)
- `owner` — denormalized from `proxy_keys` at ingestion time
- `team` — denormalized from `proxy_keys` at ingestion time
- `customer` — denormalized from `proxy_keys` at ingestion time
- `benchmark_session_id` — optional FK → `sessions.session_id` when traffic carries session metadata
- `provider_id`
- `provider_route`
- `model`
- `litellm_call_id`
- `provider_request_id`
- `started_at`
- `finished_at`
- `latency_ms`
- `ttft_ms`
- `proxy_overhead_ms`
- `provider_latency_ms`
- `input_tokens`
- `output_tokens`
- `cached_input_tokens`
- `cache_write_tokens`
- `status`
- `error_code`

### Usage rollup

Represents derived summaries for usage mode.

Core fields:

- `usage_rollup_id`
- `scope_type` with values `key_alias`, `owner`, `team`, `customer`, `model`, `provider`, `day`, `hour`
- `scope_id`
- `metric_name`
- `metric_value`
- `computed_at`
- `window_start`
- `window_end`

### Artifact

Represents exported bundles.

Core fields:

- `artifact_id`
- `session_id` or `experiment_id`
- `artifact_type`
- `storage_path`
- `created_at`

## Observability sources

### LiteLLM request data (benchmark mode)

Use LiteLLM request rows, structured logs, callbacks, or equivalent exported records to capture:

- request timing
- cost or usage fields when exposed
- request IDs
- model and provider routing fields
- error states
- benchmark session metadata from virtual key tags

### LiteLLM request data (usage mode)

Use LiteLLM spend logs or structured logs to capture:

- request timing
- cost or usage fields when exposed
- request IDs
- model and provider routing fields
- error states
- virtual key ID (replaced with `key_alias` from `proxy_keys` registry before persistence)

Collectors must match the LiteLLM virtual key ID to the `proxy_keys` registry by alias, then drop the raw key ID before writing `usage_requests` rows. If no registry entry exists, the collector stores `key_alias = null` and logs a warning.

### Prometheus

Use Prometheus for:

- live operational metrics
- scrape-based time-series
- cross-checking request counts and latency distributions
- dashboard panels and trend lines

### Benchmark session registry

Use the session registry for:

- session metadata
- repo context
- harness profile selection
- operator-supplied notes
- status transitions

## Derived metrics

### Request level

- latency milliseconds
- TTFT milliseconds
- proxy overhead milliseconds
- provider latency milliseconds
- output tokens per second
- cache hit indicators

### Session level

- request count
- success count
- error count
- median latency
- p95 latency
- median TTFT
- total input tokens
- total output tokens
- median output tokens per second
- cache hit ratio by request count

### Variant level

- session count
- session success rate
- median session duration
- median request latency across sessions
- p95 request latency across sessions
- median session TTFT
- variance statistics across repeated sessions

### Usage level

- request count by key alias, owner, team, customer, model, provider, and time bucket
- success count and error count by the same dimensions
- median latency by key alias and model
- p95 latency by key alias and model
- median TTFT by key alias and model
- total input tokens by key alias and model
- total output tokens by key alias and model
- total cost/spend when available from LiteLLM logs
- cache hit ratio by request count
- error rate by key alias and model

## Minimal schema expectations

The benchmark database should include at least:

### Benchmark tables

- `providers`
- `harness_profiles`
- `variants`
- `experiments`
- `task_cards`
- `sessions`
- `requests`
- `metric_rollups`
- `artifacts`

### Usage-mode tables

- `proxy_keys` — non-secret registry for LiteLLM virtual key metadata
- `usage_requests` — normalized usage records with optional benchmark session linkage
- `usage_rollups` — derived summaries by key alias, model, provider, owner, team, customer, and time bucket

## Join strategy

### Benchmark joins

- `requests.session_id -> sessions.session_id`
- `sessions.variant_id -> variants.variant_id`
- `sessions.experiment_id -> experiments.experiment_id`
- `sessions.task_card_id -> task_cards.task_card_id`
- `variants.harness_profile_id -> harness_profiles.harness_profile_id`

### Usage joins

- `usage_requests.key_alias -> proxy_keys.key_alias`
- `usage_requests.benchmark_session_id -> sessions.session_id` (optional, nullable)
- `usage_requests.litellm_call_id -> LiteLLM spend_log.call_id` (source audit)
- `usage_requests.provider_id -> providers.provider_id`

### Cross-mode joins

When a usage request carries benchmark session metadata:

- `usage_requests.benchmark_session_id -> sessions.session_id`
- `sessions.experiment_id -> experiments.experiment_id`
- `sessions.variant_id -> variants.variant_id`

This lets operators query usage traffic that was generated during a benchmark session, or query all usage traffic (including sessionless traffic) through `usage_requests` alone.

### LiteLLM log joins

The collector joins LiteLLM spend logs to `proxy_keys` by matching the LiteLLM virtual key ID to the `key_alias` in the registry. After ingestion, the raw key ID is dropped. The stable joins are:

- `usage_requests.key_alias -> proxy_keys.key_alias`
- `usage_requests.litellm_call_id -> LiteLLM log.call_id` (for audit and debugging)

Preserve raw source keys alongside benchmark keys so raw ingestion can be audited.

## Redaction boundary

Store prompt and response text only when an explicit content-capture flag is enabled.

Default ingestion stores:

- IDs
- timing
- status
- token counts
- routing fields
- cache counters
- summarized error metadata

## Query patterns to support

### Benchmark queries

The schema must make these queries cheap and obvious:

- compare median latency across variants in one experiment
- compare TTFT across harness profiles for one provider/model pair
- inspect all requests in one session
- find failed sessions for one harness profile
- compare cache behavior across routing settings
- export session summaries and request-level rows for external analysis

### Usage queries

The schema must make these queries cheap and obvious:

- total requests, tokens, and cost by key alias for a time window
- error rate by key alias and model for a time window
- median latency and p95 latency by key alias and model for a time window
- total usage by team or customer for a time window
- compare usage across models for one key alias
- find unattributed traffic (key_alias is null)
- export usage summaries and request-level rows for external analysis
- cross-mode query: all traffic (benchmark + usage) for a given model and a time window

## LiteLLM spend-log field inventory

The following table maps LiteLLM `/spend/logs` fields to the canonical `usage_request` schema. Fields are classified as **stable** (present on every successful/failed record) or **best-effort** (availability depends on LiteLLM version, provider, or request type).

### Field mapping table

| LiteLLM field | Canonical target | Presence | Notes |
|:--------------|:-----------------|:---------|:------|
| `request_id` | `litellm_call_id` | **Stable** | Primary source; ingest `request_id`. If absent, fall back to `call_id` |
| `call_id` | `litellm_call_id` | **Stable** | Commonly distinct from `request_id` in callback payloads (see fixtures); ignored at ingest when `request_id` is present |
| `api_key` | — (dropped at ingest) | **Stable** | Hashed LiteLLM virtual key. Replaced by `key_alias` from `proxy_keys` registry |
| `api_key_alias` | `key_alias` | **Best-effort** | Human-readable alias. May be missing on older LiteLLM versions or when key is not in registry |
| `user` | `owner` (denormalized) | **Best-effort** | Often the same as `api_key_alias`, but not guaranteed |
| `customer_identifier` | `customer` (denormalized) | **Best-effort** | May mirror `user`; not always present |
| `startTime` | `started_at` | **Stable** | ISO 8601 string; fallback from `timestamp` or `created_at` |
| `endTime` | `finished_at` | **Best-effort** | Null on streaming requests that time out or on some error paths |
| `model` | `model` | **Stable** | Resolved upstream model name (e.g. `gpt-4o`) |
| `model_id` | `model` | **Stable** | Alias for `model` on most records |
| `requested_model` | — (metadata) | **Stable** | Model alias sent by the client; useful for audit |
| `provider` | `provider_id` | **Stable** | Short provider slug (e.g. `openai`, `fireworks`) |
| `custom_llm_provider` | `provider_route` | **Best-effort** | Full provider string; may differ from `provider` |
| `spend` | `cost_usd` (planned) | **Best-effort** | Cost in USD. May be `0.0` for failed requests or when provider pricing is not configured |
| `total_tokens` | `input_tokens + output_tokens` | **Stable** | Sum of prompt + completion tokens |
| `prompt_tokens` | `input_tokens` | **Stable** | Input side token count |
| `completion_tokens` | `output_tokens` | **Stable** | Output side token count |
| `cache_hit` | `cached_input_tokens` indicator | **Best-effort** | Boolean flag; may be absent on providers that do not support caching |
| `cached_input_tokens` | `cached_input_tokens` | **Best-effort** | Actual cached token count when cache is enabled and hit |
| `cache_write_tokens` | `cache_write_tokens` | **Best-effort** | Tokens written to cache; rarely exposed by providers |
| `stream` | — (metadata) | **Stable** | Boolean; `true` for streaming requests |
| `completion_start_time` | `—` (source for `ttft_ms`) | **Best-effort** | ISO timestamp of first token arrival; derive `ttft_ms = round((completion_start_time − startTime) × 1000)` when `ttft` is absent |
| `latency` | `latency_ms` | **Stable** | Total request latency in seconds; multiplied by 1000 on ingest |
| `ttft` | `ttft_ms` | **Best-effort** | Time-to-first-token in seconds; typically null or absent on non-streaming requests and errors |
| `total_latency` | `latency_ms` | **Stable** | Alias for `latency`; same value |
| `time_to_first_token` | `ttft_ms` | **Best-effort** | Alias for `ttft` |
| `status` | `status` | **Stable** | String: `"success"`, `"failure"`, or `"pending"` |
| `error` | `error_message` | **Best-effort** | Error message string on failures; stored as `error_message` when ingest schema supports it; null on successes |
| `error_code` | `error_code` | **Best-effort** | Numeric HTTP-style code (e.g. `429`); may be absent when LiteLLM cannot map the error |
| `metadata` | Various (denormalized) | **Best-effort** | JSON blob with session correlation keys. Field names vary by LiteLLM version and callback config |

### Redaction and sensitivity

The following fields are **never** stored in committed fixtures or ingested rows by default:

- Prompt and response text (redacted by `redact_messages_in_logs: true`)
- Raw upstream API keys (only LiteLLM virtual key hashes transit, and are dropped at ingest)
- Request/response bodies beyond routing and timing metadata

### Gap list — fields LiteLLM does not expose reliably

| Desired field | Why it matters | Current LiteLLM limitation | Workaround |
|:--------------|:---------------|:---------------------------|:-----------|
| **Per-request cost accuracy** | Budget enforcement, chargeback | `spend` is best-effort; provider pricing tables may lag | Use provider invoices for billing of record; use `spend` for trending only |
| **Cache write tokens** | Cache cost attribution | Not exposed by most providers via LiteLLM | Aggregate `cache_hit` ratio as proxy |
| **TTFT on non-streaming requests** | Latency breakdown | `ttft` is typically null or absent when `stream: false` | Derive `ttft_ms = (completion_start_time − startTime) × 1000` when both fields present |
| **Provider request ID** | Cross-referencing provider logs | Not in `/spend/logs`; only in callbacks | Use `call_id` as primary audit key |
| **Key alias on every record** | Human-readable attribution | `api_key_alias` missing when key not in `proxy_keys` registry | Store `key_alias = null` and warn; match retroactively |
| **Prompt token breakdown (system vs user)** | Usage optimization | Not exposed in spend logs | Not available without custom callbacks |
| **Finish reason** | Detect truncation / stop conditions | Not in spend logs; only in response body | Not available without content logging |

## Prometheus label inventory

LiteLLM exposes Prometheus metrics at `/metrics`. The following labels are present on the counters and histograms relevant to usage attribution.

### Labels available on `litellm_proxy_total_requests_metric_total`

| Label | Example values | Cardinality | API-key attribution? |
|:------|:---------------|:------------|:---------------------|
| `requested_model` | `gpt-4o`, `kimi-k2-5` | Low (model aliases) | Yes — by model |
| `model` | `gpt-4o`, `accounts/fireworks/models/kimi-k2p5` | Medium (resolved names) | Yes — by model |
| `user` | hashed virtual key or alias | Medium–High (one per key) | **Partial** — hashed key, not human-readable alias |
| `api_key` | `hashed_api_key=sk...abc` | High (one per virtual key) | **Partial** — hashed, requires reverse lookup |
| `status_code` | `200`, `429`, `500` | Low | Yes — by status |
| `end_user` | `bench-user-alpha` | Medium | Yes — by end-user tag |
| `key_alias` | — | — | **Not exposed** |

### Labels available on `litellm_request_total_latency_metric_bucket`

| Label | Example values | Cardinality | API-key attribution? |
|:------|:---------------|:------------|:---------------------|
| `requested_model` | `gpt-4o`, `kimi-k2-5` | Low | Yes — by model |
| `model` | resolved model string | Medium | Yes — by model |
| `user` | hashed key or alias | Medium–High | Partial |
| `api_key` | hashed key | High | Partial |
| `status_code` | `200`, `429` | Low | Yes — by status |

### Labels **not** available on Prometheus metrics

| Desired label | Why it's missing | Impact |
|:--------------|:-----------------|:-------|
| `key_alias` | LiteLLM Prometheus exporter does not emit human-readable aliases | Cannot build live dashboards filtered by key alias |
| `session_id` | Not in Prometheus labels; only in `metadata` callback | Cannot correlate live metrics with benchmark sessions via Prometheus alone |
| `experiment` | Only in callback `metadata` | Cannot break down live metrics by experiment |
| `variant` | Only in callback `metadata` | Cannot break down live metrics by variant |
| `provider` (slug) | `custom_llm_provider` may differ | Minor — `model` usually encodes provider |

### Prometheus cardinality warning

Filtering Prometheus metrics by `api_key` or `user` label at high cardinality (hundreds or thousands of virtual keys) can cause:

- **Memory pressure** in Prometheus for series storage
- **Slow query evaluation** for high-cardinality aggregations
- **Label explosion** if keys are short-lived (e.g. per-session keys)

### Recommendation: API-key-level live dashboards

**Can we build live Prometheus dashboards broken down by API key alias?**

**No — not directly from Prometheus labels.**

| Dashboard type | Data source | Feasibility |
|:---------------|:------------|:------------|
| Model-level latency / error rate / throughput | Prometheus (live) | **Fully possible** — `requested_model` and `status_code` labels are stable and low-cardinality |
| Status-level breakdown | Prometheus (live) | **Fully possible** — `status_code` label is reliable |
| End-user-level breakdown | Prometheus (live) | **Possible with caveats** — `end_user` label exists but cardinality depends on tagging discipline |
| **API-key-alias-level breakdown** | Prometheus (live) | **Not possible** — `key_alias` is not a Prometheus label |
| API-key-alias-level breakdown | Postgres (`/spend/logs`) | **Fully possible** — `api_key_alias` is in spend log rows; requires periodic ETL or direct query |
| Session-level correlation | Postgres + registry join | **Fully possible** — join `usage_requests` to `proxy_keys` by `key_alias` |

**Operational implication:**

- Use **Prometheus** for live operational dashboards (model-level, status-level, aggregate latency)
- Use **Postgres spend logs** (or the benchmark `usage_requests` table) for API-key-alias-level reporting, cost attribution, and session correlation
- If live key-alias dashboards are required, consider a **hybrid approach**: Prometheus for real-time aggregates, with a lightweight Postgres query or materialized view for key-level drill-down

## Sanitized fixtures

Representative `/spend/logs` records are committed under `tests/fixtures/litellm_spend_logs/`:

- `successful_request.json` — non-streaming, cache miss, full metadata
- `failed_request.json` — rate-limit error, zero tokens/spend, null TTFT
- `streaming_request.json` — streaming flag, large completion, low TTFT
- `cached_request.json` — cache hit, low latency/spend, cached token count
- `sparse_request.json` — best-effort fields (e.g., `ttft`, `cache_write_tokens`, `endTime`) omitted entirely, demonstrating the common real-world partial record
- `non_streaming_with_completion_start.json` — non-streaming request where `ttft` is null but `completion_start_time` is present; demonstrates the gap-list derivation path `ttft_ms = round((completion_start_time − startTime) × 1000)`
- `fallback_to_call_id.json` — request where `request_id` is absent and only `call_id` is present; demonstrates the fallback path for `litellm_call_id`

These fixtures are synthetic and contain no real API keys or prompt/response content.
