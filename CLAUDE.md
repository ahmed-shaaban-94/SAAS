# DataPulse — Business/Sales Analytics SaaS

## Project Overview

A data analytics platform for sales data: import raw Excel/CSV files, clean and transform through a medallion architecture (bronze/silver/gold), analyze with SQL, and visualize on interactive dashboards.

**Pipeline**: Import (Bronze) -> Clean (Silver) -> Analyze (Gold) -> Dashboard

## Session Context

At the start of every conversation, read `docs/brain/_INDEX.md` for recent session context
(last 5 sessions: what changed, which layers/modules were touched).

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
├── analytics/          # Gold layer: models, repository, service
├── pipeline/           # Pipeline tracking + execution + quality gates
├── api/                # FastAPI: app.py, deps.py, routes/ (46 route files, ~283 routes)
├── core/               # Cross-cutting primitives: auth, db, jwt, security, config
├── graph/              # Code intelligence: indexer.py, store.py, analyzers/, mcp_server.py
├── brain/              # Session memory (FTS + pgvector); MCP-indexed knowledge base
├── scheduler/          # APScheduler jobs (health, digests, sync schedules, #546-3 rls audit)
├── ai_light/           # Lightweight AI insights (OpenAI/Anthropic client)
├── anomalies/          # Anomaly detection + calendar
├── annotations/        # Chart annotations
├── audit/              # Audit log service
├── billing/            # Stripe subscription + plans
├── branding/           # Tenant branding (logo, colors)
├── control_center/     # Data control plane: connectors, mappings, pipeline drafts, sync
├── dispensing/         # Pharma dispensing analytics
├── embed/              # Embeddable chart tokens
├── expiry/             # Batch/lot expiry tracking (FEFO)
├── explore/            # Self-service data exploration
├── forecasting/        # Time-series forecasting
├── gamification/       # Points/badges system
├── insights_first/     # First-insight quick wins for the onboarding flow
├── inventory/          # Stock levels, reorder, movements
├── leads/              # Marketing lead capture
├── lineage/            # Data lineage tracking
├── notifications_center/ # In-app notification feed
├── onboarding/         # New tenant onboarding flow + sample pharma dataset seeder
├── pos/                # POS terminals, transactions, shifts, catalog (see also pos-desktop/)
├── purchase_orders/    # PO creation + receipt + vendor invoices
├── rbac/               # Role-based access control
├── reports/            # Scheduled report generation
├── reseller/           # Reseller/white-label support
├── scenarios/          # What-if scenario modeling
├── suppliers/          # Supplier CRUD + catalog
├── targets/            # KPI target tracking
├── tasks/              # Background task queue
├── upload/             # File upload + UUID path traversal prevention
├── views/              # Saved dashboard views
├── watcher/            # File system watcher for auto-ingestion
└── logging.py          # structlog

dbt/models/             # dbt transformation
├── bronze/             # Source definitions
├── staging/            # Silver: stg_sales (dedup, clean, 30 cols)
└── marts/              # Gold: 8 dims, 6 facts, 14 aggs, metrics_summary

migrations/             # 000-099+: schemas, RLS, tenants, pipeline_runs, quality_checks, POS, billing
n8n/workflows/          # 8 workflows: health, pipeline, success/failure/digest/error
frontend/               # Next.js 14: 60 pages, 116 hooks, Recharts, Tailwind, 28 Playwright E2E specs
android/                # Kotlin + Jetpack Compose: data/domain/presentation/di
tests/                  # pytest: 237 test files, unit coverage enforced at 77% in CI (target 95%)
```

## Docker Services

| Service | Container | Port | Purpose |
|---------|-----------|------|---------|
| `postgres` | datapulse-db | 5432 | PostgreSQL 16 + pgvector |
| `api` | datapulse-api | 8000 | FastAPI analytics API |
| `frontend` | datapulse-frontend | 3000 | Next.js dashboard |
| `redis` | datapulse-redis | (internal) | Redis cache |
| Auth0 / Clerk | Managed SaaS | — | Auth (OAuth2/OIDC) — `AUTH_PROVIDER` flag picks the active IdP |

```bash
docker compose up -d --build
```

## Database

### Schemas (Medallion)

| Schema | Purpose | Populated by |
|--------|---------|-------------|
| `bronze` | Raw data, as-is from source | Python bronze loader |
| `public_staging` / `silver` | Cleaned, transformed | dbt staging models |
| `public_marts` / `gold` | Aggregated, business-ready | dbt marts models (8 dims + 6 facts + 14 aggs) |
| `brain` | Session tracking, decisions, incidents, project knowledge | Stop hook + MCP tools |

### Key Data Volumes

- bronze.sales: 2.27M rows (Q1.2023-Q4.2025, 47 cols)
- stg_sales: ~1.1M (deduped), fct_sales: 1.13M (6 FKs, 4 financial measures)
- 8 dims: date(1096), billing(11), customer(24.8k), product(17.8k), site(2), staff(1.2k), plus pharma dims (batch, supplier)
- 14 aggs + metrics_summary + pipeline_runs + quality_checks

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
- **Authentication**: dual-provider — `AUTH_PROVIDER=auth0|clerk` (.env) picks the active IdP. Backend JWT verification reads `active_jwks_url` / `active_issuer_url` / `active_audience` from `core/config.py`, so `core/jwt.py` never branches on provider. Frontend uses a bridge (`frontend/src/lib/auth-bridge.tsx`) exposing NextAuth's `useSession`/`signIn`/`signOut` API backed by either `@clerk/nextjs` or `next-auth/react`; the `SessionProvider` mounts whichever is active. Clerk is a **temporary swap while clients are small** — flip `AUTH_PROVIDER=auth0` and `NEXT_PUBLIC_AUTH_PROVIDER=auth0` to return. The Clerk JWT template named `datapulse` must emit `tenant_id` + `roles` claims (see `scripts/clerk_setup.py`).
- **⚠ Provider swap runbook**: `AUTH_PROVIDER` (backend, runtime) and `NEXT_PUBLIC_AUTH_PROVIDER` (frontend, baked in at build time) **must match** and the frontend must be **rebuilt** whenever you flip either one. A mismatch = backend rejects every frontend-issued token as `Invalid token issuer`. The `_warn_on_auth_provider_mismatch` validator in `core/config.py` logs a startup warning if `CLERK_SECRET_KEY` is set with `AUTH_PROVIDER=auth0` (or vice-versa).
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
- pytest + pytest-cov: 237 test files, ~865 test functions (@pytest.mark.unit / integration split)
- Current unit coverage: ~79% on `src/datapulse/` (enforced in CI via `--cov-fail-under=77`; reproduce locally with `make coverage`). Target is 95% — tracked per-module; integration-test gate remains at 40% pending a measured baseline (issue #540).
- Playwright E2E tests: 12 spec files (`frontend/e2e/`)
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

**Phase 2 — Golden Path Sprint** (in flight): Upload → first-insight in < 5 min.
Tracked under epic [#398](https://github.com/ahmed-shaaban-94/Data-Pulse/issues/398); tasks #399–#405. Plan: `docs/superpowers/plans/2026-04-17-phase2-golden-path.md`.

### Sample Pharma Dataset (Phase 2 Task 2 / #401)

`src/datapulse/onboarding/sample_data.py` provides a deterministic 5 000-row
synthetic dataset that looks like a small Egyptian 10-branch pharma chain.

- **No PII, no real patient data, no real customer identifiers.** All
  customer names are generic group labels; staff names are fictional;
  product descriptions use therapeutic-class wording, not branded drugs.
- **Deterministic**: same `seed` → byte-identical rows. Safe for snapshot
  tests and idempotent reloads.
- **Idempotency markers**: every row tags `source_file='sample.csv'` and
  `source_quarter='SAMPLE'`. Reload = DELETE on markers + INSERT.
- **Tenant-scoped**: rows carry `tenant_id`; `insert_sample_rows` refuses
  a row/caller mismatch.
- **API**: `POST /api/v1/onboarding/load-sample` (rate-limited 5/min) —
  returns `{rows_loaded, pipeline_run_id, duration_seconds}`. Orchestrates
  via `SampleLoadService`: insert + create pipeline_run + seed synthetic
  passing quality_checks so Pipeline Health renders a healthy sample run.
- **Attribution**: the dataset is authored in-repo under `sample_data.py`.
  No external source; no license constraints.

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

## Code Intelligence Graph

`src/datapulse/graph/` — SQLite-backed symbol/edge graph of the full codebase.

```bash
# Re-index (run from project root)
PYTHONPATH=src python -m datapulse.graph

# Also available as an MCP server for Claude Code
PYTHONPATH=src python src/datapulse/graph/mcp_server.py
```

Indexes: Python symbols (functions, classes, methods), TypeScript components/hooks, dbt models. Edges: `calls`, `imports`, `depends_on`, `tests`. DB stored at `~/.datapulse/graph.db`.

## Brain (Session Memory)

`src/datapulse/brain/` — PostgreSQL-backed session tracking with FTS + pgvector semantic search.

**Storage**: `brain` schema in PostgreSQL (sessions, decisions, incidents, knowledge tables).

**MCP Tools** (registered in the same `datapulse-graph` MCP server):
| Tool | Purpose |
|------|---------|
| `brain_search(query)` | Hybrid FTS + semantic search across all brain tables |
| `brain_recent(count)` | Last N sessions with full detail |
| `brain_session(id)` | Single session with linked decisions/incidents |
| `brain_log_decision(title, body_md)` | Record a session-level decision |
| `brain_log_incident(title, body_md, severity)` | Record an incident |
| `brain_log_knowledge(title, body_md, category, tags)` | Store static project knowledge (architecture, API docs, runbooks, dbt explanations, onboarding) |
| `brain_knowledge_search(query, category)` | Search the project knowledge base by keyword and/or category |

**Hook**: Stop hook (`.claude/hooks/brain-session-end.sh`) auto-captures session data into PostgreSQL. Falls back to markdown files if DB is unavailable.

**Embedding**: Uses OpenRouter API (`OPENROUTER_API_KEY` + `BRAIN_EMBED_MODEL`) for 1536-dim vectors. Semantic search is optional — FTS always works without API key.

## Architecture Documentation

See `docs/ARCHITECTURE.md` for:
- System architecture (Mermaid diagrams)
- Data flow diagram
- Request flow sequence diagram
- Database ERD
- Module dependency map
- Deployment architecture
- Security architecture
