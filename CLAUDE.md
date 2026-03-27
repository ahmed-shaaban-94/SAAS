# DataPulse — Business/Sales Analytics SaaS

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

## Project Structure

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
│   ├── __init__.py
│   ├── models.py                # Pydantic models (ImportConfig, ImportResult, ColumnInfo)
│   ├── reader.py                # read_csv(), read_excel(), read_file()
│   ├── type_detector.py         # Auto-detect column types from DataFrame
│   └── validator.py             # File validation (size, format)
├── analytics/                   # Analytics module — gold layer queries
│   ├── __init__.py
│   ├── models.py                # Pydantic models (KPISummary, TrendResult, RankingResult, etc.)
│   ├── repository.py            # SQLAlchemy read-only queries against marts schema
│   └── service.py               # Business logic layer with default filters
├── api/                         # FastAPI REST API
│   ├── __init__.py
│   ├── app.py                   # App factory (CORS, logging, routers)
│   ├── deps.py                  # Dependency injection (sessions, services)
│   └── routes/
│       ├── __init__.py
│       ├── health.py            # GET /health
│       └── analytics.py         # 10 analytics endpoints under /api/v1/analytics/
└── utils/
    ├── __init__.py
    └── logging.py               # structlog configuration

dbt/
├── dbt_project.yml
├── profiles.yml
└── models/
    ├── bronze/                  # Source definitions + base models
    │   ├── _bronze__sources.yml
    │   └── bronze_sales.sql
    ├── staging/                 # Silver layer (cleaning + renaming)
    │   ├── _staging__sources.yml
    │   └── stg_sales.sql        # Cleaned: 30 cols, dedup, billing EN, derived fields
    └── marts/                   # Gold layer (dimension + fact tables)
        ├── _marts__models.yml   # Schema, docs, 57 dbt tests
        ├── dim_date.sql         # Calendar dimension (2023-2025, week/quarter columns)
        ├── dim_billing.sql      # Billing dimension (10 types, 5 groups)
        ├── dim_customer.sql     # Customer dimension (unknown member at key=-1)
        ├── dim_product.sql      # Product/drug dimension (unknown member at key=-1)
        ├── dim_site.sql         # Site/location dimension (unknown member at key=-1)
        ├── dim_staff.sql        # Staff/personnel dimension (unknown member at key=-1)
        └── fct_sales.sql        # Sales fact table (6 FK joins, COALESCE to -1)

migrations/                      # SQL migrations (tracked via schema_migrations)
├── 000_create_schema_migrations.sql  # Migration tracking bootstrap
├── 001_create_bronze_schema.sql      # Bronze schema + tables
├── 002_add_rls_and_roles.sql         # RLS + read-only role
└── 003_add_tenant_id.sql            # Tenant-scoped RLS (tenant_id col, bronze.tenants table)

frontend/                            # Next.js 14 dashboard (Phase 1.5)
├── Dockerfile                       # node:20-alpine dev container
├── package.json                     # Next.js 14, SWR, Recharts, Tailwind, date-fns
├── tailwind.config.ts               # midnight-pharma color tokens
├── src/
│   ├── app/
│   │   ├── layout.tsx               # Root layout: sidebar + providers
│   │   ├── page.tsx                 # Redirect to /dashboard
│   │   └── dashboard/
│   │       ├── page.tsx             # Executive overview: KPI grid + trend charts
│   │       └── loading.tsx          # Skeleton loading state
│   ├── components/
│   │   ├── layout/sidebar.tsx       # Nav sidebar (6 pages)
│   │   ├── layout/header.tsx        # Page header
│   │   ├── dashboard/kpi-card.tsx   # KPI card with trend indicator
│   │   ├── dashboard/kpi-grid.tsx   # 7 KPI cards grid
│   │   ├── dashboard/daily-trend-chart.tsx   # Recharts area chart
│   │   ├── dashboard/monthly-trend-chart.tsx # Recharts bar chart
│   │   ├── filters/filter-bar.tsx   # Date preset filter bar
│   │   ├── shared/ranking-table.tsx # Generic ranking table
│   │   ├── shared/ranking-chart.tsx # Horizontal bar chart
│   │   ├── shared/summary-stats.tsx # Stat cards grid
│   │   ├── shared/progress-bar.tsx  # Progress bar
│   │   ├── providers.tsx            # SWR + Filter context wrapper
│   │   ├── error-boundary.tsx       # React error boundary
│   │   ├── empty-state.tsx          # Empty data placeholder
│   │   └── loading-card.tsx         # Skeleton loading card
│   ├── hooks/                       # 9 SWR hooks (1 per API endpoint)
│   │   ├── use-summary.ts           # GET /api/v1/analytics/summary
│   │   ├── use-daily-trend.ts       # GET /api/v1/analytics/trends/daily
│   │   ├── use-monthly-trend.ts     # GET /api/v1/analytics/trends/monthly
│   │   ├── use-top-products.ts      # GET /api/v1/analytics/products/top
│   │   ├── use-top-customers.ts     # GET /api/v1/analytics/customers/top
│   │   ├── use-top-staff.ts         # GET /api/v1/analytics/staff/top
│   │   ├── use-sites.ts             # GET /api/v1/analytics/sites
│   │   ├── use-returns.ts           # GET /api/v1/analytics/returns
│   │   └── use-health.ts            # GET /health
│   ├── contexts/filter-context.tsx  # Global filters synced to URL params
│   ├── types/api.ts                 # TS interfaces matching Pydantic models
│   ├── types/filters.ts             # FilterParams interface
│   └── lib/
│       ├── api-client.ts            # fetchAPI<T> with Decimal parsing
│       ├── swr-config.ts            # SWR global config
│       ├── formatters.ts            # Currency (EGP), percent, compact
│       ├── date-utils.ts            # parseDateKey, date presets
│       ├── constants.ts             # Chart colors, nav items, API URL
│       └── utils.ts                 # cn() helper

tests/
├── conftest.py
├── test_reader.py
├── test_type_detector.py
├── test_config.py
├── test_validator.py
├── test_loader.py
└── test_coverage_gaps.py
```

## Docker Services

| Service | Container | Port | Purpose |
|---------|-----------|------|---------|
| `app` | datapulse-app | 8888 | Python app + JupyterLab |
| `postgres` | datapulse-db | 5432 | PostgreSQL 16 |
| `pgadmin` | datapulse-pgadmin | 5050 | Database admin UI |
| `api` | datapulse-api | 8000 | FastAPI analytics API |
| `frontend` | datapulse-frontend | 3000 | Next.js dashboard |

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
| `bronze.tenants` | bronze | 1 | Tenant registry (tenant_id, tenant_name) |
| `bronze.sales` | bronze | 2,269,598 | Raw sales data (Q1.2023–Q4.2025, 47 columns incl. tenant_id) |
| `public_staging.stg_sales` | staging | ~1.1M (deduped) | Cleaned sales (35 cols, EN billing, normalized status, flags, 7 dbt tests) |
| `public_marts.dim_date` | marts | 1,096 | Calendar dimension (2023-2025, week/quarter columns) |
| `public_marts.dim_billing` | marts | 11 | Billing dimension (10 types + Unknown, 5 groups) |
| `public_marts.dim_customer` | marts | 24,801 | Customer dimension (name, unknown member at -1) |
| `public_marts.dim_product` | marts | 17,803 | Product dimension (drug_code, brand, category, unknown at -1) |
| `public_marts.dim_site` | marts | 2 | Site dimension (name, area_manager, unknown at -1) |
| `public_marts.dim_staff` | marts | 1,226 | Staff dimension (name, position, unknown at -1) |
| `public_marts.fct_sales` | marts | 1,134,073 | Fact table (6 FKs COALESCE to -1, 4 financial measures) |
| `public_marts.agg_sales_daily` | marts | 9,004 | Daily sales aggregation |
| `public_marts.agg_sales_monthly` | marts | 36 | Monthly sales with MoM/YoY growth |
| `public_marts.agg_sales_by_product` | marts | 161,703 | Product performance by month |
| `public_marts.agg_sales_by_customer` | marts | 43,674 | Customer analytics by month |
| `public_marts.agg_sales_by_site` | marts | 36 | Site performance by month |
| `public_marts.agg_sales_by_staff` | marts | 3,123 | Staff performance by month |
| `public_marts.agg_returns` | marts | 91,536 | Return analysis by product/customer |
| `public_marts.metrics_summary` | marts | 1,094 | Daily KPI with MTD/YTD running totals |

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
| `DATABASE_URL` | `postgresql://datapulse:<password>@localhost:5432/datapulse` | PostgreSQL connection (set in .env) |
| `MAX_FILE_SIZE_MB` | 500 | Max upload file size |
| `MAX_ROWS` | 10,000,000 | Max rows per dataset |
| `MAX_COLUMNS` | 200 | Max columns per dataset |
| `BRONZE_BATCH_SIZE` | 50,000 | Rows per insert batch |

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
- All credentials via `.env` file (never hardcoded in source)
- Docker ports bound to `127.0.0.1` only
- Tenant-scoped RLS on `bronze.sales`, all marts tables, and silver view (`security_invoker=on`)
- Session variable pattern: `SET LOCAL app.tenant_id = '<id>'` — reader sees only their tenant's rows
- `FORCE ROW LEVEL SECURITY` on all RLS-enabled tables (owner bypass prevented)
- SQL column whitelist before INSERT (prevents injection)
- Financial columns use `NUMERIC(18,4)` (not floating-point)

### Testing
- pytest + pytest-cov
- Current coverage: 95%+ on `src/datapulse/`
- Target: 80%+ minimum

## Future Phases

- **Phase 1.3**: Data Cleaning (silver layer via dbt) [DONE]
- **Phase 1.3.5**: Security hardening, gold layer recovery, QC [DONE]
- **Phase 1.5 prep**: Tenant-scoped RLS across all layers [DONE]
- **Phase 1.4**: Data Analysis (analytics module, aggregations, FastAPI API, Power BI 99 measures + calc group) [DONE]
- **Phase 1.4.1**: Schema fixes, dbt agg models built, migrations applied, RLS active, API live [DONE]
- **Phase 1.5.1-1.5.3**: Next.js scaffold, API client, executive overview page [DONE]
- **Phase 1.5.4-1.5.7**: Analytics pages, polish, E2E tests
- **Phase 2**: Automation via n8n workflows
- **Phase 3**: AI-powered analysis via LangGraph
- **Phase 4**: Public website / landing page
