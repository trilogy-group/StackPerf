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

- `proxy_key_id` -- surrogate primary key (UUID or auto-increment), stable across renames and reissues
- `key_alias` -- human-readable, unique, non-secret identifier (e.g., `team-alpha-gpt4o`)
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
- `proxy_key_id` -- FK -> `proxy_keys.proxy_key_id` (nullable if key not in registry); the collector resolves the LiteLLM key ID to `proxy_key_id` using an ephemeral mapping that lives outside the benchmark DB (see Collector key-matching below)
- `key_alias` -- denormalized from `proxy_keys` at ingestion time (retains alias at time of request even if alias is later renamed or revoked)
- `owner` -- denormalized from `proxy_keys` at ingestion time
- `team` -- denormalized from `proxy_keys` at ingestion time
- `customer` -- denormalized from `proxy_keys` at ingestion time
- `benchmark_session_id` -- optional FK -> `sessions.session_id` when traffic carries session metadata
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
- `cost` -- spend amount when available from LiteLLM logs; null when LiteLLM spend data is unreliable or the field is not exposed
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
- virtual key ID (resolved to `proxy_key_id` via ephemeral key-mapping, then dropped before persistence)

Collectors must resolve the LiteLLM virtual key ID to `proxy_key_id` through an ephemeral key-mapping table outside the benchmark database, then drop the raw key ID before writing `usage_requests` rows. If no registry entry exists, the collector stores `proxy_key_id = null` and logs a warning.

### Collector key-matching

The collector needs to resolve the LiteLLM virtual key ID (from logs) to a `proxy_key_id` without storing raw key secrets in the benchmark database. The mapping cannot live in the benchmark DB per the redaction rules.

**Expected approach**: maintain an ephemeral key-mapping table in the collector process or a sidecar file outside the benchmark database. When a key is created in LiteLLM, the operator (or a provisioning script) also inserts a mapping row `(litellm_virtual_key_id -> proxy_key_id, key_alias)` into this ephemeral store. The collector queries this mapping at ingestion time, writes `proxy_key_id` and denormalized `key_alias` into `usage_requests`, and never persists the raw key ID.

**Operational expectations**:
- The ephemeral mapping is the single source of truth for the collector.
- If a mapping is missing, the collector writes `proxy_key_id = null` and logs a warning (the same fallback behavior already documented for `key_alias`).
- The mapping is refreshed when keys are created, revoked, or reissued.
- Historical `usage_requests` rows remain immutable even if the mapping or the `proxy_keys` registry entry changes later.

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

- `proxy_keys` -- non-secret registry for LiteLLM virtual key metadata
- `usage_requests` -- normalized usage records with optional benchmark session linkage
- `usage_rollups` -- derived summaries by key alias, model, provider, owner, team, customer, and time bucket

## Join strategy

### Benchmark joins

- `requests.session_id -> sessions.session_id`
- `sessions.variant_id -> variants.variant_id`
- `sessions.experiment_id -> experiments.experiment_id`
- `sessions.task_card_id -> task_cards.task_card_id`
- `variants.harness_profile_id -> harness_profiles.harness_profile_id`

### Usage joins

- `usage_requests.proxy_key_id -> proxy_keys.proxy_key_id` (nullable for unattributed traffic)
- `usage_requests.key_alias -> proxy_keys.key_alias` (convenience join for queries; the alias may change over time)
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

The collector resolves the LiteLLM virtual key ID to `proxy_key_id` through an ephemeral key-mapping table outside the benchmark database (see Collector key-matching above), then drops the raw key ID before writing `usage_requests`. The stable joins are:

- `usage_requests.proxy_key_id -> proxy_keys.proxy_key_id`
- `usage_requests.key_alias -> proxy_keys.key_alias` (convenience join; alias may change over time)
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
- find unattributed traffic (proxy_key_id is null)
- export usage summaries and request-level rows for external analysis
- cross-mode query: all traffic (benchmark + usage) for a given model and time window
