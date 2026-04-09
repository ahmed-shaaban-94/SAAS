# DataPulse Operational Runbook

> Quick reference for on-call engineers. For disaster recovery, see [disaster-recovery.md](disaster-recovery.md).

---

## Table of Contents

1. [Service Overview](#1-service-overview)
2. [Deployment](#2-deployment)
3. [Database Migrations](#3-database-migrations)
4. [Bronze Ingestion Pipeline](#4-bronze-ingestion-pipeline)
5. [dbt Transformations](#5-dbt-transformations)
6. [Monitoring & Observability](#6-monitoring--observability)
7. [Common Incidents](#7-common-incidents)
8. [Maintenance Procedures](#8-maintenance-procedures)

---

## 1. Service Overview

| Service | Container | Port | Health Check |
|---------|-----------|------|-------------|
| FastAPI API | `datapulse-api` | 8000 | `GET /health` |
| Next.js Frontend | `datapulse-frontend` | 3000 | internal |
| PostgreSQL | `datapulse-db` | 5432 | `pg_isready` |
| Redis | `datapulse-redis` | 6379 | `redis-cli ping` |
| n8n | `datapulse-n8n` | 5678 | `GET /healthz` |
| Nginx | `datapulse-nginx` | 80/443 | proxy |

**Tech stack**: FastAPI (Python 3.11) + Next.js 14 + PostgreSQL 16 + dbt-core + Redis

---

## 2. Deployment

### Production deploy (CI/CD)

Deployments are triggered automatically by merging to `main`. The GitHub Actions workflow (`deploy-prod.yml`) handles:
1. Build Docker images
2. Trivy security scan (fail on CRITICAL/HIGH)
3. Push to registry
4. SSH deploy to DigitalOcean droplet

### Manual deploy (emergency)

```bash
# On the production server
cd /opt/datapulse
git pull origin main

# Rebuild and restart (zero-downtime with --no-deps)
docker compose -f docker-compose.yml -f docker-compose.prod.yml pull
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --no-deps api frontend nginx

# Verify health
curl -s http://localhost:8000/health | jq .
```

### Rollback

```bash
# Find the previous image tag
docker images datapulse-api --format "table {{.Tag}}\t{{.CreatedAt}}"

# Rollback to specific tag
IMAGE_TAG=<previous-tag> docker compose up -d --no-deps api
```

---

## 3. Database Migrations

Migrations run automatically on container startup via `scripts/prestart.sh`. If a migration fails, the container exits (non-zero) — this is intentional.

### Run migrations manually

```bash
docker exec datapulse-api bash scripts/prestart.sh
```

### Check migration status

```bash
docker exec datapulse-db psql -U datapulse -c \
    "SELECT id, name, applied_at FROM schema_migrations ORDER BY id;"
```

### Rollback a migration

Migrations are **not automatically reversible**. Each migration file has a rollback comment at the top. Execute the rollback SQL manually:

```bash
# Example: rollback migration 031
docker exec datapulse-db psql -U datapulse -c \
    "DROP INDEX IF EXISTS idx_agg_product_tenant_ym;"
```

---

## 4. Bronze Ingestion Pipeline

The bronze pipeline loads raw Excel/CSV files into `bronze.sales`.

### Trigger ingestion

```bash
# Via API (webhook)
curl -X POST https://smartdatapulse.tech/api/v1/pipeline/execute \
    -H "X-API-Key: $API_KEY" \
    -H "Content-Type: application/json" \
    -d '{"source": "/app/data/raw/sales"}'

# Or directly in container
docker exec datapulse-api python -m datapulse.bronze.loader \
    --source /app/data/raw/sales
```

### Monitor pipeline run

```bash
# Check latest runs
docker exec datapulse-db psql -U datapulse -c \
    "SELECT id, status, started_at, completed_at, error_message
     FROM pipeline_runs ORDER BY started_at DESC LIMIT 5;"

# Live logs
docker logs datapulse-api --follow --since 5m 2>&1 | grep '"pipeline_run_id"'
```

### Pipeline stuck or failed

```bash
# Check for stuck 'running' runs (> 30 min old)
docker exec datapulse-db psql -U datapulse -c \
    "SELECT id, status, started_at
     FROM pipeline_runs
     WHERE status = 'running'
       AND started_at < NOW() - INTERVAL '30 minutes';"

# Mark stuck run as failed
docker exec datapulse-db psql -U datapulse -c \
    "UPDATE pipeline_runs
     SET status = 'failed', error_message = 'manually terminated (stuck)'
     WHERE id = '<run_id>';"
```

---

## 5. dbt Transformations

dbt transforms bronze → silver → gold. Must be run after any bronze ingestion.

### Run all models

```bash
docker exec datapulse-api bash -c "cd /app/dbt && dbt run"
```

### Run specific layers

```bash
# Silver only
docker exec datapulse-api bash -c "cd /app/dbt && dbt run --select staging"

# Gold only
docker exec datapulse-api bash -c "cd /app/dbt && dbt run --select marts"

# Single model
docker exec datapulse-api bash -c "cd /app/dbt && dbt run --select fct_sales"
```

### Run dbt tests

```bash
docker exec datapulse-api bash -c "cd /app/dbt && dbt test"
```

### dbt run failures

```bash
# Check which models failed
docker exec datapulse-api bash -c \
    "cd /app/dbt && dbt run 2>&1 | grep -E 'ERROR|FAIL'"

# Check a specific model's compiled SQL
docker exec datapulse-api bash -c \
    "cd /app/dbt && cat target/compiled/datapulse/models/staging/stg_sales.sql"
```

---

## 6. Monitoring & Observability

### Application metrics (Prometheus)

The `/metrics` endpoint is exposed internally on port 8000. Nginx blocks it from the public internet. Prometheus scrapes it via Docker network:

```
http://datapulse-api:8000/metrics
```

Key metrics:
- `http_requests_total` — Request count by method, handler, status code
- `http_request_duration_seconds` — P50/P95/P99 latency per endpoint

### Slow query monitoring (pg_stat_statements)

```sql
-- Top 20 slowest queries
SELECT
    ROUND(mean_exec_time::numeric, 2) AS mean_ms,
    ROUND(total_exec_time::numeric, 2) AS total_ms,
    calls,
    LEFT(query, 100) AS query_preview
FROM pg_stat_statements
ORDER BY total_exec_time DESC
LIMIT 20;

-- Reset stats after a deployment
SELECT pg_stat_statements_reset();
```

Run via:
```bash
docker exec datapulse-db psql -U datapulse -c "<query above>"
```

### Structured logs

Nginx access logs are in JSON format. Parse with jq:

```bash
# Follow live access logs
docker exec datapulse-nginx tail -f /var/log/nginx/access.log | jq .

# Top 10 slowest requests in the last hour
docker exec datapulse-nginx bash -c \
    "tail -n 5000 /var/log/nginx/access.log | jq -r '.request_time + \" \" + .uri'" \
    | sort -rn | head -10
```

Application logs (structlog JSON):
```bash
docker logs datapulse-api --since 1h 2>&1 | jq -c 'select(.level == "error")'
```

### Health check

```bash
curl -s https://smartdatapulse.tech/health | jq .
# Healthy: {"status": "healthy", "checks": {...}}
# Degraded: {"status": "degraded", ...} (DB unreachable returns 503)
```

---

## 7. Common Incidents

### API returns 502/504

**Symptoms**: Nginx returns 502 Bad Gateway or 504 Gateway Timeout.

```bash
# 1. Check if API container is running
docker ps | grep datapulse-api

# 2. Check API health directly
docker exec datapulse-api curl -s http://localhost:8000/health

# 3. Check API logs for errors
docker logs datapulse-api --tail 100 2>&1 | jq -c 'select(.level == "error")'

# 4. Restart API if unhealthy
docker compose restart api
```

### Database connection errors

```bash
# Check postgres is up
docker exec datapulse-db pg_isready -U datapulse

# Check connection count (max 100)
docker exec datapulse-db psql -U datapulse -c \
    "SELECT count(*), state FROM pg_stat_activity GROUP BY state;"

# Check for long-running queries (> 30s)
docker exec datapulse-db psql -U datapulse -c \
    "SELECT pid, query_start, state, LEFT(query, 80) AS query
     FROM pg_stat_activity
     WHERE query_start < NOW() - INTERVAL '30 seconds'
       AND state != 'idle';"

# Kill a blocking query
docker exec datapulse-db psql -U datapulse -c \
    "SELECT pg_terminate_backend(<pid>);"
```

### Redis unavailable

Redis is used by n8n and optionally for API caching. API continues to function without Redis (falls back to DB queries).

```bash
docker compose restart redis
```

### Authentication failures (401 spikes)

Auth0 outage or misconfigured JWT audience.

```bash
# Check API logs for auth errors
docker logs datapulse-api --since 10m 2>&1 | \
    jq -c 'select(.event == "auth_error" or .event == "jwt_error")'

# Verify AUTH0_DOMAIN and AUTH0_AUDIENCE env vars
docker exec datapulse-api env | grep AUTH0
```

### dbt run fails after migration

If a migration added/removed columns, dbt models may fail with `column does not exist`.

```bash
# 1. Run migrations first
docker exec datapulse-api bash scripts/prestart.sh

# 2. Then run dbt
docker exec datapulse-api bash -c "cd /app/dbt && dbt run"

# 3. If model fails, check compiled SQL
docker exec datapulse-api bash -c \
    "cd /app/dbt && dbt run --select <failing_model> 2>&1 | tail -20"
```

---

## 8. Maintenance Procedures

### Restart all services

```bash
docker compose down
docker compose up -d
```

### Check disk usage

```bash
# Database size
docker exec datapulse-db psql -U datapulse -c \
    "SELECT pg_size_pretty(pg_database_size('datapulse'));"

# Table sizes
docker exec datapulse-db psql -U datapulse -c \
    "SELECT relname, pg_size_pretty(pg_total_relation_size(oid))
     FROM pg_class WHERE relkind = 'r'
     ORDER BY pg_total_relation_size(oid) DESC LIMIT 10;"

# Docker volumes
docker system df
```

### Manual vacuum (large table bloat)

```bash
docker exec datapulse-db psql -U datapulse -c \
    "VACUUM (ANALYZE, VERBOSE) bronze.sales;"
```

### Clear Redis cache

```bash
docker exec datapulse-redis redis-cli FLUSHDB
```

### Rotate API key

```bash
# 1. Generate a new key
NEW_KEY=$(openssl rand -hex 32)
echo "New API_KEY: $NEW_KEY"

# 2. Update .env
# 3. Restart API
docker compose up -d --no-deps api

# 4. Update n8n workflow credentials and any external integrations
```
