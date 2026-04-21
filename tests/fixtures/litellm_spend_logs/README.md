# LiteLLM Spend Log Fixtures

Sanitized, representative `/spend/logs` records for unit testing and documentation.

## Files

| File | Scenario | Key Characteristics |
|:-----|:---------|:--------------------|
| `successful_request.json` | Standard success | Non-streaming, no cache, full tokens; `ttft` null |
| `failed_request.json` | Rate-limit failure | Error code 429, zero tokens/spend |
| `streaming_request.json` | Streaming success | `stream: true`, large completion, low TTFT |
| `cached_request.json` | Cache hit | `cache_hit: true`, low latency/spend; `ttft` null |
| `sparse_request.json` | Partial record | Best-effort fields omitted entirely (not just null) |
| `non_streaming_with_completion_start.json` | TTFT derivation gap-fill | Non-streaming; provides `completion_start_time` so `ttft_ms` can be derived |
| `fallback_to_call_id.json` | Fallback ID | `request_id` absent; `call_id` serves as `litellm_call_id` |

## Sanitization Rules

All fixtures use **synthetic data only**:

- **API keys**: `sk-litellm-hash-XXXXXXXX` — fake hashes, not real credentials
- **User identifiers**: `bench-user-<alpha|beta|gamma|delta>` — synthetic
- **Key aliases**: `bench-session-<alpha|beta|gamma|delta>` — synthetic
- **Session/experiment IDs**: `session-<alpha|beta|gamma|delta>-001`, `model-comparison-q2` — synthetic
- **No prompt or response text** — `metadata` only contains session correlation keys
- **Costs**: Synthetic, rounded values for illustration
- **Timestamps**: Synthetic, fixed April 2025 dates

## Data Quality Notes

- `api_key` in these fixtures is the LiteLLM **virtual key hash**, not the upstream provider key
- `api_key_alias` is the human-readable alias from the `proxy_keys` registry
- `user` / `customer_identifier` may be the alias or a separate user field depending on LiteLLM version
- `model` is the resolved upstream model; `requested_model` is the alias sent by the client
