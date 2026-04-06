# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Changed
- Reorganized repository structure for professional presentation
- Moved plan documents into organized `docs/plans/` hierarchy
- Created comprehensive phase plans with sub-phase breakdowns
- Added validation & debugging runbooks
- Rewrote README.md with complete project documentation

## [0.7.0] - 2026-04 — Dragon Roar: Full Audit & Hardening

### Added
- **Billing**: Stripe integration — checkout, portal, webhook, subscription status
- **Forecasting**: Revenue forecasting with Prophet, forecast summary API
- **Annotations**: Chart annotation system for marking events on dashboards
- **Embed**: White-label iframe embed with token-based auth
- **Onboarding**: User onboarding module with progress tracking
- **Notifications Center**: In-app notification system with SSE real-time updates
- **Targets & Goals**: Budget vs actual tracking, KPI target management
- **Saved Views**: User-customizable dashboard view persistence
- **Explore**: Self-service SQL query builder with dbt manifest catalog
- **Dashboard Builder**: Drag-and-drop dashboard layout customization
- **Custom Reports**: Parameterized SQL report template engine
- **Android App**: Kotlin + Jetpack Compose mobile client (data/domain/presentation/di)
- **Scheduler**: In-process APScheduler replacing n8n (health checks, quality digest, AI digest)
- **Tests**: 3 new test files (scheduler, async executor, Slack notifications)
- **Migration 023**: Expression indexes on `(year*100+month)` for agg table performance

### Fixed
- **CRITICAL**: Quality checks referenced `net_sales` column on stg_sales — column does not exist; blocked every pipeline run at silver gate
- **Data integrity**: Added `net_amount` column across stg_sales, fct_sales, and all agg models
- **Data integrity**: Added `tenant_id` to stg_sales dedup PARTITION BY — prevents cross-tenant false deduplication
- **Data integrity**: Replaced non-deterministic `ROW_NUMBER()` dimension keys with stable MD5 hash keys
- **Security**: Auth env detection used `os.getenv()` instead of settings object — production could mis-detect as dev
- **Security**: Health endpoint exposed infrastructure details to unauthenticated callers
- **Security**: CORS default included `localhost:3000` — applied in production if not overridden
- **Security**: Embed/billing sessions lacked `statement_timeout` — runaway queries possible
- **Security**: Async SQL blocklist missing `VACUUM`, `ANALYZE`, `LOCK` + no semicolon/comment rejection
- **Security**: Bronze loader path traversal used string prefix check instead of `Path.is_relative_to()`
- **Performance**: `EXTRACT()` in heatmap/significance queries blocked index usage — rewrote to range predicates
- **Performance**: Why-Changed diagnostic fired 12 queries (3 per dimension) — folded totals into main CTE (now 4 queries)
- **Pipeline**: Forecasting route didn't pass `tenant_id` — defaulted to tenant "1"
- **Pipeline**: dbt subprocess not killed on timeout — orphaned processes accumulated
- **Pipeline**: No concurrency guard — added PostgreSQL advisory lock to prevent concurrent pipeline runs
- **Pipeline**: `with_retry` decorator existed but was never wired into executor — now applied to bronze loader
- **Frontend**: `use-returns.test.ts` referenced `product_name` but type is `drug_name` — TypeScript check failed
- **Frontend**: `use-billing.ts` passed `fetchAPI` as value instead of lambda — fragile auth propagation
- **CI**: `continue-on-error: true` on mypy — type errors never failed CI (removed)
- **CI**: E2E tests not in CI — added Playwright job
- **Observability**: Bound `run_id` + `tenant_id` to structlog context vars for pipeline log correlation
- **Observability**: `get_site_detail` was the only uncached detail method — added `@cached`

### Removed
- Dead hooks: `use-monthly-trend.ts`, `use-ai-status.ts`, `use-track.ts` (zero imports)
- Dead module: `pipeline/anomaly.py` (superseded by `anomalies/` package)
- Dead test: `test_anomaly.py` (tested removed module)
- Deprecated: `metrics_summary` net amount aliases that just copied gross values

### Changed
- Docker prod compose requires `IMAGE_TAG`, `API_KEY`, `PIPELINE_WEBHOOK_SECRET` (fail-fast)
- Docker prod compose sets `SENTRY_ENVIRONMENT: production` for API
- Frontend coverage thresholds raised from 3% to 20%
- Sanitized `.env.example` — removed real Sentry DSNs and local filesystem paths
- `.gitignore` now excludes `*.pem`, `*.key`, `*.crt`, `*.p12`
- Extracted shared `ChartTooltip` component + `findPeakValley` utility (eliminated 5x duplication)
- Added `aria-current="page"` to active sidebar nav links
- Added `ErrorRetry` error states to 3 customer/staff components
- Scheduler quality digest uses parameterized tenant query instead of hardcoded `'1'`
- `conftest.py` patch refactored to dynamic list with ExitStack + optional patches

## [0.6.0] - 2026-03 — Phase 4: Public Website

### Added
- **Landing Page**: Hero section with CSS-only dashboard mockup
- **Features Grid**: 6 feature cards with glow hover effects
- **Pipeline Visualization**: 4 connected steps (Import -> Clean -> Analyze -> Visualize)
- **Stats Banner**: 4 animated count-up metrics
- **Pricing Section**: 3 tiers (Starter/Pro/Enterprise) with popular badge
- **FAQ Accordion**: 8 questions with single-open behavior
- **Waitlist Form**: Email collection with rate limiting and validation
- **Legal Pages**: Privacy policy and terms of service
- **SEO**: Meta tags, Open Graph, Twitter cards, JSON-LD, sitemap, robots.txt
- **Accessibility**: Skip-to-content, ARIA, keyboard nav, reduced motion
- **E2E Tests**: 18 marketing + SEO specs
- **Route Groups**: `(marketing)` + `(app)` separation

## [0.5.0] - 2026-03 — Enhancement 2: Full Stack Flex

### Added
- Dark/light theme toggle via `next-themes`
- Date range picker with `react-day-picker` + `@radix-ui/react-popover`
- Detail page monthly trend charts
- Print report page (`/dashboard/report`) with `@media print` styles
- Mobile swipe-to-close sidebar drawer
- 14 backend tests, E2E theme tests

## [0.4.0] - 2026-03 — The Great Fix

### Fixed
- **10 CRITICAL findings**: Keycloak OIDC auth, RLS enforcement on all layers
- **29 HIGH findings**: dim_site bug, fetch timeout, Docker hardening
- Frontend auth flow, CORS headers, security headers
- See `docs/reports/the-great-fix.md` for full report

## [0.3.0] - 2026-02 — Phase 2: Automation & AI

### Added
- **n8n + Redis**: Docker infrastructure, health check workflow
- **Pipeline Tracking**: `pipeline_runs` table with RLS, pipeline module, 5 API endpoints, 53 tests
- **Webhook Execution**: Executor module, 4 API endpoints, n8n full pipeline workflow
- **File Watcher**: watchdog-based directory monitor with debounce and auto-trigger
- **Quality Gates**: `quality_checks` table with RLS, 7 check functions, 79 tests
- **Notifications**: 4 n8n sub-workflows (Slack success/failure/digest/global error)
- **Pipeline Dashboard**: `/pipeline` page, 5 components, 3 SWR hooks, E2E tests
- **AI-Light**: OpenRouter client, anomaly detection, AI narratives, `/insights` page

## [0.2.0] - 2026-01 — Phase 1.5: Dashboard

### Added
- **Next.js 14** project with TypeScript, Tailwind CSS, App Router
- **6 Dashboard Pages**: Executive overview, Products, Customers, Staff, Sites, Returns
- **Components**: KPI cards, trend charts, ranking tables, filter bar
- **Data Fetching**: 9 SWR hooks, API client with Decimal parsing
- **Theme**: midnight-pharma dark mode color tokens
- **Infrastructure**: Docker multi-stage build, error boundary, loading skeletons
- **E2E Tests**: 18 Playwright specs across 5 files

## [0.1.0] - 2025-12 — Phase 1: Data Pipeline

### Added
- **Bronze Layer**: Excel/CSV ingestion via Polars + PyArrow into PostgreSQL (1.1M rows)
- **Silver Layer**: dbt staging models with cleaning, deduplication, normalization (7 tests)
- **Gold Layer**: Star schema — 6 dimensions, 1 fact table, 8 aggregation models (~40 tests)
- **FastAPI API**: 10 analytics endpoints with parameterized SQL queries
- **Power BI**: 99 DAX measures with calculation groups
- **Security**: Tenant-scoped RLS, SQL injection prevention, CORS
- **Testing**: 95%+ Python coverage
- **Docker**: 5-service compose setup
- **Migrations**: 7 SQL migrations with schema versioning
