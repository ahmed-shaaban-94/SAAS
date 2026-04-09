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
| Frontend | Next.js 14 + TypeScript + Tailwind CSS |
| Charts | Recharts |
| Data Fetching | SWR |
| BI / Analytics | Power BI Desktop (Import mode, 99 DAX measures) |

## Project Structure

```
src/datapulse/          # Python backend
├── config.py           # Pydantic settings
├── bronze/             # Bronze layer: loader.py, column_map.py
├── import_pipeline/    # CSV/Excel reader, validator, type detector
├── analytics/          # Gold layer: models, repository, service (10 API endpoints)
├── pipeline/           # Pipeline tracking + execution + quality gates (11 API endpoints)
├── api/                # FastAPI: app.py, deps.py, routes/ (health, analytics, pipeline)
└── logging.py          # structlog

dbt/models/             # dbt transformation
├── bronze/             # Source definitions
├── staging/            # Silver: stg_sales (dedup, clean, 30 cols)
└── marts/              # Gold: 6 dims, 1 fact, 8 aggs, metrics_summary

migrations/             # 000-007: schemas, RLS, tenants, n8n, pipeline_runs, quality_checks
n8n/workflows/          # 6 workflows: health, pipeline, success/failure/digest/error
frontend/               # Next.js 14: 6 pages, 9 SWR hooks, Recharts, Tailwind, Playwright E2E
android/                # Kotlin + Jetpack Compose: data/domain/presentation/di
tests/                  # pytest: reader, type_detector, config, validator, loader, coverage
```

## Docker Services

| Service | Container | Port | Purpose |
|---------|-----------|------|---------|
| `postgres` | datapulse-db | 5432 | PostgreSQL 16 |
| `api` | datapulse-api | 8000 | FastAPI analytics API |
| `frontend` | datapulse-frontend | 3000 | Next.js dashboard |
| `redis` | datapulse-redis | (internal) | Redis cache |
| Auth0 | Managed SaaS | — | Auth (OAuth2/OIDC) |

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

### Key Data Volumes

- bronze.sales: 2.27M rows (Q1.2023-Q4.2025, 47 cols)
- stg_sales: ~1.1M (deduped), fct_sales: 1.13M (6 FKs, 4 financial measures)
- 6 dims: date(1096), billing(11), customer(24.8k), product(17.8k), site(2), staff(1.2k)
- 8 aggs + metrics_summary + pipeline_runs + quality_checks

## Running the Bronze Pipeline

```bash
docker exec -it datapulse-api python -m datapulse.bronze.loader --source /app/data/raw/sales
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
- **Authentication**: Auth0 OIDC — backend JWT validation (`src/datapulse/api/jwt.py`), frontend NextAuth (`frontend/src/lib/auth.ts`)
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
- Vitest + MSW + Testing Library available for frontend unit tests
- Run tests: `make test` (Python), `docker compose exec frontend npx playwright test` (E2E)

### Frontend Features
- **Theming**: Dark/light mode via `next-themes` (attribute="class", defaultTheme="dark"). CSS variables in globals.css, `useChartTheme` hook for Recharts SVG compatibility. Toggle in sidebar footer.
- **Date Range Picker**: `react-day-picker` + `@radix-ui/react-popover` in filter-bar alongside presets
- **Detail Page Trends**: Monthly revenue trend charts on product/customer/staff detail pages via `monthly_trend` API field
- **Print Report**: `/dashboard/report` page with print-optimized layout, `@media print` styles in globals.css
- **Mobile**: Touch swipe-to-close on sidebar drawer (60px threshold)

## Deployment

- When deploying to the droplet, always check for `docker-compose.override.yml` that may force dev mode. Remove or rename it before production builds.
- Always use `docker compose build --no-cache` when deploying code changes, and verify containers are running the latest image after deploy.
- Each conversation/feature should use a separate git branch. Create a descriptive branch name before starting work.

## Code Quality

- After making code changes, always run CI lint checks locally before pushing. Use `ruff check src/ tests/` (Python) and `npx tsc --noEmit` (TypeScript) to catch failures early.

## Data Pipeline

- When fixing dbt models, verify that all referenced columns actually exist in the source data before applying transformations. Check both staging and production schemas.

## Future Phases

Phases 1.3–2.8 + The Great Fix + Enhancements 2-3 + Phase 4 = all DONE.

- **Phase 5**: Multi-tenancy & Billing — Stripe subscriptions, usage metering, admin panel [PLANNED]
- **Phase 6**: Data Sources & Connectors — Google Sheets, MySQL/SQL Server, Shopify, schema mapping [PLANNED]
- **Phase 7**: Self-Service Analytics — saved views, dashboard builder, scheduled reports, export [PLANNED]
- **Phase 8**: AI & Intelligence — NL queries (AR/EN), forecasting, ML alerts, AI summaries v2 [PLANNED]
- **Phase 9**: Collaboration & Teams — comments, sharing, workspaces, activity feed [PLANNED]
- **Phase 10**: Scale & Infra — S3/MinIO, Celery, Redis, Kubernetes, CDN, Prometheus+Grafana [PLANNED]

## Team Structure & Roles

5-person team, each with dedicated Claude Code skills and agents:

| Role | Scope | Key Directories |
|------|-------|----------------|
| **Pipeline Engineer** | Bronze ingestion, dbt models, quality gates, migrations, n8n | `src/datapulse/bronze/`, `pipeline/`, `dbt/`, `migrations/`, `n8n/` |
| **Analytics Engineer** | Analytics queries, forecasting, AI insights, targets, explore | `src/datapulse/analytics/`, `forecasting/`, `ai_light/`, `targets/`, `explore/` |
| **Platform Engineer** | API framework, auth, caching, async tasks, Docker, CI/CD | `src/datapulse/api/`, `core/`, `cache*.py`, `tasks/`, `docker-compose.yml` |
| **Frontend Engineer** | Dashboard pages, components, hooks, state, charts, theme | `frontend/src/` |
| **Quality & Growth Engineer** | Testing, E2E, marketing, Android, documentation | `tests/`, `frontend/e2e/`, `frontend/src/app/(marketing)/`, `android/`, `docs/` |

## Claude Code Agents

Custom agents in `.claude/agents/` for common workflows:

| Agent | Command | What it does |
|-------|---------|-------------|
| `add-dbt-model` | `/add-dbt-model agg <name>` | Scaffold dbt model + schema YAML + run + test |
| `add-migration` | `/add-migration <desc>` | Idempotent migration + RLS + apply |
| `add-analytics-endpoint` | `/add-analytics-endpoint <name>` | Model → Repo → Service (cached) → Route → Test |
| `add-docker-service` | `/add-docker-service <name> <image>` | Add to 3 compose files + healthcheck + env |
| `add-page` | `/add-page <name>` | Next.js page + loading + hook + component + nav |
| `add-chart` | `/add-chart <type> <name>` | Recharts component + theme + ChartCard |
| `coverage-check` | `/coverage-check [module]` | Run tests → analyze gaps → suggest/write tests |

## Architecture Documentation

See `docs/ARCHITECTURE.md` for:
- System architecture (Mermaid diagrams)
- Data flow diagram
- Request flow sequence diagram
- Database ERD
- Module dependency map
- Deployment architecture
- Security architecture
