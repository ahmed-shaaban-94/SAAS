# Performance Testing

Performance benchmarks and testing strategy for API response times, database query optimization, frontend metrics, and data pipeline throughput.

## Current Baselines

| Component | Metric | Current | Target |
|-----------|--------|---------|--------|
| API `/health` | Response time | < 50ms | < 100ms |
| API analytics endpoints | Response time (p95) | < 500ms | < 1000ms |
| API pipeline endpoints | Response time (p95) | < 300ms | < 500ms |
| Bronze loader | Throughput | ~50K rows/batch | 50K rows/batch |
| dbt full build | Duration | < 5 min | < 10 min |
| Frontend LCP | Largest Contentful Paint | < 2.5s | < 2.5s |
| Frontend FCP | First Contentful Paint | < 1.5s | < 1.5s |

## API Performance Testing

### Manual Benchmarking

```bash
# Single endpoint timing
curl -s -o /dev/null -w "DNS: %{time_namelookup}s\nConnect: %{time_connect}s\nTTFB: %{time_starttransfer}s\nTotal: %{time_total}s\n" \
  -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/analytics/summary

# All analytics endpoints
for endpoint in summary trends/daily trends/monthly products/top customers/top staff/top sites returns; do
  TIME=$(curl -s -o /dev/null -w "%{time_total}" \
    -H "Authorization: Bearer $TOKEN" \
    "http://localhost:8000/api/v1/analytics/$endpoint")
  echo "$endpoint: ${TIME}s"
done
```

### Load Testing with wrk

```bash
# Install wrk (if available)
# Simple load test: 10 concurrent connections, 30 seconds
wrk -t4 -c10 -d30s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/analytics/summary

# Expected output:
# Requests/sec: > 100
# Avg latency: < 500ms
# p99 latency: < 2000ms
```

### Load Testing with Python (TODO)

```python
# tests/performance/test_api_load.py
import asyncio
import time
import httpx

async def benchmark_endpoint(url: str, token: str, n_requests: int = 100):
    """Measure response times for N sequential requests."""
    times = []
    async with httpx.AsyncClient() as client:
        for _ in range(n_requests):
            start = time.perf_counter()
            resp = await client.get(url, headers={"Authorization": f"Bearer {token}"})
            elapsed = (time.perf_counter() - start) * 1000  # ms
            times.append(elapsed)
            assert resp.status_code == 200

    times.sort()
    return {
        "p50": times[len(times) // 2],
        "p95": times[int(len(times) * 0.95)],
        "p99": times[int(len(times) * 0.99)],
        "avg": sum(times) / len(times),
        "max": max(times),
    }
```

## Database Query Optimization

### Identifying Slow Queries

```sql
-- Enable pg_stat_statements (if not already)
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Top 10 slowest queries by total time
SELECT
    calls,
    ROUND(total_exec_time::numeric, 2) AS total_ms,
    ROUND(mean_exec_time::numeric, 2) AS avg_ms,
    ROUND(max_exec_time::numeric, 2) AS max_ms,
    LEFT(query, 100) AS query_preview
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;

-- Reset stats (after optimization)
SELECT pg_stat_statements_reset();
```

### EXPLAIN ANALYZE for Key Queries

```sql
-- Summary query (most called analytics endpoint)
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT * FROM public_marts.metrics_summary
WHERE date_key >= '2024-01-01' AND date_key <= '2024-12-31'
ORDER BY date_key DESC
LIMIT 1;

-- Top products query
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT * FROM public_marts.agg_sales_by_product
WHERE month_key >= '2024-01' AND month_key <= '2024-12'
ORDER BY net_sales DESC
LIMIT 10;

-- Daily trend query
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT * FROM public_marts.agg_sales_daily
WHERE date_key >= '2024-01-01' AND date_key <= '2024-12-31'
ORDER BY date_key;
```

### Index Recommendations

```sql
-- Check existing indexes
SELECT indexname, tablename, indexdef
FROM pg_indexes
WHERE schemaname = 'public_marts'
ORDER BY tablename, indexname;

-- Recommended indexes for analytics queries (TODO):
-- These should be created based on EXPLAIN ANALYZE results

-- Daily aggregation lookup by date
CREATE INDEX IF NOT EXISTS idx_agg_daily_date
ON public_marts.agg_sales_daily (date_key);

-- Monthly aggregation lookup by month
CREATE INDEX IF NOT EXISTS idx_agg_monthly_month
ON public_marts.agg_sales_monthly (month_key);

-- Product aggregation lookup by month + net_sales (for top-N)
CREATE INDEX IF NOT EXISTS idx_agg_product_month_sales
ON public_marts.agg_sales_by_product (month_key, net_sales DESC);

-- Metrics summary lookup by date
CREATE INDEX IF NOT EXISTS idx_metrics_date
ON public_marts.metrics_summary (date_key DESC);
```

### Connection Pool Monitoring

```sql
-- Current connections by state
SELECT state, COUNT(*)
FROM pg_stat_activity
WHERE datname = 'datapulse'
GROUP BY state;

-- Max connections setting
SHOW max_connections;

-- Connection pool config in SQLAlchemy
-- Check: src/datapulse/config.py or deps.py for pool_size, max_overflow
```

## Frontend Performance

### Lighthouse Audit

```bash
# Run Lighthouse via CLI (requires lighthouse npm package)
npx lighthouse http://localhost:3000 --output=json --output-path=./lighthouse-report.json

# Or use Chrome DevTools:
# 1. Open http://localhost:3000 in Chrome
# 2. DevTools -> Lighthouse tab
# 3. Check Performance, Accessibility, SEO
# 4. Generate report
```

### Target Scores

| Page | Performance | Accessibility | SEO | Best Practices |
|------|------------|---------------|-----|----------------|
| Landing (`/`) | 95+ | 95+ | 100 | 95+ |
| Dashboard (`/dashboard`) | 85+ | 90+ | N/A | 90+ |
| Products (`/products`) | 85+ | 90+ | N/A | 90+ |

### Bundle Analysis

```bash
# Analyze Next.js bundle
cd frontend && npx next build
# Check .next/analyze/ for bundle report (if @next/bundle-analyzer is configured)

# Or use built-in Next.js output
cd frontend && ANALYZE=true npx next build
```

### Key Frontend Metrics

| Metric | How to Measure | Target |
|--------|---------------|--------|
| FCP (First Contentful Paint) | Lighthouse / Web Vitals | < 1.5s |
| LCP (Largest Contentful Paint) | Lighthouse / Web Vitals | < 2.5s |
| CLS (Cumulative Layout Shift) | Lighthouse / Web Vitals | < 0.1 |
| FID (First Input Delay) | Real user monitoring | < 100ms |
| TTFB (Time to First Byte) | Lighthouse / curl | < 500ms |
| JS Bundle Size | Build output | < 200KB gzipped (first load) |

### SWR Caching

```typescript
// Check SWR config: frontend/src/lib/swr-config.ts
// Key settings that affect perceived performance:
// - dedupingInterval: prevents duplicate requests (default 2000ms)
// - revalidateOnFocus: refetch when tab regains focus
// - refreshInterval: polling interval (0 = disabled)
// - errorRetryCount: how many times to retry failed requests
```

## Data Pipeline Benchmarks

### Bronze Loader

```bash
# Time the full bronze load
time docker exec -it datapulse-app python -m datapulse.bronze.loader \
  --source /app/data/raw/sales

# Expected metrics:
# - File read (Excel -> Polars): < 30s per file
# - Parquet write: < 10s
# - DB insert (50K batch): < 5s per batch
# - Total for ~2.3M rows: < 5 min
```

### dbt Build

```bash
# Time full dbt build
time docker exec -it datapulse-app dbt run --project-dir /app/dbt --profiles-dir /app/dbt

# Time individual stages
time docker exec -it datapulse-app dbt run --select staging --project-dir /app/dbt --profiles-dir /app/dbt
time docker exec -it datapulse-app dbt run --select marts --project-dir /app/dbt --profiles-dir /app/dbt

# Expected:
# - Staging (stg_sales): < 60s
# - Dimensions: < 30s total
# - Fact table: < 120s
# - Aggregations: < 120s total
# - Full build: < 5 min
```

### Full Pipeline End-to-End

```bash
# Bronze + Staging + Marts via API trigger
time curl -X POST http://localhost:8000/api/v1/pipeline/trigger \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json"

# Expected: < 10 min for full pipeline
# Monitor progress via pipeline status endpoint
```

## Recommended Additions (TODO)

### Continuous Performance Monitoring

- [ ] Add API response time logging in structlog (duration_ms field)
- [ ] Create a Grafana dashboard for API latency (requires Prometheus)
- [ ] Add frontend Web Vitals reporting (e.g., `web-vitals` library + API endpoint)

### Regression Testing

- [ ] Save baseline performance numbers in a file
- [ ] Compare new builds against baseline
- [ ] Fail CI if p95 latency increases by > 20%

### Database Tuning

- [ ] Review `postgresql.conf` settings:
  - `shared_buffers` (25% of RAM)
  - `work_mem` (4MB per sort/hash)
  - `effective_cache_size` (75% of RAM)
  - `maintenance_work_mem` (for VACUUM/INDEX)
- [ ] Add `VACUUM ANALYZE` schedule for heavily-updated tables
- [ ] Consider partitioning `fct_sales` by date if data grows significantly

### Caching Layer

- [ ] Add Redis caching for expensive analytics queries
- [ ] Cache invalidation on pipeline completion
- [ ] Cache key based on tenant_id + query params + data freshness timestamp

## Performance Checklist

Before each release:

1. [ ] Run Lighthouse on landing page -- scores meet targets
2. [ ] Run Lighthouse on dashboard page -- scores meet targets
3. [ ] Benchmark all 10 analytics API endpoints -- p95 < 1s
4. [ ] Check `pg_stat_statements` for new slow queries
5. [ ] Verify JS bundle size has not grown significantly
6. [ ] Run full pipeline and verify duration is within bounds
7. [ ] Check Docker resource usage: `docker stats`
