# Validation & Debugging (COMPLETED)

> **Note (2026-04)**: Keycloak references below are historical. Auth is now handled by Auth0.

> All validation, testing, and debugging documentation consolidated. This is the reference document.

---

# Validation and Debugging

Comprehensive testing, validation, and debugging guides for the DataPulse platform.

## Purpose

These documents serve as actionable references for:

1. **Running and extending tests** across all layers of the stack
2. **Validating data quality** through the medallion pipeline
3. **Auditing security** controls (auth, RLS, CORS, headers)
4. **Diagnosing issues** with a structured debugging runbook
5. **Measuring performance** against defined baselines

## Documents

| Document | Scope |
|----------|-------|
| [Backend Testing](./backend-testing.md) | Python: pytest, fixtures, mocking, coverage |
| [Frontend Testing](./frontend-testing.md) | Next.js: Playwright E2E, component testing |
| [dbt Testing](./dbt-testing.md) | dbt: schema tests, data tests, source freshness |
| [Data Quality](./data-quality.md) | Pipeline: 7 quality checks, gates, flow |
| [Security Audit](./security-audit.md) | OWASP, RLS, auth, CORS, headers |
| [Debugging Runbook](./debugging-runbook.md) | Troubleshooting across all services |
| [Performance Testing](./performance-testing.md) | API, DB, frontend, pipeline benchmarks |

## Current State

| Layer | Coverage / Status |
|-------|------------------|
| Python backend | 95%+ line coverage (pytest-cov) |
| Frontend E2E | 18+ Playwright specs across 6+ files |
| dbt models | ~40 schema + data tests |
| Data quality | 7 check functions, quality gate logic |
| Security | Keycloak OIDC, tenant-scoped RLS, rate limiting |
| Docker | 8 services, all health-checked |

## Quick Start

```bash
# Backend tests
docker exec -it datapulse-app pytest --cov=src/datapulse --cov-report=term-missing

# Frontend E2E tests
docker compose exec frontend npx playwright test

# dbt tests
docker exec -it datapulse-app dbt test --project-dir /app/dbt --profiles-dir /app/dbt

# All checks in sequence
docker exec -it datapulse-app pytest && \
docker compose exec frontend npx playwright test && \
docker exec -it datapulse-app dbt test --project-dir /app/dbt --profiles-dir /app/dbt
```

---

## Backend Testing

Python testing for the DataPulse backend: FastAPI API, data pipeline, analytics, and infrastructure.

## Current State (DONE)

- **Framework**: pytest + pytest-cov
- **Coverage**: 95%+ on `src/datapulse/`
- **Test files**: `tests/conftest.py`, `test_reader.py`, `test_type_detector.py`, `test_config.py`, `test_validator.py`, `test_loader.py`, `test_coverage_gaps.py`
- **Total tests**: 100+ across all modules

## Running Tests

```bash
# Full test suite with coverage
docker exec -it datapulse-app pytest --cov=src/datapulse --cov-report=term-missing

# Specific module
docker exec -it datapulse-app pytest tests/test_reader.py -v

# Single test
docker exec -it datapulse-app pytest tests/test_reader.py::test_read_csv_basic -v

# With output visible
docker exec -it datapulse-app pytest -s --tb=short

# Coverage report as HTML
docker exec -it datapulse-app pytest --cov=src/datapulse --cov-report=html
# Output in htmlcov/ directory
```

## Test Categories

### 1. Unit Tests

Tests for isolated functions and classes with no external dependencies.

| Module | File | What It Tests |
|--------|------|---------------|
| `import_pipeline.reader` | `test_reader.py` | `read_csv()`, `read_excel()`, `read_file()` -- file parsing with Polars |
| `import_pipeline.type_detector` | `test_type_detector.py` | Auto-detection of column types from DataFrames |
| `import_pipeline.validator` | `test_validator.py` | File size, format, and column validation |
| `config` | `test_config.py` | Pydantic settings loading, defaults, env overrides |
| `bronze.column_map` | `test_coverage_gaps.py` | Excel header to DB column mapping |
| `pipeline.quality` | `test_coverage_gaps.py` | 7 quality check functions |

### 2. Integration Tests

Tests that interact with the database or external services.

| Module | What It Tests |
|--------|---------------|
| `bronze.loader` | Full Excel -> Polars -> Parquet -> PostgreSQL pipeline |
| `analytics.repository` | SQLAlchemy queries against marts schema |
| `analytics.service` | Business logic with default filters |
| `pipeline.repository` | CRUD for pipeline_runs table |
| `pipeline.service` | Pipeline lifecycle (start/complete/fail) |
| `pipeline.executor` | Bronze loader and dbt subprocess execution |
| `pipeline.quality_repository` | Quality check persistence |
| `pipeline.quality_service` | Quality gate orchestration |

### 3. API Tests

Tests for FastAPI endpoints using `TestClient`.

| Endpoint Group | Routes Tested |
|---------------|---------------|
| Health | `GET /health` (200 OK, 503 DB down) |
| Analytics | 10 endpoints under `/api/v1/analytics/` |
| Pipeline | 11 endpoints under `/api/v1/pipeline/` |

## Fixtures (`tests/conftest.py`)

Key fixtures to understand and reuse:

```python
# Database session (uses test database or mocked)
@pytest.fixture
def db_session():
    """Provides a SQLAlchemy session scoped to a single test."""

# FastAPI test client
@pytest.fixture
def client(db_session):
    """TestClient with dependency overrides for DB session."""

# Sample DataFrames
@pytest.fixture
def sample_sales_df():
    """Polars DataFrame matching bronze.sales schema."""

# Temporary files for import tests
@pytest.fixture
def sample_csv(tmp_path):
    """Creates a temporary CSV file for import testing."""

@pytest.fixture
def sample_excel(tmp_path):
    """Creates a temporary Excel file for import testing."""
```

## Mocking Patterns

### Database Mocking

```python
from unittest.mock import MagicMock, patch

# Mock the session
mock_session = MagicMock()
mock_session.execute.return_value.scalars.return_value.all.return_value = [...]

# Patch at the dependency injection level
with patch("datapulse.api.deps.get_db_session", return_value=mock_session):
    response = client.get("/api/v1/analytics/summary")
```

### Subprocess Mocking (for dbt)

```python
@patch("subprocess.run")
def test_dbt_execution(mock_run):
    mock_run.return_value = CompletedProcess(args=[], returncode=0, stdout="OK")
    result = executor.run_dbt_stage("staging")
    assert result.success is True
```

### External Service Mocking

```python
# Mock Polars file reading
@patch("polars.read_excel")
def test_read_excel(mock_read):
    mock_read.return_value = pl.DataFrame({"col1": [1, 2, 3]})
    result = read_file("test.xlsx")
    assert result.row_count == 3
```

## Coverage Targets

| Module | Current | Target | Notes |
|--------|---------|--------|-------|
| `config.py` | 95%+ | 90% | Env var edge cases |
| `bronze/` | 95%+ | 90% | Loader + column_map |
| `import_pipeline/` | 95%+ | 90% | Reader + validator + type detector |
| `analytics/` | 95%+ | 85% | Repository queries need live DB |
| `pipeline/` | 95%+ | 85% | Executor subprocess mocking |
| `api/` | 95%+ | 85% | All routes via TestClient |
| **Overall** | **95%+** | **80%** | Minimum acceptable |

## Recommended Additions (TODO)

### Property-Based Testing

```bash
pip install hypothesis
```

Use Hypothesis for data-heavy modules:

- [ ] `type_detector.py` -- random DataFrames with mixed types
- [ ] `validator.py` -- boundary values for file sizes and row counts
- [ ] `column_map.py` -- fuzzy header matching edge cases

### Load Testing for API

```bash
pip install locust
```

- [ ] Locustfile for analytics endpoints under concurrent load
- [ ] Measure response times at 10, 50, 100 concurrent users

### Contract Testing

- [ ] Validate API responses against Pydantic models programmatically
- [ ] Ensure frontend TypeScript types stay in sync with backend models

### Test Organization

- [ ] Split `test_coverage_gaps.py` into module-specific files
- [ ] Add `tests/api/` directory for endpoint tests
- [ ] Add `tests/integration/` directory for DB-dependent tests
- [ ] Add pytest markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.slow`

```ini
# pyproject.toml addition
[tool.pytest.ini_options]
markers = [
    "unit: fast tests with no external deps",
    "integration: tests requiring database",
    "slow: tests taking > 5 seconds",
]
```

## Checklist for Adding New Tests

1. Identify the module and function under test
2. Check if a fixture already exists in `conftest.py`
3. Write the test following existing patterns (arrange/act/assert)
4. Mock external dependencies (DB, filesystem, subprocess)
5. Run with coverage to verify the new code is covered
6. Ensure the test is deterministic (no random failures, no time dependencies)

---

## Data Quality

Data quality framework for the DataPulse medallion pipeline: 7 quality check functions, quality gates, and pipeline integration.

## Current State (DONE)

- **Module**: `src/datapulse/pipeline/quality.py`
- **Service**: `src/datapulse/pipeline/quality_service.py`
- **Repository**: `src/datapulse/pipeline/quality_repository.py`
- **Table**: `public.quality_checks` (with RLS)
- **API**: `GET /api/v1/pipeline/{run_id}/quality`, `POST /api/v1/pipeline/{run_id}/quality-check`
- **Tests**: 79 tests covering quality functions, repository, and service

## The 7 Quality Checks

Each check function returns a `QualityCheckResult` with `passed: bool`, `metric_value: float`, and `details: dict`.

### 1. Row Count Check

**Purpose**: Verify the output row count is within expected bounds.

```python
def check_row_count(actual: int, expected_min: int, expected_max: int) -> QualityCheckResult
```

- **When**: After each pipeline stage (bronze, staging, marts)
- **Pass condition**: `expected_min <= actual <= expected_max`
- **Example**: Bronze load expects 1M-3M rows; staging expects 50-100% of bronze (deduplication)

### 2. Null Rate Check

**Purpose**: Ensure critical columns do not exceed a null threshold.

```python
def check_null_rate(null_count: int, total_count: int, threshold: float) -> QualityCheckResult
```

- **When**: After staging and marts
- **Pass condition**: `null_count / total_count <= threshold`
- **Example**: `reference_no` should have < 1% nulls; `customer_name` should have < 5% nulls

### 3. Schema Drift Check

**Purpose**: Detect unexpected column additions, removals, or type changes.

```python
def check_schema_drift(expected_columns: list[str], actual_columns: list[str]) -> QualityCheckResult
```

- **When**: After bronze load (source schema may change)
- **Pass condition**: Expected columns are a subset of actual columns (new columns are warnings, missing columns fail)

### 4. Duplicate Check

**Purpose**: Detect duplicate rows on a key column.

```python
def check_duplicates(total_count: int, distinct_count: int, threshold: float) -> QualityCheckResult
```

- **When**: After staging (deduplication should have run)
- **Pass condition**: `(total_count - distinct_count) / total_count <= threshold`

### 5. Value Range Check

**Purpose**: Verify numeric values fall within acceptable bounds.

```python
def check_value_range(min_val: float, max_val: float, expected_min: float, expected_max: float) -> QualityCheckResult
```

- **When**: After marts aggregation
- **Pass condition**: `expected_min <= min_val` and `max_val <= expected_max`
- **Example**: `net_sales` should be between -1M and 10M per transaction

### 6. Freshness Check

**Purpose**: Verify data is not stale (most recent record is within expected recency).

```python
def check_freshness(latest_date: datetime, max_age_hours: int) -> QualityCheckResult
```

- **When**: After bronze load
- **Pass condition**: `now() - latest_date <= max_age_hours`

### 7. Referential Integrity Check

**Purpose**: Verify foreign keys resolve to existing dimension records.

```python
def check_referential_integrity(orphan_count: int, total_count: int, threshold: float) -> QualityCheckResult
```

- **When**: After marts fact table build
- **Pass condition**: `orphan_count / total_count <= threshold`
- **Example**: All `fct_sales.customer_key` values should exist in `dim_customer`

## Quality Gate Logic

The quality service orchestrates checks and determines pass/fail:

```
Pipeline Stage Completes
        |
        v
  Run Quality Checks (1-N checks per stage)
        |
        v
  Persist Results to quality_checks table
        |
        v
  Evaluate Gate: ALL checks passed?
       / \
      /   \
   YES     NO
    |       |
    v       v
  Continue  Fail Pipeline
  to next   (mark run as failed,
  stage     log details)
```

### Gate Modes

| Mode | Behaviour |
|------|-----------|
| **Strict** | Any check failure fails the pipeline |
| **Warn** | Failures are logged but pipeline continues |
| **Threshold** | Pipeline fails only if > N checks fail |

## Pipeline Integration

Quality checks run at three points in the pipeline:

| Stage | Checks Run | Gate Mode |
|-------|-----------|-----------|
| After Bronze | row_count, schema_drift, freshness | Strict |
| After Staging (Silver) | row_count, null_rate, duplicates | Strict |
| After Marts (Gold) | row_count, value_range, referential_integrity | Strict |

### n8n Workflow Integration

The `2.3.1_full_pipeline_webhook.json` workflow includes quality gate nodes:

```
Webhook -> Bronze -> QC -> Staging -> QC -> Marts -> QC -> Success
                     |                |              |
                     v                v              v
                  Fail Alert      Fail Alert      Fail Alert
```

## API Endpoints

### Get Quality Results

```bash
# Get all quality check results for a pipeline run
curl http://localhost:8000/api/v1/pipeline/{run_id}/quality
```

Response:

```json
{
  "checks": [
    {
      "id": 1,
      "pipeline_run_id": "uuid",
      "check_name": "row_count",
      "stage": "bronze",
      "passed": true,
      "metric_value": 1134073.0,
      "details": {"expected_min": 1000000, "expected_max": 3000000},
      "created_at": "2025-01-15T10:00:00Z"
    }
  ]
}
```

### Trigger Quality Check

```bash
# Run a specific quality check for a pipeline run
curl -X POST http://localhost:8000/api/v1/pipeline/{run_id}/quality-check \
  -H "Content-Type: application/json" \
  -d '{"check_name": "row_count", "stage": "bronze"}'
```

## Database Schema

```sql
-- public.quality_checks
CREATE TABLE quality_checks (
    id SERIAL PRIMARY KEY,
    pipeline_run_id UUID NOT NULL REFERENCES pipeline_runs(id),
    check_name VARCHAR(100) NOT NULL,
    stage VARCHAR(50) NOT NULL,
    passed BOOLEAN NOT NULL,
    metric_value NUMERIC,
    details JSONB,
    tenant_id UUID NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- RLS enabled
ALTER TABLE quality_checks ENABLE ROW LEVEL SECURITY;
ALTER TABLE quality_checks FORCE ROW LEVEL SECURITY;
```

## Recommended Additions (TODO)

### Statistical Checks

- [ ] Standard deviation check -- flag values > 3 sigma from mean
- [ ] Distribution check -- detect skew changes between runs
- [ ] Trend check -- alert when metrics change > X% from previous run

### Historical Comparison

- [ ] Compare current check results against the last N runs
- [ ] Detect gradual degradation trends
- [ ] Store historical baselines per check

### Alert Enrichment

- [ ] Include sample failing rows in quality check details
- [ ] Add remediation suggestions to check results
- [ ] Link to specific dbt test failures when applicable

### Dashboard Integration

- [ ] Display quality check history on the pipeline dashboard
- [ ] Show pass/fail trends over time
- [ ] Quality score metric (% of checks passing over last 30 days)

---

## dbt Testing

Testing strategy for dbt models across the medallion architecture: bronze sources, staging (silver), and marts (gold).

## Current State (DONE)

- **Framework**: dbt-core + dbt-postgres
- **Tests**: ~40 schema tests + data tests
- **Models**: 1 staging + 6 dims + 1 fact + 8 aggs + 1 metrics
- **Schema files**: `_bronze__sources.yml`, `_staging__sources.yml`, `_dims__models.yml`, `_facts__models.yml`, `_aggs__models.yml`

## Running Tests

```bash
# All dbt tests
docker exec -it datapulse-app dbt test --project-dir /app/dbt --profiles-dir /app/dbt

# Tests for a specific model
docker exec -it datapulse-app dbt test --select stg_sales --project-dir /app/dbt --profiles-dir /app/dbt

# Tests for a schema/directory
docker exec -it datapulse-app dbt test --select marts.dims --project-dir /app/dbt --profiles-dir /app/dbt

# Single named test
docker exec -it datapulse-app dbt test --select test_name --project-dir /app/dbt --profiles-dir /app/dbt

# Run models then test
docker exec -it datapulse-app dbt build --project-dir /app/dbt --profiles-dir /app/dbt
```

## Test Types

### 1. Schema Tests (Generic)

Defined in YAML schema files. These are declarative column-level assertions.

| Test | Purpose | Example |
|------|---------|---------|
| `unique` | No duplicate values in column | `dim_customer.customer_key` |
| `not_null` | No NULL values in column | `fct_sales.sale_key` |
| `accepted_values` | Column contains only expected values | `dim_billing.billing_group` |
| `relationships` | Foreign key integrity | `fct_sales.customer_key -> dim_customer.customer_key` |

Example from `_dims__models.yml`:

```yaml
models:
  - name: dim_customer
    columns:
      - name: customer_key
        tests:
          - unique
          - not_null
      - name: customer_name
        tests:
          - not_null
```

### 2. Data Tests (Custom SQL)

Custom SQL assertions in `dbt/tests/` directory. A test fails if the query returns any rows.

```sql
-- tests/assert_no_negative_net_sales.sql
SELECT *
FROM {{ ref('fct_sales') }}
WHERE net_sales < 0
  AND billing_type NOT IN ('returns', 'credit_note')
```

### 3. Source Freshness

Checks that source data is not stale.

```bash
docker exec -it datapulse-app dbt source freshness --project-dir /app/dbt --profiles-dir /app/dbt
```

Defined in `_bronze__sources.yml`:

```yaml
sources:
  - name: bronze
    tables:
      - name: sales
        loaded_at_field: _loaded_at
        freshness:
          warn_after: { count: 24, period: hour }
          error_after: { count: 48, period: hour }
```

## Model Coverage

### Staging (`stg_sales`)

| Test | Column | Status |
|------|--------|--------|
| `not_null` | `reference_no` | DONE |
| `not_null` | `date` | DONE |
| Deduplication check | (row count vs bronze) | DONE |
| Billing type EN mapping | `billing_type` | DONE |
| Derived field logic | Various | DONE |

### Dimensions

| Model | Tests | Key Assertions |
|-------|-------|---------------|
| `dim_date` | unique, not_null on `date_key` | 1,096 rows (2023-2025) |
| `dim_billing` | unique, not_null, accepted_values | 11 rows (10 types + Unknown) |
| `dim_customer` | unique, not_null on `customer_key` | Unknown member at key=-1 |
| `dim_product` | unique, not_null on `product_key` | Unknown member at key=-1 |
| `dim_site` | unique, not_null on `site_key` | Unknown member at key=-1 |
| `dim_staff` | unique, not_null on `staff_key` | Unknown member at key=-1 |

### Fact Table (`fct_sales`)

| Test | Column | Notes |
|------|--------|-------|
| `not_null` | All FK columns | COALESCE to -1 ensures no NULLs |
| `relationships` | All FK columns | Reference their dimension tables |
| `not_null` | `net_sales`, `gross_sales` | Financial measures always present |

### Aggregation Tables

| Model | Key Tests |
|-------|-----------|
| `agg_sales_daily` | not_null on date_key, unique on date_key |
| `agg_sales_monthly` | not_null, MoM/YoY calculations correct |
| `agg_sales_by_product` | not_null on product_key + month_key |
| `agg_sales_by_customer` | not_null on customer_key + month_key |
| `agg_sales_by_site` | not_null on site_key + month_key |
| `agg_sales_by_staff` | not_null on staff_key + month_key |
| `agg_returns` | not_null, return quantities positive |
| `metrics_summary` | not_null, MTD/YTD running totals non-negative |

## Recommended Additions (TODO)

### Row Count Assertions

- [ ] Add `dbt_utils.equal_rowcount` between related tables
- [ ] Add minimum row count assertions for critical tables

```yaml
# Requires dbt-utils package
tests:
  - dbt_utils.equal_rowcount:
      compare_model: ref('stg_sales')
```

### Referential Integrity Across Layers

- [ ] Verify every `fct_sales` FK resolves to a dimension row
- [ ] Verify agg tables sum to fct_sales totals (reconciliation)

```sql
-- tests/assert_agg_daily_matches_fact.sql
WITH fact_total AS (
    SELECT SUM(net_sales) AS total FROM {{ ref('fct_sales') }}
),
agg_total AS (
    SELECT SUM(net_sales) AS total FROM {{ ref('agg_sales_daily') }}
)
SELECT * FROM fact_total f
CROSS JOIN agg_total a
WHERE ABS(f.total - a.total) > 0.01
```

### Financial Precision Tests

- [ ] Verify NUMERIC(18,4) precision is maintained (no floating-point drift)
- [ ] Assert `gross_sales >= net_sales` where applicable

### Schema Drift Detection

- [ ] Compare expected column list against actual table schema
- [ ] Alert on unexpected columns or type changes

### Continuous Testing

- [ ] Run `dbt test` as part of pipeline execution (after each stage)
- [ ] This is partially done via quality gates in Phase 2.5
- [ ] Add `dbt build` (run + test) to the n8n pipeline workflow

## Test Development Checklist

1. Define expected behaviour in the schema YAML
2. Add `unique` and `not_null` on all primary keys
3. Add `relationships` for all foreign keys
4. Add `accepted_values` for enum-like columns
5. Write custom SQL tests for business logic assertions
6. Run `dbt test` and verify all pass
7. Check test results in the dbt log or `target/run_results.json`

---

## Debugging Runbook

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

---

## Frontend Testing

Testing strategy for the Next.js 14 frontend: Playwright E2E tests and component testing.

## Current State (DONE)

- **E2E Framework**: Playwright (Chromium)
- **Test count**: 18+ specs across 6+ files
- **Config**: `frontend/playwright.config.ts`
- **Test directory**: `frontend/e2e/`

## Running Tests

```bash
# All E2E tests (Docker)
docker compose exec frontend npx playwright test

# All E2E tests (local)
cd frontend && npx playwright test

# Specific test file
npx playwright test e2e/dashboard.spec.ts

# With headed browser (local dev only)
npx playwright test --headed

# With UI mode (local dev only)
npx playwright test --ui

# Generate report
npx playwright test --reporter=html
npx playwright show-report
```

## Test Files

| File | Specs | Coverage Area |
|------|-------|---------------|
| `e2e/dashboard.spec.ts` | KPI cards, trend charts, filter bar | Executive overview page |
| `e2e/navigation.spec.ts` | Sidebar nav, active highlight, root redirect | App navigation |
| `e2e/filters.spec.ts` | Date preset clicks | Filter bar functionality |
| `e2e/pages.spec.ts` | All 5 analytics pages load | Page rendering |
| `e2e/health.spec.ts` | API health indicator | Health dot component |
| `e2e/pipeline.spec.ts` | Pipeline dashboard: title, trigger, overview, nav | Pipeline page |
| `e2e/website.spec.ts` | Public website: hero, features, pricing, FAQ, etc. | Marketing pages |

## Playwright Configuration

Key settings in `frontend/playwright.config.ts`:

```typescript
export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  expect: { timeout: 5_000 },
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
});
```

## Test Patterns

### Page Load Test

```typescript
test('dashboard page loads', async ({ page }) => {
  await page.goto('/dashboard');
  await expect(page.getByRole('heading', { name: /overview/i })).toBeVisible();
});
```

### API-Dependent Test

```typescript
test('KPI cards display data', async ({ page }) => {
  await page.goto('/dashboard');
  // Wait for SWR to fetch and render
  await expect(page.getByTestId('kpi-grid')).toBeVisible();
  const cards = page.getByTestId('kpi-card');
  await expect(cards).toHaveCount(7);
});
```

### Interactive Test

```typescript
test('FAQ accordion expands on click', async ({ page }) => {
  await page.goto('/');
  const faqItem = page.getByRole('button', { name: /what is datapulse/i });
  await faqItem.click();
  await expect(page.getByText(/datapulse is a data analytics/i)).toBeVisible();
});
```

### Accessibility Test

```typescript
test('skip-to-content link works', async ({ page }) => {
  await page.goto('/');
  await page.keyboard.press('Tab');
  const skipLink = page.getByRole('link', { name: /skip to content/i });
  await expect(skipLink).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(page.locator('#main-content')).toBeFocused();
});
```

## Test Data Strategy

- **API mocking**: Tests run against the real API (integration style). The API container must be running.
- **No mock service worker**: Tests validate the full stack from browser to database.
- **Stable selectors**: Use `data-testid`, `role`, and accessible names -- not CSS classes.

## Recommended Additions (TODO)

### Component Testing

Playwright supports component testing, or use Vitest + Testing Library:

```bash
npm install -D vitest @testing-library/react @testing-library/jest-dom
```

Priority components for unit tests:

- [ ] `kpi-card.tsx` -- renders correct value, trend indicator, formatting
- [ ] `filter-bar.tsx` -- date presets update context
- [ ] `ranking-table.tsx` -- sorts data, handles empty state
- [ ] `formatters.ts` -- currency (EGP), percent, compact number formatting
- [ ] `date-utils.ts` -- `parseDateKey`, date presets
- [ ] `api-client.ts` -- `fetchAPI` error handling, Decimal parsing

### Visual Regression

- [ ] Add `@playwright/test` screenshot comparison for key pages
- [ ] Capture baseline screenshots for dashboard, products, landing page
- [ ] Compare on each PR to catch unintended visual changes

```typescript
test('dashboard visual regression', async ({ page }) => {
  await page.goto('/dashboard');
  await page.waitForLoadState('networkidle');
  await expect(page).toHaveScreenshot('dashboard.png', { maxDiffPixels: 100 });
});
```

### Mobile Testing

- [ ] Add a mobile viewport project to Playwright config

```typescript
projects: [
  { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  { name: 'mobile', use: { ...devices['iPhone 13'] } },
],
```

- [ ] Test sidebar drawer, mobile menu, responsive layouts

### Accessibility Automation

- [ ] Integrate `@axe-core/playwright` for automated a11y scanning

```typescript
import AxeBuilder from '@axe-core/playwright';

test('dashboard has no a11y violations', async ({ page }) => {
  await page.goto('/dashboard');
  const results = await new AxeBuilder({ page }).analyze();
  expect(results.violations).toEqual([]);
});
```

### Test Coverage Goals

| Area | Current | Target |
|------|---------|--------|
| Page loads (all routes) | DONE | Maintain |
| KPI rendering | DONE | Maintain |
| Navigation | DONE | Maintain |
| Filters | DONE | Add date range picker |
| Theme toggle | DONE | Add visual regression |
| Public website | DONE | Maintain |
| Component units | None | 20+ specs |
| Mobile viewport | None | 10+ specs |
| Accessibility (axe) | None | All pages |

## Debugging Failed Tests

```bash
# Run with trace
npx playwright test --trace on

# View trace
npx playwright show-trace trace.zip

# Run with debug mode (pauses on failure)
PWDEBUG=1 npx playwright test

# Screenshot on failure (already in config via trace: 'on-first-retry')
# Check test-results/ directory after failures
```

---

## Performance Testing

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

---

## Security Audit

Security validation checklist for the DataPulse platform: authentication, authorization, data isolation, network security, and OWASP controls.

## Current State (DONE)

- **Authentication**: Keycloak OIDC with JWT validation
- **Authorization**: Tenant-scoped RLS on all data tables
- **Users**: `demo-admin` (admin role), `demo-viewer` (viewer role)
- **Rate limiting**: 60/min analytics, 5/min pipeline mutations
- **CORS**: Restricted origins and headers
- **Security headers**: X-Content-Type-Options, X-Frame-Options, Referrer-Policy
- **Docker**: Ports bound to `127.0.0.1`

## Authentication Validation

### Keycloak OIDC

| Check | How to Validate | Status |
|-------|----------------|--------|
| JWT signature validation | Send request with tampered JWT -- expect 401 | DONE |
| Expired token rejection | Send request with expired JWT -- expect 401 | DONE |
| Missing token rejection | Send request with no Authorization header -- expect 401 | DONE |
| Role-based access | `demo-viewer` cannot trigger pipeline -- expect 403 | DONE |
| Token refresh flow | Frontend refreshes token before expiry | DONE |

```bash
# Test: missing token
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/analytics/summary
# Expected: 401

# Test: invalid token
curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer invalid.token.here" \
  http://localhost:8000/api/v1/analytics/summary
# Expected: 401

# Test: valid token (obtain from Keycloak first)
TOKEN=$(curl -s -X POST http://localhost:8080/realms/datapulse/protocol/openid-connect/token \
  -d "client_id=datapulse-api" \
  -d "username=demo-admin" \
  -d "password=<password>" \
  -d "grant_type=password" | jq -r '.access_token')

curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/analytics/summary
# Expected: 200
```

### JWT Validation (`src/datapulse/api/jwt.py`)

- [x] Validates token signature against Keycloak public key
- [x] Checks `exp` (expiry) claim
- [x] Checks `iss` (issuer) claim matches Keycloak realm
- [x] Extracts `tenant_id` from custom claims
- [x] Extracts roles from `realm_access.roles`

## Row-Level Security (RLS)

### Tables with RLS

| Table | Policy | Status |
|-------|--------|--------|
| `bronze.sales` | `tenant_id = current_setting('app.tenant_id')` | DONE |
| `public_staging.stg_sales` | `security_invoker=on` (view) | DONE |
| `public_marts.dim_*` | RLS policy on tenant_id | DONE |
| `public_marts.fct_sales` | RLS policy on tenant_id | DONE |
| `public_marts.agg_*` | RLS policy on tenant_id | DONE |
| `public.pipeline_runs` | RLS policy on tenant_id | DONE |
| `public.quality_checks` | RLS policy on tenant_id | DONE |

### RLS Validation Commands

```sql
-- Connect as the app user (not superuser)
-- Verify RLS is enabled
SELECT tablename, rowsecurity
FROM pg_tables
WHERE schemaname IN ('bronze', 'public_staging', 'public_marts', 'public')
  AND rowsecurity = true;

-- Verify FORCE ROW LEVEL SECURITY
SELECT relname, relforcerowsecurity
FROM pg_class
WHERE relname IN ('sales', 'fct_sales', 'pipeline_runs', 'quality_checks');

-- Test tenant isolation: set tenant A, query, verify no tenant B data
SET LOCAL app.tenant_id = 'tenant-a-uuid';
SELECT COUNT(*) FROM bronze.sales;  -- Should return only tenant A rows

SET LOCAL app.tenant_id = 'tenant-b-uuid';
SELECT COUNT(*) FROM bronze.sales;  -- Should return only tenant B rows

-- Test: no tenant_id set -> zero rows (not an error)
RESET app.tenant_id;
SELECT COUNT(*) FROM bronze.sales;  -- Should return 0
```

### Owner Bypass Prevention

```sql
-- Verify FORCE ROW LEVEL SECURITY is set (prevents table owner from bypassing)
SELECT relname, relforcerowsecurity
FROM pg_class c
JOIN pg_namespace n ON c.relnamespace = n.oid
WHERE n.nspname = 'bronze' AND c.relname = 'sales';
-- relforcerowsecurity should be TRUE
```

## CORS Validation

### Allowed Configuration

```python
# src/datapulse/api/app.py
CORS_ORIGINS = ["http://localhost:3000"]
CORS_HEADERS = ["Content-Type", "Authorization", "X-API-Key", "X-Pipeline-Token"]
```

### Validation Commands

```bash
# Test: allowed origin
curl -s -o /dev/null -w "%{http_code}" \
  -H "Origin: http://localhost:3000" \
  -X OPTIONS \
  http://localhost:8000/api/v1/analytics/summary
# Expected: 200 with Access-Control-Allow-Origin header

# Test: disallowed origin
curl -s -D - \
  -H "Origin: http://evil.com" \
  -X OPTIONS \
  http://localhost:8000/api/v1/analytics/summary
# Expected: No Access-Control-Allow-Origin header in response

# Test: disallowed header
curl -s -D - \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Headers: X-Evil-Header" \
  -X OPTIONS \
  http://localhost:8000/api/v1/analytics/summary
# Expected: X-Evil-Header not in Access-Control-Allow-Headers
```

## Security Headers

### Expected Headers

| Header | Value | Purpose |
|--------|-------|---------|
| `X-Content-Type-Options` | `nosniff` | Prevent MIME sniffing |
| `X-Frame-Options` | `DENY` | Prevent clickjacking |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Limit referrer leakage |

```bash
# Verify headers
curl -s -D - http://localhost:8000/health | grep -E "X-Content-Type|X-Frame|Referrer"
```

## Rate Limiting

| Endpoint Group | Limit | Status |
|---------------|-------|--------|
| Analytics (`/api/v1/analytics/*`) | 60 requests/minute | DONE |
| Pipeline mutations (`POST /api/v1/pipeline/*`) | 5 requests/minute | DONE |
| Health (`/health`) | No limit | DONE |

### Validation

```bash
# Test rate limiting (send 61 requests rapidly)
for i in $(seq 1 61); do
  curl -s -o /dev/null -w "%{http_code}\n" \
    -H "Authorization: Bearer $TOKEN" \
    http://localhost:8000/api/v1/analytics/summary
done
# Expected: first 60 return 200, 61st returns 429
```

## SQL Injection Prevention

| Control | Location | Status |
|---------|----------|--------|
| Column whitelist before INSERT | `bronze/loader.py` | DONE |
| SQLAlchemy parameterised queries | `analytics/repository.py` | DONE |
| No raw SQL string concatenation | All modules | DONE |
| Pydantic validation on all inputs | `api/routes/*.py` | DONE |

## OWASP Top 10 Checklist

| # | Risk | Mitigation | Status |
|---|------|-----------|--------|
| A01 | Broken Access Control | Keycloak OIDC + RLS + role checks | DONE |
| A02 | Cryptographic Failures | TLS in production, NUMERIC for money | DONE |
| A03 | Injection | Parameterised queries, column whitelist | DONE |
| A04 | Insecure Design | Tenant isolation by design, RLS | DONE |
| A05 | Security Misconfiguration | CORS restricted, ports 127.0.0.1 only | DONE |
| A06 | Vulnerable Components | Pin dependency versions | DONE |
| A07 | Auth Failures | Keycloak, JWT validation, rate limiting | DONE |
| A08 | Data Integrity Failures | Quality gates, schema validation | DONE |
| A09 | Logging Failures | structlog JSON logging, error tracking | DONE |
| A10 | SSRF | No user-controlled URLs in backend | DONE |

## Docker Network Security

| Control | Status |
|---------|--------|
| All ports bound to `127.0.0.1` (not `0.0.0.0`) | DONE |
| Internal services (Redis) not exposed on host | DONE |
| Keycloak admin console on localhost only | DONE |
| `.env` file excluded from Docker image (`.dockerignore`) | DONE |

## Recommended Additions (TODO)

### Dependency Scanning

- [ ] Add `pip-audit` to CI for Python dependency CVE scanning
- [ ] Add `npm audit` to CI for frontend dependency scanning

```bash
pip install pip-audit
pip-audit

cd frontend && npm audit
```

### Secret Scanning

- [ ] Verify no secrets in git history: `git log --all -p | grep -i "password\|secret\|api_key"`
- [ ] Add pre-commit hook with `detect-secrets`

### Penetration Testing Checklist

- [ ] Test IDOR: can user A access user B's pipeline runs by UUID?
- [ ] Test privilege escalation: can `demo-viewer` call pipeline trigger?
- [ ] Test session fixation: does Keycloak rotate session on login?
- [ ] Test CSRF: are state-changing requests protected?

### Monitoring

- [ ] Alert on repeated 401/403 responses (brute force detection)
- [ ] Alert on rate limit hits (429 responses)
- [ ] Log and alert on RLS policy violations
