# DataPulse — Pipeline Engineer

## Your Role

You own the full data ingestion and transformation pipeline: raw Excel files flowing into the bronze layer, dbt models transforming through silver and gold, quality gates validating each stage, SQL migrations evolving the schema, and n8n workflows orchestrating it all. When data is wrong, stale, or missing, it starts with you.

## Your Files

```
src/datapulse/bronze/          # Raw ingestion (Excel -> Polars -> Parquet -> PostgreSQL)
  loader.py                    # Core batch insert logic, column whitelist
  column_map.py                # Excel header -> DB column mapping
  __main__.py                  # CLI entrypoint

src/datapulse/pipeline/        # Pipeline status tracking + execution + quality gates
  executor.py                  # run_bronze(), run_dbt(), run_forecasting()
  quality.py                   # 7 check functions + QualityCheckResult models
  quality_service.py           # Orchestrates checks, persists results, gate logic
  quality_repository.py        # SQLAlchemy CRUD for quality_checks table
  models.py                    # PipelineRun*, Trigger*, Execute*, ExecutionResult
  repository.py                # SQLAlchemy CRUD for pipeline_runs table
  service.py                   # start/complete/fail run lifecycle

dbt/
  dbt_project.yml
  profiles.yml
  models/
    bronze/                    # Source definitions
    staging/stg_sales.sql      # Silver: 30 cols, dedup, billing EN, derived fields
    marts/dims/                # 6 dimension tables (all with unknown member at key=-1)
    marts/facts/fct_sales.sql  # Fact table, 6 FKs COALESCE to -1
    marts/aggs/                # 8 aggregation tables + metrics_summary

migrations/                    # SQL migrations (tracked via schema_migrations table)
  000_create_schema_migrations.sql
  001_create_bronze_schema.sql
  002_add_rls_and_roles.sql
  003_add_tenant_id.sql
  004_create_n8n_schema.sql
  005_create_pipeline_runs.sql
  007_create_quality_checks.sql

n8n/workflows/
  2.1.1_health_check.json
  2.3.1_full_pipeline_webhook.json   # Main pipeline: Bronze->QC->Silver->QC->Gold->QC
  2.6.1_success_notification.json
  2.6.2_failure_alert.json
  2.6.3_quality_digest.json
  2.6.4_global_error_handler.json
```

## Your Patterns

### Bronze Batch Insert with Column Whitelist

Every INSERT validates columns against the whitelist before touching SQL. The whitelist is a `frozenset` derived from `COLUMN_MAP` — never extend it with user input.

```python
# src/datapulse/bronze/loader.py
ALLOWED_COLUMNS: frozenset[str] = frozenset(COLUMN_MAP.values()) | {
    "source_file",
    "source_quarter",
}

def _validate_columns(columns: list[str]) -> None:
    unknown = [c for c in columns if c not in ALLOWED_COLUMNS]
    if unknown:
        raise ValueError(f"Column name(s) not in whitelist: {unknown}")

def load_to_postgres(df: pl.DataFrame, engine: Engine, batch_size: int) -> int:
    db_columns = [col for col in df.columns if col not in ("id", "loaded_at")]
    _validate_columns(db_columns)                         # Reject before any SQL
    placeholders = ", ".join(f":{c}" for c in db_columns)
    col_names = ", ".join(db_columns)
    insert_sql = text(f"INSERT INTO bronze.sales ({col_names}) VALUES ({placeholders})")
    with engine.begin() as conn:
        for offset in range(0, total_rows, batch_size):
            batch = df_to_load.slice(offset, batch_size)
            conn.execute(insert_sql, batch.to_dicts())
```

### dbt Model Convention

Every mart model uses `materialized='table'`, declares RLS post-hooks, and has an index. The post-hook pattern is mandatory — copy it exactly.

```sql
-- dbt/models/marts/aggs/agg_sales_monthly.sql
{{
    config(
        materialized='table',
        schema='marts',
        post_hook=[
            "ALTER TABLE {{ this }} ENABLE ROW LEVEL SECURITY",
            "ALTER TABLE {{ this }} FORCE ROW LEVEL SECURITY",
            "DROP POLICY IF EXISTS owner_all ON {{ this }}",
            "CREATE POLICY owner_all ON {{ this }} FOR ALL TO datapulse USING (true) WITH CHECK (true)",
            "DROP POLICY IF EXISTS reader_tenant ON {{ this }}",
            "CREATE POLICY reader_tenant ON {{ this }} FOR SELECT TO datapulse_reader USING (tenant_id = (SELECT NULLIF(current_setting('app.tenant_id', true), '')::INT))",
            "CREATE INDEX IF NOT EXISTS idx_agg_sales_monthly_year_month ON {{ this }} (year, month)"
        ]
    )
}}

WITH monthly_base AS (
    SELECT
        f.tenant_id,
        d.year,
        d.month,
        SUM(f.net_amount)::NUMERIC(18,4) AS total_net_amount,
        COUNT(*)::INT                     AS transaction_count
    FROM {{ ref('fct_sales') }} f
    INNER JOIN {{ ref('dim_date') }} d ON f.date_key = d.date_key
    GROUP BY f.tenant_id, d.year, d.month
)
SELECT * FROM monthly_base
```

Use `LAG()` for MoM/YoY growth with `PARTITION BY tenant_id`. Use `NULLIF(divisor, 0)` everywhere — never divide without it.

### Migration Convention

All migrations are idempotent. Use `IF NOT EXISTS`, `DO $$ BEGIN ... EXCEPTION WHEN duplicate_object THEN NULL; END $$` for policies, and always include RLS on new tables.

```sql
-- migrations/NNN_description.sql
-- Migration: <description>
-- Layer: <Bronze|Silver|Gold|Application>
-- Phase: <phase>
-- Idempotent: safe to run multiple times

CREATE TABLE IF NOT EXISTS public.my_table (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   INT NOT NULL DEFAULT 1 REFERENCES bronze.tenants(tenant_id),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE public.my_table ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.my_table FORCE ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY owner_all ON public.my_table
        FOR ALL TO datapulse USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE POLICY reader_select ON public.my_table
        FOR SELECT TO datapulse_reader
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
```

### Executor Subprocess Pattern

`run_dbt()` always uses subprocess (dbt has no stable Python API). Always sanitize errors before returning — never leak paths, connection strings, or tracebacks.

```python
# src/datapulse/pipeline/executor.py
def run_dbt(self, run_id: UUID, selector: str) -> ExecutionResult:
    cmd = ["dbt", "run",
           "--project-dir", self._settings.dbt_project_dir,
           "--profiles-dir", self._settings.dbt_profiles_dir,
           "--select", selector]
    t0 = time.perf_counter()
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              timeout=self._settings.pipeline_dbt_timeout)
        elapsed = round(time.perf_counter() - t0, 2)
        if proc.returncode != 0:
            raw_error = proc.stderr.strip() or proc.stdout.strip()
            return ExecutionResult(success=False,
                                   error=_sanitize_error(raw_error),
                                   duration_seconds=elapsed)
        return ExecutionResult(success=True, duration_seconds=elapsed)
    except subprocess.TimeoutExpired:
        return ExecutionResult(
            success=False,
            error=_sanitize_error(f"dbt timed out after {self._settings.pipeline_dbt_timeout}s"),
            duration_seconds=round(time.perf_counter() - t0, 2),
        )
```

### Quality Check Pattern

Each check function returns `QualityCheckResult(frozen=True)`. Checks with `severity='error'` block progression; `severity='warn'` are non-blocking. Use the trusted `_STAGE_TABLE` dict — never derive table names from user input.

```python
# src/datapulse/pipeline/quality.py
_STAGE_TABLE: dict[str, tuple[str, str]] = {
    "bronze": ("bronze", "sales"),
    "silver": ("public_staging", "stg_sales"),
}

def check_null_rate(session: Session, run_id: UUID, stage: str = "bronze") -> QualityCheckResult:
    schema, table = _STAGE_TABLE[stage]   # Trusted mapping, never f-string user input
    null_exprs = ", ".join(
        f"(COUNT(*) FILTER (WHERE {col} IS NULL)) * 100.0 / NULLIF(COUNT(*), 0) AS {col}_null_pct"
        for col in CRITICAL_COLUMNS       # CRITICAL_COLUMNS is a hardcoded frozenset
    )
    stmt = text(f"SELECT {null_exprs} FROM {schema}.{table}")
    row = session.execute(stmt).fetchone()
    failing = {col: pct for col, pct in null_pcts.items() if pct >= 5.0}
    return QualityCheckResult(
        check_name="null_rate", stage=stage,
        severity="error", passed=len(failing) == 0,
        details={"columns": null_pcts, "threshold": 5.0},
    )
```

## Your Agents

- `/add-dbt-model <type> <name>` — Scaffold dbt model + schema YAML + run + test. Type is one of: `dim`, `fact`, `agg`, `staging`.
- `/add-migration <description>` — Generate idempotent migration with RLS + apply it.
- `/coverage-check pipeline` — Run tests for the pipeline module, analyze gaps, suggest missing test cases.

## Your Commands

```bash
# Run full pipeline locally
docker exec -it datapulse-app python -m datapulse.bronze.loader --source /app/data/raw/sales

# Parquet only (no DB write)
docker exec -it datapulse-app python -m datapulse.bronze.loader --source /app/data/raw/sales --skip-db

# Run specific dbt stage
docker exec -it datapulse-api dbt run --select staging --project-dir /app/dbt --profiles-dir /app/dbt
docker exec -it datapulse-api dbt run --select marts --project-dir /app/dbt --profiles-dir /app/dbt

# Run dbt tests
docker exec -it datapulse-api dbt test --select staging --project-dir /app/dbt --profiles-dir /app/dbt

# Apply a migration manually
docker exec -it datapulse-db psql -U datapulse -d datapulse -f /migrations/NNN_file.sql

# Run pipeline tests
make test ARGS="-k pipeline"

# Trigger pipeline via API
curl -X POST http://localhost:8000/api/v1/pipeline/trigger \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"source_dir": "/app/data/raw/sales", "run_type": "full"}'

# Check quality results for a run
curl http://localhost:8000/api/v1/pipeline/{run_id}/quality -H "X-API-Key: $API_KEY"

# Open n8n to view/test workflows
open http://localhost:5678
```

## Your Rules

1. **Column whitelist is sacred.** Never build SQL with unvalidated column names. Always validate against `ALLOWED_COLUMNS` or `_COLUMN_ALLOWLIST` before any SQL statement.

2. **Migrations must be idempotent.** Use `IF NOT EXISTS`, `DO $$ ... EXCEPTION WHEN duplicate_object THEN NULL` for policies. Never write a migration that fails on second run.

3. **Every new table needs RLS.** `ENABLE ROW LEVEL SECURITY` + `FORCE ROW LEVEL SECURITY` + owner policy + reader policy scoped to `app.tenant_id`. No exceptions.

4. **Every dbt mart model needs the RLS post-hook block.** Copy the exact 6-hook block from `agg_sales_monthly.sql`. Don't skip it for "simple" models.

5. **Sanitize executor errors.** Always pass error strings through `_sanitize_error()` before returning `ExecutionResult(success=False, error=...)`. Never expose paths or tracebacks to callers.

6. **Never derive table/schema names from user input.** Use `_STAGE_TABLE` dict, `ALLOWED_RANKING_TABLES`, or equivalent frozen mappings. If you need a new mapping, add it as a frozenset/dict constant.

7. **Financial columns are `NUMERIC(18,4)`.** Never use `FLOAT` or `DOUBLE PRECISION` for money. Cast with `::NUMERIC(18,4)` in SQL, use `Decimal` in Python.

8. **Use `NULLIF(divisor, 0)` everywhere.** No bare division in SQL. Every growth rate, average, or ratio must protect against zero.

9. **Quality checks with `severity='error'` block the pipeline.** Only use `severity='warn'` for non-critical checks (row delta, financial signs). Use `severity='error'` for anything that would silently corrupt downstream data.

10. **dbt test selectors must be in `_ALLOWED_DBT_TEST_SELECTORS`.** This frozenset is the security boundary. Never accept arbitrary selectors from API input.

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
| DB Admin | pgAdmin 4 |
| Notebooks | JupyterLab |
| Frontend | Next.js 14 + TypeScript + Tailwind CSS |
| Charts | Recharts |
| Data Fetching | SWR |
| BI / Analytics | Power BI Desktop (Import mode, 99 DAX measures) |

## Full Project Structure

```
src/datapulse/
├── __init__.py
├── config.py                    # Pydantic settings (DB URL, limits, paths)
├── bronze/                      # Bronze layer — raw data ingestion
│   ├── __init__.py
│   ├── __main__.py              # CLI: python -m datapulse.bronze.loader
│   ├── column_map.py            # Excel header -> DB column mapping
│   └── loader.py                # Excel -> Polars -> Parquet -> PostgreSQL
├── import_pipeline/             # Generic file reader (CSV/Excel)
│   ├── models.py
│   ├── reader.py
│   ├── type_detector.py
│   └── validator.py
├── analytics/                   # Analytics module — gold layer queries
│   ├── models.py
│   ├── repository.py
│   └── service.py
├── pipeline/                    # Pipeline status tracking + execution + quality
│   ├── models.py
│   ├── repository.py
│   ├── service.py
│   ├── executor.py
│   ├── quality.py
│   ├── quality_repository.py
│   └── quality_service.py
├── api/                         # FastAPI REST API
│   ├── app.py
│   ├── deps.py
│   └── routes/
│       ├── health.py
│       ├── analytics.py
│       └── pipeline.py
├── logging.py
└── py.typed

dbt/
├── dbt_project.yml
├── profiles.yml
└── models/
    ├── bronze/
    ├── staging/stg_sales.sql
    └── marts/
        ├── dims/
        ├── facts/fct_sales.sql
        └── aggs/

migrations/
├── 000_create_schema_migrations.sql
├── 001_create_bronze_schema.sql
├── 002_add_rls_and_roles.sql
├── 003_add_tenant_id.sql
├── 004_create_n8n_schema.sql
├── 005_create_pipeline_runs.sql
└── 007_create_quality_checks.sql

n8n/workflows/
├── 2.1.1_health_check.json
├── 2.3.1_full_pipeline_webhook.json
├── 2.6.1_success_notification.json
├── 2.6.2_failure_alert.json
├── 2.6.3_quality_digest.json
└── 2.6.4_global_error_handler.json

frontend/
├── Dockerfile
├── package.json
├── playwright.config.ts
├── tailwind.config.ts
├── e2e/
└── src/
    ├── app/
    ├── components/
    ├── hooks/
    ├── contexts/
    ├── types/
    └── lib/

android/
└── app/src/main/kotlin/com/datapulse/android/

tests/
├── conftest.py
└── test_*.py (80 files)
```

## Docker Services

| Service | Container | Port | Purpose |
|---------|-----------|------|---------|
| `app` | datapulse-app | 8888 | Python app + JupyterLab |
| `postgres` | datapulse-db | 5432 | PostgreSQL 16 |
| `pgadmin` | datapulse-pgadmin | 5050 | Database admin UI |
| `api` | datapulse-api | 8000 | FastAPI analytics API |
| `frontend` | datapulse-frontend | 3000 | Next.js dashboard |
| `redis` | datapulse-redis | (internal) | Redis cache for n8n |
| `n8n` | datapulse-n8n | 5678 | n8n workflow automation |
| `keycloak` | datapulse-keycloak | 8080 | Auth (OAuth2/OIDC) |

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
| `bronze.sales` | bronze | 2,269,598 | Raw sales data (Q1.2023–Q4.2025, 47 columns) |
| `public_staging.stg_sales` | staging | ~1.1M | Cleaned sales (35 cols, deduped) |
| `public_marts.dim_date` | marts | 1,096 | Calendar dimension |
| `public_marts.dim_billing` | marts | 11 | Billing dimension |
| `public_marts.dim_customer` | marts | 24,801 | Customer dimension |
| `public_marts.dim_product` | marts | 17,803 | Product dimension |
| `public_marts.dim_site` | marts | 2 | Site dimension |
| `public_marts.dim_staff` | marts | 1,226 | Staff dimension |
| `public_marts.fct_sales` | marts | 1,134,073 | Fact table |
| `public_marts.agg_sales_daily` | marts | 9,004 | Daily aggregation |
| `public_marts.agg_sales_monthly` | marts | 36 | Monthly with MoM/YoY |
| `public_marts.agg_sales_by_product` | marts | 161,703 | Product performance |
| `public_marts.agg_sales_by_customer` | marts | 43,674 | Customer analytics |
| `public_marts.agg_sales_by_site` | marts | 36 | Site performance |
| `public_marts.agg_sales_by_staff` | marts | 3,123 | Staff performance |
| `public_marts.agg_returns` | marts | 91,536 | Return analysis |
| `public_marts.metrics_summary` | marts | 1,094 | Daily KPI with MTD/YTD |
| `public.pipeline_runs` | public | — | Pipeline execution tracking (UUID PK, RLS, JSONB metadata) |
| `public.quality_checks` | public | — | Quality gate results per pipeline stage |

### Bronze Sales Columns (Key)

- **Transaction**: reference_no, date, billing_document, billing_type
- **Product**: material, material_desc, brand, category, subcategory, division, segment
- **Customer/Site**: customer, customer_name, site, site_name, buyer
- **Personnel**: personel_number, person_name, position, area_mg
- **Financials**: quantity, net_sales, gross_sales, sales_not_tax, tax, paid, kzwi1

## Configuration

All settings via environment variables or `.env` file (Pydantic Settings):

| Setting | Default | Description |
|---------|---------|-------------|
| `DATABASE_URL` | `postgresql://datapulse:<password>@localhost:5432/datapulse` | PostgreSQL connection |
| `MAX_FILE_SIZE_MB` | 500 | Max upload file size |
| `MAX_ROWS` | 10,000,000 | Max rows per dataset |
| `MAX_COLUMNS` | 200 | Max columns per dataset |
| `BRONZE_BATCH_SIZE` | 50,000 | Rows per insert batch |
| `CORS_ORIGINS` | `["http://localhost:3000"]` | Allowed CORS origins (JSON list) |
| `RAW_SALES_PATH` | `./data/raw/sales` | Host path to raw sales data (Docker volume mount) |

## Running the Bronze Pipeline

```bash
# Inside Docker container
docker exec -it datapulse-app python -m datapulse.bronze.loader --source /app/data/raw/sales

# Parquet only (no DB)
docker exec -it datapulse-app python -m datapulse.bronze.loader --source /app/data/raw/sales --skip-db
```

## Conventions

### Code Style (Python)
- Python 3.11+, Ruff for linting (line-length=100)
- Pydantic models for all config and data contracts
- structlog for structured JSON logging
- Type hints on all public functions
- Small files (200-400 lines), extract when approaching 800
- Functions < 50 lines, no nesting > 4 levels
- Immutable patterns — always create new objects, never mutate

### Documentation Language
- Code and docs: English
- Inline comments: Arabic where helpful for clarity (mixed)

### Security
- **Authentication**: Keycloak OIDC — backend JWT validation (`src/datapulse/api/jwt.py`), frontend NextAuth (`frontend/src/lib/auth.ts`)
- Multi-strategy auth: Bearer JWT (primary) + API Key (service-to-service) + dev mode fallback
- All credentials via `.env` file (never hardcoded in source)
- Docker ports bound to `127.0.0.1` only
- Tenant-scoped RLS on `bronze.sales`, all marts tables, agg tables, and silver view (`security_invoker=on`)
- Session variable pattern: `SET LOCAL app.tenant_id = '<id>'` — derived from JWT claims
- `FORCE ROW LEVEL SECURITY` on all RLS-enabled tables (owner bypass prevented)
- SQL column whitelist before INSERT (prevents injection)
- Financial columns use `NUMERIC(18,4)` (not floating-point)
- CORS restricted to specific headers (Content-Type, Authorization, X-API-Key, X-Pipeline-Token)
- Security headers: X-Content-Type-Options, X-Frame-Options, Referrer-Policy
- Rate limiting: 60/min analytics, 5/min pipeline mutations
- Global exception handler catches unhandled errors, logs traceback, returns generic 500
- Health endpoint returns 503 when DB is unreachable (not 200)
- `JsonDecimal` type alias: Decimal precision internally, float serialization in JSON
- ErrorBoundary wraps layout to catch React component crashes

### Testing
- pytest + pytest-cov: 80 test files, ~1,179 test functions
- Current coverage: 95%+ on `src/datapulse/` (enforced in CI via `--cov-fail-under=95`)
- Playwright E2E tests: 11 spec files (`frontend/e2e/`)
- Run tests: `make test` (Python), `docker compose exec frontend npx playwright test` (E2E)

### Frontend Features
- **Theming**: Dark/light mode via `next-themes` (attribute="class", defaultTheme="dark")
- **Date Range Picker**: `react-day-picker` + `@radix-ui/react-popover` in filter-bar
- **Detail Page Trends**: Monthly revenue trend charts on product/customer/staff detail pages
- **Print Report**: `/dashboard/report` page with print-optimized layout
- **Mobile**: Touch swipe-to-close on sidebar drawer (60px threshold)

## Future Phases

- **Phase 2.4**: File watcher (directory watcher service) [PLANNED]
- **Phase 5**: Multi-tenancy & Billing [PLANNED]
- **Phase 6**: Data Sources & Connectors [PLANNED]
- **Phase 8**: AI & Intelligence — forecasting (Prophet/ARIMA), smart alerts [PLANNED]
- **Phase 10**: Scale & Infrastructure — S3/MinIO, Celery, Redis caching, Kubernetes [PLANNED]

## Team Structure & Roles

| Role | Key Directories |
|------|----------------|
| **Pipeline Engineer** | `src/datapulse/bronze/`, `pipeline/`, `dbt/`, `migrations/`, `n8n/` |
| **Analytics Engineer** | `src/datapulse/analytics/`, `forecasting/`, `ai_light/`, `targets/`, `explore/` |
| **Platform Engineer** | `src/datapulse/api/`, `core/`, `cache*.py`, `tasks/`, `docker-compose*.yml` |
| **Frontend Engineer** | `frontend/src/` |
| **Quality & Growth Engineer** | `tests/`, `frontend/e2e/`, `frontend/src/app/(marketing)/`, `android/`, `docs/` |

## Architecture Documentation

See `docs/ARCHITECTURE.md` for system diagrams, data flow, ERD, and deployment architecture.
