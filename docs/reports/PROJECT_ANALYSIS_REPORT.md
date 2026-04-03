# DataPulse — Full Project Analysis Report

## A. Project Overview (من الكود نفسه)

### إيه المشروع بيعمل بالظبط؟
DataPulse هو منصة SaaS لتحليل بيانات المبيعات الدوائية (pharmaceutical sales). المنصة بتستقبل ملفات Excel/CSV فيها بيانات مبيعات (~2.27 مليون صف)، بتنظفها عبر medallion architecture (Bronze → Silver → Gold)، وبتقدمها كـ dashboards تفاعلية + تحليلات متقدمة + تنبؤات + AI insights.

### Target Users
مديرين المبيعات وفرق التحليل في شركات الأدوية المصرية (Egyptian pharma — العملة EGP، خريطة مصر، بيانات bilingual AR/EN).

### Core Features الموجودة فعلاً (من الكود)

| Feature | Status | Evidence |
|---------|--------|----------|
| Bronze data ingestion (Excel→Parquet→PG) | **Working** | `bronze/loader.py`, 2.27M rows |
| Silver cleaning (dbt staging) | **Working** | `stg_sales.sql`, 1.1M deduplicated |
| Gold analytics (6 dims + 1 fact + 8 aggs) | **Working** | Full marts schema |
| REST API (84 endpoints) | **Working** | 13 route files |
| Next.js Dashboard (26 pages, 87 components) | **Working** | Full app router |
| Pipeline execution + quality gates | **Working** | executor, quality module |
| Forecasting (Holt-Winters, SMA, Seasonal Naive) | **Working** | `forecasting/` module |
| AI Insights (OpenRouter) | **Working** | `ai_light/` module |
| Self-serve Explore (dbt catalog → SQL) | **Working** | `explore/` module |
| SQL Lab (interactive queries) | **Working** | `sql_lab/` module |
| Targets & Alerts | **Working** | `targets/` module |
| Reports (templated) | **Working** | `reports/` module |
| CSV/Excel Export | **Working** | `export/` routes |
| Embedded Analytics (iframe tokens) | **Working** | `embed/` module |
| n8n Workflow Automation | **Working** | 7 workflows |
| Pipeline Dashboard UI | **Working** | pipeline components |
| Marketing/Landing Page | **Working** | `(marketing)/` routes |
| Dark/Light Theme | **Working** | next-themes + CSS vars |
| Auth (Auth0 OIDC + API Keys) | **Working** | jwt.py, auth.py, NextAuth |

### Features Under Development / Placeholder

| Feature | Status | Evidence |
|---------|--------|----------|
| File Watcher (Phase 2.4) | **Code exists, not deployed** | `watcher/` module, PLANNED in CLAUDE.md |
| Celery async queries | **Infrastructure ready** | celery-worker in docker-compose |
| Android App | **Code structure exists** | `android/` with Kotlin stubs |
| Power BI Integration | **Files exist** | `powerbi/` with 99 DAX measures |

---

## B. Tech Stack Analysis

### Backend

| Technology | Version | Usage |
|-----------|---------|-------|
| Python | 3.11+ | Primary language |
| FastAPI | ≥0.111 | REST API framework (84 endpoints) |
| SQLAlchemy | 2.0 | ORM + raw SQL via `text()` |
| Pydantic | ≥2.5 | Models, settings, validation |
| Polars + PyArrow | ≥1.0 / ≥15.0 | Data processing (bronze loader) |
| dbt-core + dbt-postgres | ≥1.8 | Data transformation (Silver/Gold) |
| Redis | ≥5.0 | Caching + Celery broker |
| Celery | ≥5.3 | Async query execution |
| structlog | ≥24.1 | Structured JSON logging |
| slowapi | ≥0.1.9 | Rate limiting per endpoint |
| PyJWT | ≥2.8 | Auth0 JWT validation |
| httpx | ≥0.27 | HTTP client (OpenRouter, n8n) |
| statsmodels | ≥0.14 | Forecasting (Holt-Winters) |
| Sentry SDK | ≥2.0 | Error tracking (optional) |
| uvicorn | ≥0.29 | ASGI server (4 workers) |

### Frontend

| Technology | Version | Usage |
|-----------|---------|-------|
| Next.js | 14.2.35 | App Router, SSR |
| TypeScript | 5.9.3 | Type safety |
| Tailwind CSS | 3.4.17 | Utility-first styling + custom tokens |
| SWR | 2.3.3 | Data fetching + stale-while-revalidate caching |
| Recharts | 2.15.3 | Charts & visualizations |
| NextAuth | 4.24.13 | Auth0 OIDC integration |
| react-day-picker | 9.14.0 | Date range picker |
| Radix UI | — | Headless UI primitives |
| next-themes | — | Dark/light mode |

### Infrastructure

| Technology | Version | Usage |
|-----------|---------|-------|
| PostgreSQL | 16-alpine | Primary database with RLS |
| Docker Compose | — | 9 services orchestration |
| n8n | 2.13.4 | Workflow automation (7 workflows) |
| Redis | 7-alpine | Cache + Celery broker |
| Nginx | 1.27-alpine | Reverse proxy (production) |
| Auth0 | SaaS | OIDC authentication |
| GitHub Actions | — | CI (6 jobs: lint, typecheck, test, frontend, docker, dbt) |

### External Services
- **Auth0** — Authentication (OIDC/OAuth2)
- **OpenRouter** — AI summaries & anomaly detection (free tier models)
- **Slack** — Pipeline notifications (webhook)
- **Sentry** — Error monitoring (optional)

---

## C. Architecture Mapping

### Services & Communication

```
                    ┌─────────────┐
                    │   Nginx     │ (host reverse proxy)
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │ Frontend │ │   API    │ │  pgAdmin  │
        │ (Next.js)│ │(FastAPI) │ │  (admin)  │
        │ :3000    │ │ :8000    │ │  :5050    │
        └────┬─────┘ └──┬───┬──┘ └────┬─────┘
             │          │   │         │
             │    ┌─────┘   └────┐    │
             ▼    ▼              ▼    ▼
        ┌──────────┐      ┌──────────┐
        │  Redis   │      │ Postgres │
        │ (cache)  │      │   (DB)   │
        └────┬─────┘      └────┬─────┘
             │                 │
        ┌────┴────┐     ┌─────┴─────┐
        │ Celery  │     │   n8n     │
        │ Worker  │     │ (workflows│
        └─────────┘     │  :5678)   │
                        └───────────┘
        ┌─────────┐
        │  App    │ (JupyterLab + Bronze loader)
        │ :8888   │
        └─────────┘
```

### Data Flow

```
Excel/CSV Files
     │
     ▼
[Bronze Loader] ─→ Parquet files + bronze.sales table (2.27M rows)
     │
     ▼
[dbt Staging]   ─→ stg_sales (1.1M deduplicated, cleaned)
     │
     ▼
[dbt Marts]     ─→ 6 dims + fct_sales + 8 aggregation tables
     │
     ▼
[Quality Gates] ─→ Null checks, row counts, duplicates, schema drift
     │
     ▼
[Redis Cache]   ─→ Analytics queries cached 5-10 min
     │
     ▼
[FastAPI]       ─→ 84 REST endpoints (JSON)
     │
     ▼
[Next.js SWR]   ─→ 40 hooks → 87 components → 26 pages
```

### Module Boundaries (Independent Units)

| Module | Can be modified independently? | Dependencies |
|--------|-------------------------------|-------------|
| `bronze/` | Yes | Config, DB |
| `analytics/` | Yes | DB (marts schema), Redis |
| `pipeline/` | Yes | DB, Bronze, dbt (subprocess) |
| `forecasting/` | Yes | DB, statsmodels |
| `ai_light/` | Yes | Analytics service, OpenRouter |
| `explore/` | Yes | dbt YAML, DB |
| `targets/` | Yes | DB |
| `reports/` | Yes | Analytics service |
| `watcher/` | Yes | API (HTTP trigger) |
| `frontend/` | Yes | API endpoints only |
| `dbt/` | Yes | DB schemas |

---

## D. Codebase Health

### Size & Complexity

| Area | Files | LOC (approx) | Complexity |
|------|-------|-------------|-----------|
| Backend Python | ~60 | ~5,500 | Medium — clean Service-Repository pattern |
| API Routes | 13 | ~1,200 | Low — thin controller layer |
| Frontend Components | 87 | ~6,000 | Medium — good component decomposition |
| Frontend Hooks | 40 | ~1,500 | Low — consistent SWR pattern |
| dbt Models | 18 | ~800 | Medium — complex joins in marts |
| Tests (Python) | 80 files | ~1,179 test functions | Excellent coverage |
| E2E Tests | 11 | ~300 | Good coverage |
| Migrations | 11 | ~400 | Clean, sequential |

### Testing
- **Python tests**: 80 test files, ~1,179 test functions
- **Coverage target**: 95%+ (enforced in CI via `--cov-fail-under=95`)
- **E2E tests**: 11 Playwright spec files
- **CI pipeline**: lint → typecheck → test → frontend build → Docker build → dbt validate

### Documentation
- `CLAUDE.md` — Comprehensive project guide (excellent)
- `docs/plans/` — Detailed phase plans (18 plan files)
- `docs/reports/` — Architecture reviews, "The Great Fix" report
- `CONTRIBUTING.md`, `SECURITY.md`, `CHANGELOG.md` — Standard OSS docs

### Technical Debt

| Issue | Severity | Location |
|-------|----------|----------|
| E2E tests disabled in CI | Medium | `.github/workflows/ci.yml:108` |
| Android app is stubs only | Low | `android/` |
| mypy `continue-on-error: true` | Low | CI typecheck job |
| File watcher not deployed | Low | `watcher/` module |
| No frontend unit tests running in CI | Medium | vitest config exists but no test files |

### Recurring Patterns (Template-worthy)
1. **New API endpoint**: Route → Dependency injection → Service → Repository → SQL
2. **New SWR hook**: `useSWR(swrKey('/path', params), fetchAPI)` with FilterContext
3. **New component**: FC with SWR hook, loading/error/empty states, chart rendering
4. **New dbt model**: SQL + YAML schema + tests
5. **New quality check**: Function in quality.py → registered in check list

---

## E. Team Roles (5 أفراد)

### Role 1: Data Pipeline Engineer
**Scope**: Bronze ingestion → dbt transforms → Quality gates → Pipeline execution

**Files**:
- `src/datapulse/bronze/` (loader, column mapping)
- `src/datapulse/pipeline/` (executor, quality, state machine, retry, rollback)
- `dbt/models/` (all SQL models — staging, marts, aggs)
- `migrations/`
- `n8n/workflows/`

**Knowledge needed**: SQL (PostgreSQL), dbt, Polars/PyArrow, data quality patterns, n8n workflow design

### Role 2: Analytics & Intelligence Engineer
**Scope**: Analytics queries → Forecasting → AI insights → Targets/Alerts → Reports/Export

**Files**:
- `src/datapulse/analytics/` (7 repository files, service, models)
- `src/datapulse/forecasting/` (methods, service, repository)
- `src/datapulse/ai_light/` (client, service, prompts)
- `src/datapulse/targets/` (targets, alerts)
- `src/datapulse/reports/` (template engine)
- `src/datapulse/explore/` (SQL builder, manifest parser)
- `src/datapulse/sql_lab/` (SQL validator)

**Knowledge needed**: SQL analytics, time-series forecasting, LLM prompting, ABC/RFM analysis

### Role 3: Backend Platform Engineer
**Scope**: API framework → Auth → Caching → Async tasks → Config → Infrastructure

**Files**:
- `src/datapulse/api/` (app.py, deps.py, jwt.py, auth.py, limiter.py, pagination.py)
- `src/datapulse/core/` (config, db, security)
- `src/datapulse/cache.py`, `cache_decorator.py`
- `src/datapulse/tasks/` (Celery)
- `docker-compose.yml`, `Dockerfile`, `Makefile`
- `.github/workflows/`, `nginx/`, `scripts/`

**Knowledge needed**: FastAPI, SQLAlchemy, JWT/OIDC, Redis, Celery, Docker, CI/CD

### Role 4: Frontend Dashboard Engineer
**Scope**: Dashboard pages → Components → Charts → State management → API integration

**Files**:
- `frontend/src/app/(app)/` (all 19 app pages)
- `frontend/src/components/` (all 87 components)
- `frontend/src/hooks/` (all 40 hooks)
- `frontend/src/contexts/`, `lib/`, `types/`
- `frontend/tailwind.config.ts`, `globals.css`

**Knowledge needed**: Next.js 14 App Router, TypeScript, Tailwind CSS, Recharts, SWR

### Role 5: Quality & Growth Engineer
**Scope**: Testing → E2E → Marketing/Landing → Android → Documentation

**Files**:
- `tests/` (80 test files, 1,179 tests)
- `frontend/e2e/` (11 Playwright specs)
- `frontend/src/app/(marketing)/` (landing page, terms, privacy)
- `android/` (Kotlin app)
- `docs/`

**Knowledge needed**: pytest, Playwright, Kotlin/Jetpack Compose, documentation

### Interaction Map

```
     ┌──── Pipeline Engineer ────┐
     │                           │
     ▼                           ▼
Analytics Engineer ←──── Platform Engineer
     │                           │
     ▼                           ▼
Frontend Engineer ←───── Quality Engineer
```

---

## F. API Endpoints Summary (84 total)

### Health (1)
- `GET /health` — DB connectivity check (503 if unreachable)

### Analytics (25 under /api/v1/analytics/)
All accept: `start_date`, `end_date`, `category`, `brand`, `site_key`, `staff_key`, `limit`
- `/dashboard` (composite), `/summary`, `/date-range`
- `/trends/daily`, `/trends/monthly`
- `/products/top`, `/customers/top`, `/staff/top`, `/sites`
- `/products/{key}`, `/customers/{key}`, `/staff/{key}`, `/sites/{key}`
- `/filters/options`, `/billing-breakdown`, `/customer-type-breakdown`
- `/top-movers`, `/products/by-category`, `/returns`, `/returns/trend`
- `/abc-analysis`, `/heatmap`, `/segments/summary`

### Pipeline (13 under /api/v1/pipeline/)
- `GET /runs`, `/runs/latest`, `/runs/{id}`, `/runs/{id}/stream` (SSE), `/runs/{id}/quality`
- `POST /runs`, `PATCH /runs/{id}`, `POST /trigger`, `POST /runs/{id}/resume`
- `POST /execute/bronze`, `/execute/dbt-staging`, `/execute/dbt-marts`, `/execute/quality-check`

### Forecasting (4), AI-Light (4), Explore (4), SQL Lab (2)
### Targets (10), Reports (3), Export (3), Embed (2), Queries (2)

---

## G. Database Schema

### Key Tables

| Table | Schema | Rows | Purpose |
|-------|--------|------|---------|
| `bronze.sales` | bronze | 2,269,598 | Raw sales (47 columns, tenant_id) |
| `stg_sales` | staging | ~1.1M | Cleaned (37 cols, deduped, EN billing) |
| `dim_date` | marts | 1,096 | Calendar 2023-2025 |
| `dim_billing` | marts | 11 | Billing types (10 + Unknown) |
| `dim_customer` | marts | 24,801 | Customers (unknown at key=-1) |
| `dim_product` | marts | 17,803 | Products (drug_code, brand, category) |
| `dim_site` | marts | 2 | Sites (name, area_manager) |
| `dim_staff` | marts | 1,226 | Staff (name, position) |
| `fct_sales` | marts | 1,134,073 | Fact table (6 FKs COALESCE to -1) |
| `agg_sales_daily` | marts | 9,004 | Daily aggregation |
| `agg_sales_monthly` | marts | 36 | Monthly + MoM/YoY growth |
| `metrics_summary` | marts | 1,094 | Daily KPI + MTD/YTD running totals |
| `pipeline_runs` | public | — | Pipeline execution tracking |
| `quality_checks` | public | — | Quality gate results per stage |

### Row-Level Security (RLS)
All tables use tenant-scoped RLS:
```sql
SET LOCAL app.tenant_id = :tid;
-- PostgreSQL policies filter rows automatically
```

---

## H. Docker Services (9)

| Service | Port | RAM | Purpose |
|---------|------|-----|---------|
| api | 8000 | 512M | FastAPI (4 uvicorn workers) |
| frontend | 3000 | 512M | Next.js (standalone) |
| postgres | 5432 | 2G | PostgreSQL 16 + RLS |
| redis | — | 256M | Cache + Celery broker |
| celery-worker | — | 512M | Async queries (4 concurrency) |
| n8n | 5678 | 512M | Workflow automation |
| app | 8888 | 2G | JupyterLab + Bronze loader |
| pgadmin | 5050 | 256M | DB admin UI |
| prestart | — | — | Run migrations, exit |

---

## I. Frontend Summary

| Category | Count |
|----------|-------|
| Pages | 26 (19 app + 4 marketing + 3 special) |
| Components | 87 |
| SWR Hooks | 40 |
| Contexts | 2 (Filter + DashboardData) |
| State Management | SWR + URL-driven filters |
| Auth | NextAuth (primary) + localStorage (fallback) |

---

## J. Future Phases

| Phase | Status |
|-------|--------|
| Phase 2.4: File Watcher | PLANNED (code exists) |
| Phase 5: Multi-tenancy & Billing | PLANNED |
| Phase 6: Data Sources & Connectors | PLANNED |
| Phase 7: Self-Service Analytics | PLANNED |
| Phase 8: AI & Intelligence v2 | PLANNED |
| Phase 9: Collaboration & Teams | PLANNED |
| Phase 10: Scale & Infrastructure | PLANNED |

---

## K. Claude Code Setup (Delivered)

### Skills (16 lightweight, role-specific)
```
/mnt/skills/user/
├── dp-context/              # Shared project reference (~386 tokens)
├── dp-pipeline-dbt/         # dbt models & migrations
├── dp-pipeline-execution/   # Pipeline runs & quality gates
├── dp-pipeline-bronze/      # Data ingestion
├── dp-analytics-queries/    # Dashboard analytics
├── dp-analytics-forecasting-ai/  # Forecasting & AI
├── dp-analytics-explore/    # Explore, targets, reports
├── dp-platform-api/         # API framework & routing
├── dp-platform-auth-cache/  # Auth, JWT, Redis, Celery
├── dp-platform-infra/       # Docker, CI, Nginx
├── dp-fe-patterns/          # Components & pages
├── dp-fe-charts/            # Recharts & theme
├── dp-fe-api-state/         # SWR hooks & filters
├── dp-qa-python/            # Python testing
├── dp-qa-e2e/               # Playwright E2E
└── dp-qa-marketing/         # Marketing & Android
```

### Agents (7 workflow automations)
```
.claude/agents/
├── add-dbt-model.md         # /add-dbt-model agg <name>
├── add-migration.md         # /add-migration <desc>
├── add-analytics-endpoint.md # /add-analytics-endpoint <name>
├── add-docker-service.md    # /add-docker-service <name> <image> <port>
├── add-page.md              # /add-page <name> <desc>
├── add-chart.md             # /add-chart <type> <name>
└── coverage-check.md        # /coverage-check [module]
```

### Per-User CLAUDE.md Files (6)
```
docs/team-configs/
├── CLAUDE-pipeline-engineer.md      # 557 lines
├── CLAUDE-analytics-engineer.md     # 370 lines
├── CLAUDE-platform-engineer.md      # 369 lines
├── CLAUDE-frontend-engineer.md      # 379 lines
├── CLAUDE-quality-growth-engineer.md # 405 lines
└── CLAUDE-gm.md                     # 384 lines (master account)
```

Each file is fully self-contained — copy as `CLAUDE.md` in repo root and go.
