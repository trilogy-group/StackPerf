# COE-316: Provision Grafana dashboards for live and historical benchmark views

## Summary

This PR implements Grafana dashboard provisioning for live LiteLLM metrics and historical benchmark summaries as specified in COE-316.

## Changes

### Dashboards Created
1. **Live Request Latency** (live-latency.json)
   - P50/P95/P99 latency distribution by model
   - Request rate tracking
   - Current latency statistics
   - Success vs failure latency breakdown

2. **Live TTFT Metrics** (live-ttft.json)
   - Time-to-first-token distribution
   - Streaming token throughput
   - TTFT percentiles (P50/P95/P99)
   - Model-specific TTFT tracking

3. **Live Error Rate** (live-error-rate.json)
   - Error rate by model
   - Request status distribution
   - Retry tracking
   - Status code analysis

4. **Experiment Summary** (experiment-summary.json)
   - Variant comparison table with latency, TTFT, error rates
   - Session history and outcomes
   - Token usage by provider
   - Historical benchmark analysis using PostgreSQL queries

### Datasources
- Added PostgreSQL datasource for historical benchmark data queries
- Prometheus datasource already configured for live metrics

### Configuration
- Updated dashboard provisioning to use 'Benchmark' folder
- All dashboards load automatically on Grafana startup

## Acceptance Criteria

- [x] Grafana loads benchmark dashboards on startup
- [x] Dashboards show live LiteLLM metrics (latency, TTFT, error-rate)
- [x] Dashboards show historical benchmark summaries
- [x] Panel labels and variable selectors match canonical benchmark dimensions

## Runtime Evidence

All services started successfully with `docker compose up -d grafana`:

```
NAME                 IMAGE                                 COMMAND                  SERVICE      STATUS
litellm              ghcr.io/berriai/litellm:main-latest   "docker/prod_entrypo…"   litellm      Up (healthy)
litellm-grafana      grafana/grafana:10.4.0                "/run.sh"                grafana      Up (healthy)
litellm-postgres     postgres:16-alpine                    "docker-entrypoint.s…"   postgres     Up (healthy)
litellm-prometheus   prom/prometheus:v2.50.0               "/bin/prometheus --c…"   prometheus   Up (healthy)
```

### Dashboards Provisioned

Grafana API confirms all 4 dashboards loaded in the "Benchmark" folder:

```json
[
    {"id": 2, "uid": "experiment-summary", "title": "Experiment Summary", "folderTitle": "Benchmark"},
    {"id": 3, "uid": "live-error-rate", "title": "Live Error Rate", "folderTitle": "Benchmark"},
    {"id": 4, "uid": "live-latency", "title": "Live Request Latency", "folderTitle": "Benchmark"},
    {"id": 5, "uid": "live-ttft", "title": "Live TTFT Metrics", "folderTitle": "Benchmark"}
]
```

### Datasources Provisioned

1. **Prometheus** (default) - URL: http://litellm-prometheus:9090
2. **PostgreSQL** - URL: postgres:5432 (requires POSTGRES_PASSWORD env var)

### API Verification Commands

```bash
# Check dashboards
curl -s -u admin:admin http://localhost:3000/api/search?type=dash-db

# Check datasources
curl -s -u admin:admin http://localhost:3000/api/datasources
```

See [EVIDENCE_COE-316.md](./EVIDENCE_COE-316.md) for full runtime verification details.

## Testing

- All 306 existing tests pass
- Dashboard JSON files validated
- Security hardened (no hardcoded credentials - requires explicit POSTGRES_PASSWORD env var)

Closes COE-316
