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

### Artifact

Represents exported bundles.

Core fields:

- `artifact_id`
- `session_id` or `experiment_id`
- `artifact_type`
- `storage_path`
- `created_at`

## Observability sources

### LiteLLM request data

Use LiteLLM request rows, structured logs, callbacks, or equivalent exported records to capture:

- request timing
- cost or usage fields when exposed
- request IDs
- model and provider routing fields
- error states

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

## Minimal schema expectations

The benchmark database should include at least:

- `providers`
- `harness_profiles`
- `variants`
- `experiments`
- `task_cards`
- `sessions`
- `requests`
- `metric_rollups`
- `artifacts`

## Join strategy

Preferred joins:

- `requests.session_id -> sessions.session_id`
- `sessions.variant_id -> variants.variant_id`
- `sessions.experiment_id -> experiments.experiment_id`
- `sessions.task_card_id -> task_cards.task_card_id`
- `variants.harness_profile_id -> harness_profiles.harness_profile_id`

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

The schema must make these queries cheap and obvious:

- compare median latency across variants in one experiment
- compare TTFT across harness profiles for one provider/model pair
- inspect all requests in one session
- find failed sessions for one harness profile
- compare cache behavior across routing settings
- export session summaries and request-level rows for external analysis
