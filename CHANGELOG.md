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
- See `docs/reports/The Great Fix.md` for full report

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
