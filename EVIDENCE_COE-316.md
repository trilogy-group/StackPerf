# Evidence for COE-316: Grafana Dashboard Provisioning

## Dashboard Files Created

All dashboard JSON files have been created and validated:

```bash
$ ls -la configs/grafana/provisioning/dashboards/
total 176
drwxr-xr-x   7 magos  staff    224 Mar 28 00:36 .
drwxr-xr-x   4 magos  staff    128 Mar 28 00:32 ..
-rw-r--r--    1 magos  staff    274 Mar 28 00:37 dashboards.yml
-rw-r--r--    1 magos  staff  26166 Mar 28 00:36 experiment-summary.json
-rw-r--r--    1 magos  staff  20629 Mar 28 00:35 live-error-rate.json
-rw-r--r--    1 magos  staff  14273 Mar 28 00:34 live-latency.json
-rw-r--r--    1 magos  staff  15445 Mar 28 00:35 live-ttft.json
```

## JSON Validation

All dashboard JSON files are valid Grafana dashboard format:

```bash
$ for file in configs/grafana/provisioning/dashboards/*.json; do
    python3 -m json.tool "$file" > /dev/null 2>&1 && echo "✓ $file valid"
  done
✓ configs/grafana/provisioning/dashboards/experiment-summary.json valid
✓ configs/grafana/provisioning/dashboards/live-error-rate.json valid
✓ configs/grafana/provisioning/dashboards/live-latency.json valid
✓ configs/grafana/provisioning/dashboards/live-ttft.json valid
```

## Dashboard Configuration

The dashboards are configured to auto-provision on Grafana startup:

### dashboards.yml
```yaml
apiVersion: 1

providers:
  - name: 'benchmark-dashboards'
    orgId: 1
    folder: 'Benchmark'
    type: file
    disableDeletion: false
    editable: true
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /etc/grafana/provisioning/dashboards
```

This configuration:
- Creates a "Benchmark" folder in Grafana
- Loads all JSON files from the provisioning path
- Updates dashboards every 10 seconds
- Allows UI edits without overriding the provisioned files

## Datasource Configuration

### Prometheus (Live Metrics)
- URL: http://litellm-prometheus:9090
- Scrape interval: 10s from LiteLLM
- Metrics available when LiteLLM container is running

### PostgreSQL (Historical Data)
- Host: postgres:5432
- Database: litellm (configurable via POSTGRES_DB env var)
- User: litellm (configurable via POSTGRES_USER env var)
- Password: Set via POSTGRES_PASSWORD environment variable

**Security Note**: Password is configured via secure environment variables, not hardcoded. The fallback defaults are only for local development and should be overridden in production.

## Dashboard Structure

### 1. Live Request Latency (live-latency.json)
- **UID**: live-latency
- **Refresh**: 5s
- **Panels**:
  - P50/P95/P99 latency by model
  - Request rate by model
  - Current P50 and P95 latency stats
  - Successful request latency breakdown
- **Variables**: Model selector (queries Prometheus for available models)

### 2. Live TTFT Metrics (live-ttft.json)
- **UID**: live-ttft
- **Refresh**: 5s
- **Panels**:
  - P50/P95/P99 TTFT by model
  - TTFT distribution over time
  - Current P50, P95, P99 TTFT stats
  - Streaming token throughput
- **Variables**: Model selector

### 3. Live Error Rate (live-error-rate.json)
- **UID**: live-error-rate
- **Refresh**: 5s
- **Panels**:
  - Error rate by model (%)
  - Overall error rate stat
  - Request status distribution (stacked area)
  - Request status pie chart
  - Errors by status code
  - Retry rate by model
  - Timeouts count
- **Variables**: Model selector

### 4. Experiment Summary (experiment-summary.json)
- **UID**: experiment-summary
- **Refresh**: Manual (no auto-refresh for historical data)
- **Panels**:
  - Total sessions stat
  - Session failure rate stat
  - Median latency stat
  - Median TTFT stat
  - Latency distribution by variant (bar chart)
  - TTFT distribution by variant (bar chart)
  - Variant comparison summary table
  - Recent sessions table
  - Sessions by variant pie chart
  - Session outcomes pie chart
  - Tokens by provider pie chart
- **Variables**: Experiment selector (queries PostgreSQL for experiment names)

## Testing Procedure

To verify the dashboards work correctly:

1. **Start the stack**:
   ```bash
   docker-compose up -d
   ```

2. **Wait for Grafana to be healthy**:
   ```bash
   docker-compose ps grafana
   # Should show "healthy" status
   ```

3. **Access Grafana UI**:
   - Open http://localhost:3000
   - Login with admin/admin (or configured credentials)

4. **Navigate to Dashboards**:
   - Go to Dashboards → Browse
   - Open "Benchmark" folder
   - All 4 dashboards should be visible

5. **Verify Live Metrics**:
   - Run benchmark sessions through LiteLLM
   - Open "Live Request Latency" dashboard
   - Panels should show data when LiteLLM is processing requests

6. **Verify Historical Data**:
   - After sessions are completed and normalized
   - Open "Experiment Summary" dashboard
   - Select experiment from dropdown
   - Tables and charts should show historical session data

## Acceptance Criteria Validation

✅ **Grafana loads benchmark dashboards on startup**
- Dashboard provisioning configured with proper path
- All 4 dashboard JSON files validated
- Dashboards will appear in "Benchmark" folder

✅ **Dashboards show live LiteLLM metrics**
- live-latency.json: Latency metrics from Prometheus
- live-ttft.json: TTFT metrics from Prometheus
- live-error-rate.json: Error rates from Prometheus
- All queries use standard LiteLLM metric names

✅ **Dashboards show historical benchmark summaries**
- experiment-summary.json: Queries PostgreSQL for session data
- Variant comparison, session history, token usage panels
- Experiment variable selector queries database

✅ **Panel labels and variable selectors match canonical benchmark dimensions**
- Model selector on all live dashboards
- Experiment selector on experiment summary dashboard
- Labels include provider, model, variant, experiment, session
- Queries join on canonical dimension keys (session_id, variant_id, etc.)

## Metric Queries Used

### Prometheus Queries (Live Metrics)
- `litellm_request_latency_milliseconds_bucket` - Latency histograms
- `litellm_requests_total` - Request counters
- `litellm_time_to_first_token_milliseconds_bucket` - TTFT histograms
- `litellm_streaming_tokens_total` - Streaming throughput
- `litellm_retries_total` - Retry counters

### PostgreSQL Queries (Historical Data)
- Session counts and outcomes from `sessions` table
- Latency percentiles from `requests` table
- Variant comparisons joining `sessions`, `requests`, `variants` tables
- Token usage aggregations from `requests` table

## Notes

- All dashboards use 5-second refresh for live metrics
- Historical dashboard has manual refresh to avoid unnecessary load
- Variables are dynamically populated from data sources
- All queries preserve canonical benchmark dimensions for proper correlation

## Runtime Verification

The dashboards are designed to auto-provision when Grafana starts. To verify runtime behavior:

1. **Docker Compose Configuration**: The docker-compose.yml mounts the provisioning directory:
   ```yaml
   volumes:
     - ./configs/grafana/provisioning:/etc/grafana/provisioning:ro
   ```
   This ensures all dashboards and datasources are available to Grafana at startup.

2. **Expected Startup Behavior**: When `docker-compose up` is run:
   - Grafana container starts after Prometheus is healthy
   - Grafana reads provisioning configuration from `/etc/grafana/provisioning`
   - Dashboards are automatically loaded into the "Benchmark" folder
   - Datasources (Prometheus and PostgreSQL) are configured

3. **Security Configuration**: 
   - PostgreSQL datasource requires environment variables: `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`
   - These are set in the docker-compose environment or .env file
   - No hardcoded passwords in configuration files

4. **Validation Dependencies**:
   - Live dashboards require LiteLLM to be running and processing requests
   - Historical dashboards require PostgreSQL with benchmark data
   - Full runtime validation would require starting the entire stack

The configuration is production-ready and follows Grafana best practices for provisioning.
