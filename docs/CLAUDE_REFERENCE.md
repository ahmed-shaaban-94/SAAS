# DataPulse — Claude Reference (load on demand)

> Extracted from `CLAUDE.md` to keep per-turn context small. Read this file when you need the information, not every turn.

## Medallion Data Architecture

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

## Tech Stack

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
├── config.py           # Pydantic settings (re-export from core/config.py)
├── bronze/             # Bronze layer: loader.py, column_map.py
├── import_pipeline/    # CSV/Excel reader, validator, type detector
├── analytics/          # Gold-layer queries, repository, service
├── pipeline/           # Pipeline tracking + execution + quality gates
├── api/                # FastAPI: app.py, deps.py, routes/ (~46 route files, ~283 routes)
├── core/               # Cross-cutting primitives: auth, db, jwt, security, config
├── graph/              # Code intelligence: indexer.py, store.py, analyzers/, mcp_server.py
├── brain/              # Session memory (FTS + pgvector); MCP-indexed knowledge base
├── scheduler/          # APScheduler jobs (health, digests, sync schedules, rls audit)
├── ai_light/           # Lightweight AI insights (OpenAI/Anthropic/OpenRouter)
├── anomalies/          # Anomaly detection + calendar
├── annotations/        # Chart annotations
├── audit/              # Audit log service
├── billing/            # Stripe + Paymob subscription
├── branding/           # Tenant branding (logo, colors)
├── control_center/     # Data control plane: connectors, mappings, pipeline drafts, sync
├── dispensing/         # Pharma dispensing analytics
├── embed/              # Embeddable chart tokens
├── expiry/             # Batch/lot expiry tracking (FEFO)
├── explore/            # Self-service data exploration
├── forecasting/        # Time-series forecasting
├── gamification/       # Points/badges
├── insights_first/     # First-insight quick wins for onboarding
├── inventory/          # Stock levels, reorder, movements
├── leads/              # Marketing lead capture
├── lineage/            # Data lineage tracking
├── notifications_center/ # In-app notifications
├── onboarding/         # New tenant onboarding + sample pharma seeder
├── pos/                # POS terminals, transactions, shifts, catalog
├── purchase_orders/    # PO creation + receipt + vendor invoices
├── rbac/               # Role-based access control
├── reports/            # Scheduled report generation
├── reseller/           # Reseller / white-label
├── scenarios/          # What-if scenario modeling
├── suppliers/          # Supplier CRUD + catalog
├── targets/            # KPI target tracking
├── tasks/              # Background task queue
├── upload/             # File upload + UUID path traversal prevention
├── views/              # Saved dashboard views
├── watcher/            # File system watcher for auto-ingestion
└── logging.py          # structlog config

dbt/models/
├── bronze/             # Source definitions
├── staging/            # Silver: stg_sales (dedup, clean, 30 cols)
└── marts/              # Gold: 8 dims, 6 facts, 14 aggs, metrics_summary

migrations/             # 000-099+: schemas, RLS, tenants, pipeline_runs, POS, billing
n8n/workflows/          # 8 workflows: health, pipeline, success/failure/digest/error
frontend/               # Next.js 14: ~60 pages, 116 hooks, Recharts, Tailwind, 28 Playwright specs
android/                # Kotlin + Jetpack Compose: data/domain/presentation/di
tests/                  # pytest: 237 test files, unit coverage ≥77% in CI
```

## Docker Services

| Service | Container | Port | Purpose |
|---------|-----------|------|---------|
| `postgres` | datapulse-db | 5432 | PostgreSQL 16 + pgvector |
| `api` | datapulse-api | 8000 | FastAPI analytics API |
| `frontend` | datapulse-frontend | 3000 | Next.js dashboard |
| `redis` | datapulse-redis | (internal) | Redis cache |
| Clerk | Managed SaaS | — | Auth (OAuth2/OIDC) — sole IdP |

`docker compose up -d --build` brings up the local stack.

## Database Schemas

| Schema | Purpose | Populated by |
|--------|---------|-------------|
| `bronze` | Raw data, as-is from source | Python bronze loader |
| `public_staging` / `silver` | Cleaned, transformed | dbt staging models |
| `public_marts` / `gold` | Aggregated, business-ready | dbt marts (8 dims + 6 facts + 14 aggs) |
| `brain` | Session memory, decisions, incidents, knowledge | Stop hook + MCP tools |

### Key Data Volumes
- bronze.sales: 2.27M rows (Q1.2023–Q4.2025, 47 cols)
- stg_sales: ~1.1M (deduped); fct_sales: 1.13M (6 FKs, 4 financial measures)
- 8 dims: date (1096), billing (11), customer (24.8k), product (17.8k), site (2), staff (1.2k), plus pharma dims (batch, supplier)
- 14 aggs + metrics_summary + pipeline_runs + quality_checks

## Frontend features

- **Theming**: dark/light via `next-themes` (attribute="class", defaultTheme="dark"). CSS vars in globals.css. `useChartTheme` hook for Recharts SVG compatibility. Toggle in sidebar footer.
- **Date range picker**: `react-day-picker` + `@radix-ui/react-popover` in filter-bar alongside presets.
- **Detail page trends**: monthly revenue trend charts on product/customer/staff detail pages via `monthly_trend` API field.
- **Print report**: `/dashboard/report` with `@media print` styles in globals.css.
- **Mobile**: touch swipe-to-close on sidebar drawer (60px threshold).

## API contract (issue #658)

Shared source of truth at `contracts/openapi.json`, generated from the
FastAPI app by `scripts/dump_openapi.py`. The frontend reads it via
`openapi-typescript` into `frontend/src/generated/api.ts`.

- After any route / Pydantic response model change: `make openapi` then
  `cd frontend && npm run codegen`. Commit both files.
- Reference a response shape by endpoint path in hooks:
  `fetchAPI<ApiGet<"/api/v1/analytics/summary">>(...)` — helper lives in
  `frontend/src/lib/api-types.ts`.
- CI gates the drift in two places: `typecheck` job runs
  `make openapi-check`; `frontend` job runs `npm run codegen:check`.
- Pilot hooks on the generated types: `use-summary`, `use-top-products`,
  `use-daily-trend`. Full migration of the remaining ~100 hooks is
  follow-up work tracked per domain.

## Testing

- pytest + pytest-cov: 237 test files, ~865 test functions, `@pytest.mark.unit` / `@pytest.mark.integration` split
- Current unit coverage: ~79% on `src/datapulse/` (CI gate: `--cov-fail-under=77`; reproduce with `make coverage`). Target 95% per-module. Integration gate at 40% pending measured baseline (issue #540).
- Playwright E2E: 12 spec files in `frontend/e2e/`
- Vitest + MSW + Testing Library available for frontend unit tests
- Run: `make test` (Python), `docker compose exec frontend npx playwright test` (E2E)

## Deployment

- Check for `docker-compose.override.yml` that may force dev mode; remove/rename before production builds.
- Always use `docker compose build --no-cache` when deploying code changes; verify containers are on the latest image after deploy.
- Each conversation / feature = separate git branch.

## Team Structure & Roles

5-person team, each with dedicated Claude Code skills and agents:

| Role | Scope | Key Directories |
|------|-------|----------------|
| Pipeline Engineer | Bronze ingestion, dbt models, quality gates, migrations, n8n | `src/datapulse/bronze/`, `pipeline/`, `dbt/`, `migrations/`, `n8n/` |
| Analytics Engineer | Analytics queries, forecasting, AI insights, targets, explore | `src/datapulse/analytics/`, `forecasting/`, `ai_light/`, `targets/`, `explore/` |
| Platform Engineer | API framework, auth, caching, async tasks, Docker, CI/CD | `src/datapulse/api/`, `core/`, `cache*.py`, `tasks/`, `docker-compose.yml` |
| Frontend Engineer | Dashboard pages, components, hooks, state, charts, theme | `frontend/src/` |
| Quality & Growth Engineer | Testing, E2E, marketing, Android, documentation | `tests/`, `frontend/e2e/`, `frontend/src/app/(marketing)/`, `android/`, `docs/` |

## Claude Code Agents (project scaffolds)

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

Indexes Python symbols (functions, classes, methods), TypeScript components/hooks, dbt models. Edges: `calls`, `imports`, `depends_on`, `tests`. DB at `~/.datapulse/graph.db`. See `docs/CONVENTIONS/graph-mcp.md` for usage rules.

## Brain (Session Memory)

`src/datapulse/brain/` — PostgreSQL-backed session tracking with FTS + pgvector semantic search. Storage: `brain` schema (sessions, decisions, incidents, knowledge tables).

MCP tools (registered in the `datapulse-graph` server):

| Tool | Purpose |
|------|---------|
| `brain_search(query)` | Hybrid FTS + semantic search across all brain tables |
| `brain_recent(count)` | Last N sessions with full detail |
| `brain_session(id)` | Single session with linked decisions/incidents |
| `brain_log_decision(title, body_md)` | Record a session-level decision |
| `brain_log_incident(title, body_md, severity)` | Record an incident |
| `brain_log_knowledge(title, body_md, category, tags)` | Store static project knowledge |
| `brain_knowledge_search(query, category)` | Search knowledge by keyword / category |

**Hook**: Stop hook `.claude/hooks/brain-session-end.sh` auto-captures session data into PostgreSQL; falls back to markdown files if DB unavailable.

**Embedding**: OpenRouter API (`OPENROUTER_API_KEY` + `BRAIN_EMBED_MODEL`) for 1536-dim vectors. Semantic search is optional — FTS always works without an API key.

See `docs/CONVENTIONS/second-brain.md` for when to read/write the vault.

## Phase Roadmap

- Phases 1.3–2.8 + The Great Fix + Enhancements 2–3 + Phase 4 = **DONE**.
- **Phase 2 Golden Path** (in flight): Upload → first-insight in <5 min. Epic #398, tasks #399–#405. Plan: `docs/superpowers/plans/2026-04-17-phase2-golden-path.md`.
- **Phase 5**: Multi-tenancy & Billing — Stripe subscriptions, usage metering, admin panel [PLANNED]
- **Phase 6**: Data Sources & Connectors — Google Sheets, MySQL/SQL Server, Shopify, schema mapping [PLANNED]
- **Phase 7**: Self-Service Analytics — saved views, dashboard builder, scheduled reports, export [PLANNED]
- **Phase 8**: AI & Intelligence — NL queries (AR/EN), forecasting, ML alerts, AI summaries v2 [PLANNED]
- **Phase 9**: Collaboration & Teams — comments, sharing, workspaces, activity feed [PLANNED]
- **Phase 10**: Scale & Infra — S3/MinIO, Celery, Redis, Kubernetes, CDN, Prometheus+Grafana [PLANNED]

### Sample Pharma Dataset (Phase 2 Task 2 / #401)

`src/datapulse/onboarding/sample_data.py` provides a deterministic 5,000-row synthetic dataset resembling a small Egyptian 10-branch pharma chain.

- **No PII, no real patient data, no real customer identifiers.** Customer names are generic labels; staff names are fictional; product descriptions use therapeutic-class wording, not branded drugs.
- **Deterministic**: same `seed` → byte-identical rows. Safe for snapshot tests and idempotent reloads.
- **Idempotency markers**: every row tags `source_file='sample.csv'` and `source_quarter='SAMPLE'`. Reload = DELETE on markers + INSERT.
- **Tenant-scoped**: rows carry `tenant_id`; `insert_sample_rows` refuses a row/caller mismatch.
- **API**: `POST /api/v1/onboarding/load-sample` (5/min rate limit) — returns `{rows_loaded, pipeline_run_id, duration_seconds}`. Orchestrated via `SampleLoadService` (insert + pipeline_run + synthetic passing quality_checks so Pipeline Health renders a healthy sample run).
