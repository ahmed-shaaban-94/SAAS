# Debugging Runbook

Structured troubleshooting guide for common issues across all DataPulse services.

## Service Health Overview

```bash
# Check all containers are running
docker compose ps

# Check container logs (last 50 lines)
docker compose logs --tail=50 api
docker compose logs --tail=50 frontend
docker compose logs --tail=50 postgres
docker compose logs --tail=50 keycloak
docker compose logs --tail=50 n8n

# Check API health endpoint
curl http://localhost:8000/health

# Check frontend
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000

# Check Keycloak
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/realms/datapulse
```

## Docker Troubleshooting

### Container Won't Start

```bash
# Check exit code and logs
docker compose ps -a
docker compose logs <service-name>

# Common causes:
# - Port conflict: another process on 5432, 8000, 3000, etc.
lsof -i :5432
lsof -i :8000
lsof -i :3000

# - Volume permission issues
docker compose down -v  # WARNING: destroys data volumes
docker compose up -d --build

# - Image build failure
docker compose build --no-cache <service-name>
```

### Container Restarts in Loop

```bash
# Check restart count
docker inspect --format='{{.RestartCount}}' datapulse-api

# Check OOM kill
docker inspect --format='{{.State.OOMKilled}}' datapulse-api

# View real-time logs
docker compose logs -f <service-name>
```

### Network Issues Between Containers

```bash
# Verify containers are on the same network
docker network inspect datapulse_default

# Test connectivity from one container to another
docker exec datapulse-api ping postgres
docker exec datapulse-api curl -s http://keycloak:8080/realms/datapulse

# DNS resolution
docker exec datapulse-api nslookup postgres
```

## Database Debugging

### Connection Issues

```bash
# Test connection from host
psql -h localhost -p 5432 -U datapulse -d datapulse

# Test connection from API container
docker exec datapulse-api python -c "
from datapulse.config import get_settings
from sqlalchemy import create_engine, text
engine = create_engine(get_settings().database_url)
with engine.connect() as conn:
    print(conn.execute(text('SELECT 1')).scalar())
"

# Check PostgreSQL logs
docker compose logs postgres | tail -20

# Check active connections
docker exec datapulse-db psql -U datapulse -c "SELECT count(*) FROM pg_stat_activity;"
```

### Query Performance

```sql
-- Slow query log (enable if not already)
ALTER SYSTEM SET log_min_duration_statement = 1000;  -- log queries > 1s
SELECT pg_reload_conf();

-- Active queries
SELECT pid, now() - pg_stat_activity.query_start AS duration, query
FROM pg_stat_activity
WHERE state = 'active'
ORDER BY duration DESC;

-- Table sizes
SELECT schemaname, tablename,
       pg_size_pretty(pg_total_relation_size(schemaname || '.' || tablename)) AS total_size
FROM pg_tables
WHERE schemaname IN ('bronze', 'public_staging', 'public_marts')
ORDER BY pg_total_relation_size(schemaname || '.' || tablename) DESC;

-- Index usage
SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;

-- Missing indexes (sequential scans on large tables)
SELECT schemaname, relname, seq_scan, seq_tup_read, idx_scan
FROM pg_stat_user_tables
WHERE seq_scan > 100
ORDER BY seq_tup_read DESC;
```

### RLS Debugging

```sql
-- Check if RLS is active
SELECT tablename, rowsecurity FROM pg_tables
WHERE schemaname = 'bronze';

-- Check current tenant setting
SHOW app.tenant_id;

-- Test: query as superuser (bypasses RLS unless FORCE is set)
-- vs. query as app user
SET ROLE datapulse_readonly;
SET LOCAL app.tenant_id = 'your-tenant-uuid';
SELECT COUNT(*) FROM bronze.sales;

-- Debug: empty results might mean tenant_id is not set
-- Check the API's session setup in deps.py
```

### Data Issues

```sql
-- Row counts across layers
SELECT 'bronze.sales' AS table_name, COUNT(*) FROM bronze.sales
UNION ALL
SELECT 'stg_sales', COUNT(*) FROM public_staging.stg_sales
UNION ALL
SELECT 'fct_sales', COUNT(*) FROM public_marts.fct_sales;

-- Orphaned foreign keys
SELECT COUNT(*) FROM public_marts.fct_sales f
LEFT JOIN public_marts.dim_customer c ON f.customer_key = c.customer_key
WHERE c.customer_key IS NULL;

-- Null rate check
SELECT
    column_name,
    COUNT(*) - COUNT(column_name) AS null_count,
    ROUND(100.0 * (COUNT(*) - COUNT(column_name)) / COUNT(*), 2) AS null_pct
FROM public_marts.fct_sales
CROSS JOIN LATERAL (VALUES
    ('customer_key', customer_key::text),
    ('product_key', product_key::text)
) AS cols(column_name, val)
GROUP BY column_name;
```

## API Debugging

### Request/Response Issues

```bash
# Test endpoint with verbose output
curl -v http://localhost:8000/api/v1/analytics/summary \
  -H "Authorization: Bearer $TOKEN"

# Check response time
curl -s -o /dev/null -w "Time: %{time_total}s\nHTTP: %{http_code}\n" \
  http://localhost:8000/api/v1/analytics/summary

# Test with specific query params
curl "http://localhost:8000/api/v1/analytics/trends/daily?start_date=2024-01-01&end_date=2024-12-31" \
  -H "Authorization: Bearer $TOKEN"
```

### Common API Errors

| Status | Cause | Debug Steps |
|--------|-------|-------------|
| 401 | Missing/invalid JWT | Check token, check Keycloak is running |
| 403 | Insufficient role | Check user's realm roles in Keycloak |
| 404 | Wrong URL path | Check `/api/v1/` prefix, check route registration |
| 422 | Validation error | Check request body/params match Pydantic model |
| 429 | Rate limited | Wait 60 seconds, or check rate limit config |
| 500 | Unhandled exception | Check API container logs |
| 503 | DB unreachable | Check postgres container, check DATABASE_URL |

### structlog Log Analysis

```bash
# API logs are JSON-formatted via structlog
docker compose logs api | tail -20

# Parse with jq
docker compose logs api 2>&1 | grep "^{" | jq '.'

# Filter by log level
docker compose logs api 2>&1 | grep "^{" | jq 'select(.level == "error")'

# Filter by endpoint
docker compose logs api 2>&1 | grep "^{" | jq 'select(.path | contains("/analytics/summary"))'

# Find slow requests
docker compose logs api 2>&1 | grep "^{" | jq 'select(.duration_ms > 1000)'

# Count errors by type
docker compose logs api 2>&1 | grep "^{" | jq -r '.event' | sort | uniq -c | sort -rn
```

### Dependency Injection Issues

If endpoints return 500 with dependency errors:

```bash
# Check deps.py for session/service wiring
# File: src/datapulse/api/deps.py

# Common issue: database session not yielding properly
# Verify with a minimal test:
docker exec datapulse-api python -c "
from datapulse.api.deps import get_db_session
session = next(get_db_session())
print('Session OK:', session)
session.close()
"
```

## Frontend Debugging

### Build Issues

```bash
# Check build logs
docker compose logs frontend

# Rebuild from scratch
docker compose build --no-cache frontend
docker compose up -d frontend

# Check for TypeScript errors locally
cd frontend && npx tsc --noEmit

# Check for lint errors
cd frontend && npx next lint
```

### Runtime Issues

```bash
# Check browser console for errors (use DevTools)
# Common issues:

# 1. API URL misconfiguration
# Check: frontend/src/lib/constants.ts -> API_URL
# Should be: http://localhost:8000 (or Docker service name)

# 2. CORS errors
# Check browser console for "Access-Control-Allow-Origin" errors
# Fix: verify CORS_ORIGINS in .env includes the frontend URL

# 3. SWR data not loading
# Check: Network tab in DevTools for failed API requests
# Check: API container is running and healthy
```

### SWR / Data Fetching

```typescript
// Enable SWR devtools in browser console:
// Add to providers.tsx temporarily:
// import { SWRDevTools } from 'swr-devtools';

// Common SWR issues:
// - Stale data: check revalidateOnFocus, refreshInterval in swr-config.ts
// - Infinite loading: check if API returns 401 (auth redirect loop)
// - Missing data: check API response shape matches TypeScript interface
```

### Theme Issues

```bash
# Dark/light mode uses next-themes with attribute="class"
# If theme doesn't apply:
# 1. Check <html> element has class="dark" or class="light"
# 2. Check Tailwind config includes darkMode: 'class'
# 3. Check CSS variables in globals.css for both themes
```

## dbt Debugging

### Model Build Failures

```bash
# Run a single model with debug logging
docker exec -it datapulse-app dbt run --select stg_sales --project-dir /app/dbt --profiles-dir /app/dbt --debug

# Check compiled SQL
cat dbt/target/compiled/datapulse/models/staging/stg_sales.sql

# Check run SQL (with actual values)
cat dbt/target/run/datapulse/models/staging/stg_sales.sql

# Test a model's SQL manually in psql
docker exec -it datapulse-db psql -U datapulse -f /path/to/compiled/sql
```

### Common dbt Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `Relation does not exist` | Source table not created yet | Run bronze loader first |
| `Column does not exist` | Schema drift in source | Check column_map.py, update model |
| `Permission denied` | Wrong DB role | Check profiles.yml credentials |
| `Compilation error` | Jinja syntax error | Check model SQL, run `dbt compile` |
| `Test failure` | Data quality issue | Check the failing assertion SQL |

### Dependency Graph

```bash
# View model lineage
docker exec -it datapulse-app dbt ls --resource-type model --project-dir /app/dbt --profiles-dir /app/dbt

# Generate docs (includes DAG visualization)
docker exec -it datapulse-app dbt docs generate --project-dir /app/dbt --profiles-dir /app/dbt
docker exec -it datapulse-app dbt docs serve --project-dir /app/dbt --profiles-dir /app/dbt --port 8081
# Open http://localhost:8081 in browser
```

## Pipeline Debugging

### Bronze Loader Issues

```bash
# Run loader with verbose output
docker exec -it datapulse-app python -m datapulse.bronze.loader \
  --source /app/data/raw/sales 2>&1 | head -50

# Check if source files exist
docker exec -it datapulse-app ls -la /app/data/raw/sales/

# Test file reading only (no DB)
docker exec -it datapulse-app python -m datapulse.bronze.loader \
  --source /app/data/raw/sales --skip-db
```

### Pipeline Run Tracking

```sql
-- Check recent pipeline runs
SELECT id, status, stage, started_at, completed_at,
       EXTRACT(EPOCH FROM (completed_at - started_at)) AS duration_seconds
FROM pipeline_runs
ORDER BY started_at DESC
LIMIT 10;

-- Check failed runs
SELECT id, status, stage, error_message, metadata
FROM pipeline_runs
WHERE status = 'failed'
ORDER BY started_at DESC
LIMIT 5;

-- Check quality results for a run
SELECT check_name, stage, passed, metric_value, details
FROM quality_checks
WHERE pipeline_run_id = 'your-run-uuid'
ORDER BY created_at;
```

## Keycloak Debugging

```bash
# Check Keycloak is healthy
curl http://localhost:8080/realms/datapulse

# View realm config
curl http://localhost:8080/admin/realms/datapulse \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Get admin token
ADMIN_TOKEN=$(curl -s -X POST http://localhost:8080/realms/master/protocol/openid-connect/token \
  -d "client_id=admin-cli" \
  -d "username=admin" \
  -d "password=<admin-password>" \
  -d "grant_type=password" | jq -r '.access_token')

# List users
curl http://localhost:8080/admin/realms/datapulse/users \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.[] | {username, enabled}'

# Check Keycloak logs
docker compose logs keycloak | tail -30
```

## n8n Debugging

```bash
# Check n8n container
docker compose logs n8n | tail -30

# Access n8n UI
# Open http://localhost:5678 in browser

# Check workflow executions via API
curl http://localhost:5678/api/v1/executions \
  -H "X-N8N-API-KEY: <your-key>" | jq '.data[:3]'

# Common issues:
# - Webhook not reachable: check n8n container can reach API container
# - Slack notifications failing: check SLACK_WEBHOOK_URL in .env
# - Redis connection: check redis container is running
```

## Emergency Procedures

### Full System Restart

```bash
docker compose down
docker compose up -d --build
# Wait for all services to be healthy
docker compose ps
```

### Database Recovery

```bash
# If postgres won't start with data corruption
docker compose stop postgres
docker volume ls | grep datapulse
# Backup the volume if possible, then:
docker compose up -d postgres

# Rerun migrations
for f in migrations/*.sql; do
  docker exec -i datapulse-db psql -U datapulse -d datapulse < "$f"
done

# Rebuild data pipeline
docker exec -it datapulse-app python -m datapulse.bronze.loader --source /app/data/raw/sales
docker exec -it datapulse-app dbt run --project-dir /app/dbt --profiles-dir /app/dbt
```

### Rollback a dbt Model Change

```bash
# dbt doesn't have built-in rollback, but you can:
# 1. Revert the model SQL change in git
git checkout HEAD~1 -- dbt/models/marts/aggs/agg_sales_daily.sql

# 2. Rerun the model
docker exec -it datapulse-app dbt run --select agg_sales_daily \
  --project-dir /app/dbt --profiles-dir /app/dbt
```
