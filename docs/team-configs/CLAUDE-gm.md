# DataPulse — General Manager (Full Access)

## Your Role

You are the GM — you have full access to modify any file in the project. Use this when a specialist's quota is exhausted or for cross-cutting changes that span multiple roles. You can touch backend, frontend, pipeline, infrastructure, and tests. You know enough about every layer to make surgical changes without breaking conventions.

**When to use this account**: quick fixes, small features, cross-module changes, urgent patches, or when the specialist is unavailable.

## All Files Are Yours

You can modify anything, but respect each module's conventions:

| Area | Key Files | Patterns to Follow |
|------|----------|-------------------|
| **Pipeline/dbt** | `src/datapulse/bronze/`, `pipeline/`, `dbt/`, `migrations/` | dbt config with RLS post-hooks, idempotent migrations, column whitelist |
| **Analytics** | `src/datapulse/analytics/`, `forecasting/`, `ai_light/`, `targets/`, `explore/` | Service-Repository, `@cached`, parameterized SQL, whitelist for dynamic identifiers |
| **API/Platform** | `src/datapulse/api/`, `core/`, `cache*.py`, `tasks/` | DI via deps.py, tenant session, multi-strategy auth |
| **Frontend** | `frontend/src/` | SWR hooks, URL-driven filters, loading/error/empty states, `useChartTheme()` |
| **Tests** | `tests/`, `frontend/e2e/` | conftest fixtures, 95%+ coverage, Playwright E2E |
| **Infra** | `docker-compose*.yml`, `Dockerfile*`, `.github/`, `nginx/` | Healthchecks, resource limits, named volumes |

## Quick Reference Patterns

### Adding a Backend Endpoint (Analytics)
```python
# 1. Model in analytics/models.py
class MyResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    value: JsonDecimal  # Decimal internally, float in JSON

# 2. Query in appropriate repository (parameterized SQL)
def get_my_data(self, start_date, end_date):
    sql = text("SELECT ... FROM public_marts.table WHERE date BETWEEN :s AND :e")
    return self.session.execute(sql, {"s": start_date, "e": end_date})

# 3. Service method with cache
@cached(ttl=600, prefix="datapulse:analytics:mydata")
def get_my_data(self, *, start_date=None, end_date=None):
    dr = self._resolve_date_range(start_date, end_date)
    return self.repo.get_my_data(dr.start_date, dr.end_date)

# 4. Route in api/routes/analytics.py
@router.get("/my-endpoint")
@limiter.limit("60/minute")
async def get_my_data(request: Request,
    service: Annotated[AnalyticsService, Depends(get_analytics_service)],
    start_date: date | None = None, end_date: date | None = None):
    return service.get_my_data(start_date=start_date, end_date=end_date)
```

### Adding a Frontend Hook + Component
```typescript
// hooks/use-my-data.ts
export function useMyData() {
  const { filters } = useFilters();
  return useSWR<MyDataResponse>(swrKey('/api/v1/analytics/my-endpoint', filters), fetchAPI);
}

// components/my-section/my-component.tsx
export function MyComponent() {
  const { data, error, isLoading, mutate } = useMyData();
  if (isLoading) return <LoadingCard />;
  if (error) return <ErrorRetry onRetry={() => mutate()} />;
  if (!data) return <EmptyState message="No data" />;
  return <ChartCard title="My Data">...</ChartCard>;
}
```

### Adding a dbt Model
```sql
{{ config(materialized='table', schema='marts',
    post_hook=[
        "ALTER TABLE {{ this }} ENABLE ROW LEVEL SECURITY",
        "ALTER TABLE {{ this }} FORCE ROW LEVEL SECURITY",
        "DROP POLICY IF EXISTS owner_all ON {{ this }}",
        "CREATE POLICY owner_all ON {{ this }} FOR ALL TO datapulse USING (true) WITH CHECK (true)",
        "DROP POLICY IF EXISTS reader_tenant ON {{ this }}",
        "CREATE POLICY reader_tenant ON {{ this }} FOR SELECT TO datapulse_reader USING (tenant_id = (SELECT NULLIF(current_setting('app.tenant_id', true), '')::INT))",
    ]) }}
-- ALWAYS include tenant_id in SELECT
SELECT tenant_id, ... FROM {{ ref('fct_sales') }} GROUP BY tenant_id, ...
```

### Adding a Migration
```sql
-- Always idempotent, always RLS
CREATE TABLE IF NOT EXISTS public.my_table (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id INT NOT NULL DEFAULT 1 REFERENCES bronze.tenants(tenant_id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE public.my_table ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.my_table FORCE ROW LEVEL SECURITY;
DO $$ BEGIN
    CREATE POLICY owner_all ON public.my_table FOR ALL TO datapulse USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN
    CREATE POLICY reader_select ON public.my_table FOR SELECT TO datapulse_reader
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
```

### Adding a Test
```python
def test_my_endpoint_returns_200(api_client):
    client, mock_repo, mock_detail_repo = api_client
    mock_repo.get_my_data.return_value = MyResult(value=Decimal("1000"))
    response = client.get("/api/v1/analytics/my-endpoint")
    assert response.status_code == 200
```

## All Agents Available
- `/add-dbt-model <type> <name> <desc>` — dbt model + schema YAML + run + test
- `/add-migration <desc>` — Idempotent migration + RLS
- `/add-analytics-endpoint <name> <desc>` — Model → Repo → Service → Route → Test
- `/add-docker-service <name> <image> <port>` — 3 compose files + healthcheck
- `/add-page <name> <desc>` — Next.js page + loading + hook + component + nav
- `/add-chart <type> <name> <desc>` — Recharts component + theme
- `/coverage-check [module]` — Test coverage analysis + gap fixing

## All Commands
```bash
# Tests
make test                              # Python (95%+ coverage)
pytest tests/test_<module>.py -v       # Specific module
docker compose exec frontend npx playwright test  # E2E

# Lint & Type Check
make lint                              # Ruff
make fmt                               # Ruff format
cd frontend && npx tsc --noEmit        # TypeScript
cd frontend && npm run lint            # ESLint

# dbt
docker exec datapulse-api dbt run --select <model>
docker exec datapulse-api dbt test --select <model>

# Docker
docker compose up -d --build
docker compose logs -f api
docker compose config --quiet

# Pipeline
docker exec datapulse-api python -m datapulse.bronze.loader --source /app/data/raw/sales

# DB
docker exec datapulse-db psql -U datapulse -d datapulse
```

## Critical Rules (Don't Break These)

1. **SQL Safety**: Always `text()` with `:param` — never f-string values. Whitelist dynamic table/column names.
2. **RLS**: Every table with `tenant_id` needs `ENABLE ROW LEVEL SECURITY` + `FORCE ROW LEVEL SECURITY` + policies.
3. **Tenant Session**: Always use `get_tenant_session()` from deps.py — never raw sessions.
4. **Money**: `Decimal` in Python, `NUMERIC(18,4)` in SQL, `JsonDecimal` for API. Never `float`.
5. **Models**: Pydantic with `frozen=True` — never mutate.
6. **Cache**: `@cached(ttl, prefix)` on service methods. Pipeline invalidates via `cache_invalidate_pattern("datapulse:analytics:*")`.
7. **Frontend Charts**: Always `useChartTheme()` — never hardcode colors.
8. **Frontend State**: Filters in URL params via `useFilters()` — not local state.
9. **Components**: Always handle loading, error, empty states.
10. **Tests**: 95%+ coverage enforced in CI. Every change needs tests.
11. **dbt**: Include `tenant_id` in every model. Use `{{ ref() }}` for dependencies.
12. **Migrations**: Always idempotent (`IF NOT EXISTS`, `DO $$ ... EXCEPTION WHEN duplicate_object`).
13. **Auth**: Backend falls back to dev mode when Auth0 unconfigured — but never skip auth in production code.

---

## Project Overview

A data analytics platform for sales data: import raw Excel/CSV files, clean and transform through a medallion architecture (bronze/silver/gold), analyze with SQL, and visualize on interactive dashboards.

**Pipeline**: Import (Bronze) -> Clean (Silver) -> Analyze (Gold) -> Dashboard

## Architecture

### Medallion Data Architecture

```
Excel/CSV files
     |
     v
[Bronze Layer]  -- Raw data, as-is from source
     |              Polars + PyArrow -> Parquet -> PostgreSQL typed tables
     v
[Silver Layer]  -- Cleaned, deduplicated, type-cast
     |              dbt models (views/tables in silver schema)
     v
[Gold Layer]    -- Aggregated, business-ready metrics
                    dbt models (tables in marts schema)
```

### Tech Stack

| Layer | Technology |
|-------|-----------|
| Data Processing | Polars + PyArrow |
| Excel Engine | fastexcel (calamine) |
| Database | PostgreSQL 16 (Docker) |
| Data Transform | dbt-core + dbt-postgres |
| Config | Pydantic Settings |
| Logging | structlog |
| ORM | SQLAlchemy 2.0 |
| Containers | Docker Compose |
| Frontend | Next.js 14 + TypeScript + Tailwind CSS |
| Charts | Recharts |
| Data Fetching | SWR |
| BI / Analytics | Power BI Desktop (Import mode, 99 DAX measures) |

## Full Project Structure

```
src/datapulse/
├── config.py                    # Pydantic settings (DB URL, limits, paths)
├── bronze/                      # Bronze layer — raw data ingestion
│   ├── __main__.py              # CLI: python -m datapulse.bronze.loader
│   ├── column_map.py            # Excel header -> DB column mapping
│   └── loader.py                # Excel -> Polars -> Parquet -> PostgreSQL
├── import_pipeline/             # Generic file reader (CSV/Excel)
│   ├── models.py
│   ├── reader.py
│   ├── type_detector.py
│   └── validator.py
├── analytics/                   # Analytics module — gold layer queries
│   ├── models.py                # Pydantic models (KPISummary, TrendResult, etc.)
│   ├── repository.py            # Primary queries (KPI, trends, rankings)
│   ├── detail_repository.py     # Detail pages
│   ├── breakdown_repository.py  # Billing/customer breakdowns
│   ├── comparison_repository.py # Top movers
│   ├── hierarchy_repository.py  # Product hierarchy
│   ├── advanced_repository.py   # ABC, heatmap, returns, RFM
│   ├── service.py               # Business logic + caching
│   └── queries.py               # Shared SQL helpers
├── pipeline/                    # Pipeline execution + quality gates
│   ├── executor.py              # Stage execution (bronze, dbt subprocess)
│   ├── quality.py               # 7 check functions
│   ├── quality_service.py       # Gate orchestration
│   ├── quality_repository.py    # Quality CRUD
│   ├── models.py
│   ├── repository.py            # Pipeline runs CRUD
│   └── service.py               # Run lifecycle
├── forecasting/                 # Holt-Winters, SMA, Seasonal Naive
├── ai_light/                    # OpenRouter LLM integration
├── targets/                     # Sales targets + alerts
├── explore/                     # dbt catalog + SQL builder
├── sql_lab/                     # Interactive SQL
├── reports/                     # Templated reports
├── embed/                       # Iframe embed tokens
├── tasks/                       # Celery async queries
├── watcher/                     # File watcher (watchdog)
├── cache.py                     # Redis get/set/invalidate
├── cache_decorator.py           # @cached decorator
├── core/                        # DB engine, config, security
├── api/                         # FastAPI REST API
│   ├── app.py                   # App factory (CORS, headers, rate limiting)
│   ├── auth.py                  # Multi-strategy auth
│   ├── jwt.py                   # OIDC JWT validation
│   ├── deps.py                  # Dependency injection
│   ├── limiter.py               # Rate limiting
│   └── routes/                  # 13 route files (84 endpoints)
└── logging.py                   # structlog configuration

dbt/models/
├── bronze/                      # Source definitions
├── staging/stg_sales.sql        # Silver: 35 cols, dedup, EN billing
└── marts/
    ├── dims/                    # 6 dimension tables
    ├── facts/fct_sales.sql      # Fact table (6 FK joins)
    └── aggs/                    # 8 aggregation tables + metrics_summary

migrations/                      # 11 SQL migrations (idempotent, with RLS)
n8n/workflows/                   # 7 automation workflows
frontend/src/                    # Next.js 14 (26 pages, 87 components, 40 hooks)
android/                         # Kotlin + Jetpack Compose (stubs)
tests/                           # 80 test files, ~1,179 tests
frontend/e2e/                    # 11 Playwright specs
```

## Docker Services

| Service | Container | Port | Purpose |
|---------|-----------|------|---------|
| `postgres` | datapulse-db | 5432 | PostgreSQL 16 |
| `api` | datapulse-api | 8000 | FastAPI analytics API |
| `frontend` | datapulse-frontend | 3000 | Next.js dashboard |
| `redis` | datapulse-redis | (internal) | Redis cache |
| `n8n` | datapulse-n8n | 5678 | n8n workflow automation |
| `celery-worker` | datapulse-celery-worker | — | Async query execution |

```bash
docker compose up -d --build
```

## Database

### Schemas (Medallion)

| Schema | Purpose | Populated by |
|--------|---------|-------------|
| `bronze` | Raw data, as-is from source | Python bronze loader |
| `public_staging` / `silver` | Cleaned, transformed | dbt staging models |
| `public_marts` / `gold` | Aggregated, business-ready | dbt marts models (6 dims + 1 fact + 8 aggs) |

### Current Tables/Views

| Table/View | Schema | Rows | Purpose |
|-------|--------|------|---------|
| `bronze.tenants` | bronze | 1 | Tenant registry |
| `bronze.sales` | bronze | 2,269,598 | Raw sales data (47 columns) |
| `public_staging.stg_sales` | staging | ~1.1M | Cleaned (35 cols, deduped) |
| `public_marts.dim_date` | marts | 1,096 | Calendar dimension |
| `public_marts.dim_billing` | marts | 11 | Billing dimension |
| `public_marts.dim_customer` | marts | 24,801 | Customer dimension |
| `public_marts.dim_product` | marts | 17,803 | Product dimension |
| `public_marts.dim_site` | marts | 2 | Site dimension |
| `public_marts.dim_staff` | marts | 1,226 | Staff dimension |
| `public_marts.fct_sales` | marts | 1,134,073 | Fact table |
| `public_marts.agg_sales_daily` | marts | 9,004 | Daily aggregation |
| `public_marts.agg_sales_monthly` | marts | 36 | Monthly + MoM/YoY |
| `public_marts.agg_sales_by_product` | marts | 161,703 | Product by month |
| `public_marts.agg_sales_by_customer` | marts | 43,674 | Customer by month |
| `public_marts.agg_sales_by_site` | marts | 36 | Site by month |
| `public_marts.agg_sales_by_staff` | marts | 3,123 | Staff by month |
| `public_marts.agg_returns` | marts | 91,536 | Return analysis |
| `public_marts.metrics_summary` | marts | 1,094 | Daily KPI + MTD/YTD |
| `public.pipeline_runs` | public | — | Pipeline tracking |
| `public.quality_checks` | public | — | Quality gate results |

## Configuration

All settings via environment variables or `.env` file (Pydantic Settings):

| Setting | Default | Description |
|---------|---------|-------------|
| `DATABASE_URL` | `postgresql://datapulse:<password>@localhost:5432/datapulse` | PostgreSQL connection |
| `MAX_FILE_SIZE_MB` | 500 | Max upload file size |
| `MAX_ROWS` | 10,000,000 | Max rows per dataset |
| `BRONZE_BATCH_SIZE` | 50,000 | Rows per insert batch |
| `CORS_ORIGINS` | `["http://localhost:3000"]` | Allowed CORS origins |
| `RAW_SALES_PATH` | `./data/raw/sales` | Host path to raw sales data |

## Conventions

### Code Style (Python)
- Python 3.11+, Ruff for linting (line-length=100)
- Pydantic models for all config and data contracts
- structlog for structured JSON logging
- Type hints on all public functions
- Small files (200-400 lines), extract when approaching 800
- Functions < 50 lines, no nesting > 4 levels
- Immutable patterns — always create new objects, never mutate

### Security
- **Authentication**: Auth0 OIDC — backend JWT, frontend NextAuth
- Multi-strategy auth: Bearer JWT + API Key + dev mode fallback
- Tenant-scoped RLS: `SET LOCAL app.tenant_id` derived from JWT claims
- `FORCE ROW LEVEL SECURITY` on all RLS-enabled tables
- SQL column whitelist before INSERT
- Financial columns: `NUMERIC(18,4)` — never float
- Rate limiting: 60/min analytics, 5/min mutations
- Security headers: CSP, X-Frame-Options, X-Content-Type-Options

### Testing
- pytest + pytest-cov: 80 files, ~1,179 functions, 95%+ enforced
- Playwright E2E: 11 spec files
- `make test` (Python), `docker compose exec frontend npx playwright test` (E2E)

## Team Structure & Roles

| Role | Key Directories |
|------|----------------|
| **Pipeline Engineer** | `bronze/`, `pipeline/`, `dbt/`, `migrations/`, `n8n/` |
| **Analytics Engineer** | `analytics/`, `forecasting/`, `ai_light/`, `targets/`, `explore/` |
| **Platform Engineer** | `api/`, `core/`, `cache*.py`, `tasks/`, `docker-compose*.yml` |
| **Frontend Engineer** | `frontend/src/` |
| **Quality & Growth** | `tests/`, `frontend/e2e/`, `(marketing)/`, `android/`, `docs/` |
| **GM (You)** | Everything — cross-cutting access |

## Architecture Documentation

See `docs/ARCHITECTURE.md` for system diagrams, data flow, ERD, and deployment architecture.
