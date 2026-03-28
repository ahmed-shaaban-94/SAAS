# DataPulse — Phase 1 Plan (MVP)

> Business/Sales Analytics Platform
> Architecture: Medallion (Bronze -> Silver -> Gold) + Dashboard

---

## Phase 1.1: Foundation [DONE]

**Goal**: Python environment, Docker infrastructure, and import pipeline ready.

### Completed
- [x] Python 3.12 project with pyproject.toml (polars, pyarrow, sqlalchemy, dbt, structlog)
- [x] Docker Compose: PostgreSQL 16 + Python app + pgAdmin + JupyterLab
- [x] Pydantic Settings config (`src/datapulse/config.py`)
- [x] structlog logging setup
- [x] Generic file reader (`import_pipeline/reader.py`) — CSV + Excel via Polars
- [x] Type detector (`import_pipeline/type_detector.py`) — auto-detect column types
- [x] File validator (`import_pipeline/validator.py`) — size + format checks
- [x] Pydantic models for ImportConfig, ImportResult, ColumnInfo
- [x] Unit tests for reader and type detector
- [x] dbt project initialized with profiles.yml

### Deliverable
Docker environment running with PostgreSQL, import pipeline reads CSV/Excel into Polars DataFrames.

---

## Phase 1.2: Bronze Layer — Data Import [DONE]

**Goal**: Load raw Excel sales data into PostgreSQL bronze schema.

### Completed
- [x] SQL migration: `001_create_bronze_schema.sql` — bronze schema + typed sales table with indexes
- [x] Column mapping: Excel headers -> snake_case DB columns (46 columns)
- [x] Bronze loader pipeline: Excel -> Polars concat -> Parquet -> PostgreSQL
- [x] CLI entry point: `python -m datapulse.bronze.loader --source <dir>`
- [x] Parquet archival: 272 MB Excel -> 57 MB Parquet (snappy compression)
- [x] Batch insert: 50K rows per batch with progress logging
- [x] dbt source definition for bronze.sales
- [x] dbt base model: bronze_sales.sql
- [x] Data loaded: 1,134,799 rows (Q1.2023–Q4.2025, 12 quarterly files)

### Deliverable
All sales data loaded in `bronze.sales` typed table. Parquet archive saved for backup.

---

## Phase 1.3: Silver Layer — Data Cleaning [DONE]

**Goal**: Clean and standardize bronze data via dbt models.

### Completed
- [x] Created `dbt/models/staging/stg_sales.sql` — silver layer view with full cleaning
- [x] Created `dbt/models/staging/_staging__sources.yml` — column descriptions
- [x] Dropped 19 columns (billing_document, fi_document_no, crm_order, knumv, item_no, mat_group, mat_group_short, cosm_mg, dis_tax, tax, kzwi1, add_dis, certification, assignment, ref_return_date, ref_return, sales_not_tax, paid, net_sales)
- [x] Renamed 22 columns to business-friendly names (e.g. material -> drug_code, gross_sales -> sales)
- [x] Deduplication by (reference_no, date, material, customer, site, quantity)
- [x] NULL handling: 'Unknown' for names, 'Uncategorized' for classifications, 0 for financials
- [x] Masked data cleanup: customer names with `#` patterns -> 'Unknown'
- [x] Billing type standardization: Arabic -> English (Credit, Cash, Delivery, etc.)
- [x] Derived columns: net_amount, invoice_year/month/quarter, is_return, has_insurance
- [x] dbt build passing — view created in public_staging schema
- [x] Normalized drug_status: 12 dirty variants (CANCELLED, CANCELED, trailing NBSP) -> 5 clean values
- [x] Extracted is_temporary flag from -T suffix in drug_status
- [x] Fixed is_return: now catches billing_way returns + negative quantity rows
- [x] Added is_walk_in flag: customer_id = site_code (26% = counter sales)
- [x] Added has_staff flag: 21% rows without staff identified
- [x] Added 6 dbt tests: not_null (invoice_id, invoice_date, billing_way, drug_code), accepted_values (billing_way, drug_status)
- [x] All 7/7 dbt tests passing

### Deliverable
Clean, validated data in silver schema (35 columns from 46, 7 dbt tests passing).

---

## Phase 1.4: Gold Layer — Business Metrics & Analytics [DONE]

**Goal**: Aggregated tables for analytics, Python analytics module, and REST API.

### Completed
- [x] 8 dbt aggregation models: agg_sales_daily, agg_sales_monthly, agg_sales_by_product, agg_sales_by_customer, agg_sales_by_site, agg_sales_by_staff, agg_returns, metrics_summary
- [x] dbt schema YAML with ~40 tests for all aggregation models
- [x] Python analytics module: Pydantic models, SQLAlchemy repository, business service layer
- [x] FastAPI REST API: 10 analytics endpoints + health check
- [x] Docker Compose: added api service (port 8000)
- [x] Test fixtures and unit tests for models, repository, service, and API endpoints

### Deliverable
Business-ready aggregated tables (star schema with 8 agg models), Python analytics layer, and FastAPI API with 10 endpoints.

---

## Phase 1.5: Dashboard & Visualization [DONE]

**Goal**: Interactive web dashboard for sales analytics.

### Completed
- [x] Initialize Next.js 14 project with TypeScript, Tailwind CSS, App Router
- [x] Build API client layer with SWR for data fetching
- [x] Build chart components (Recharts): Area chart, Bar chart, KPI cards
- [x] Build 6 dashboard pages: Executive overview, Products, Customers, Staff, Sites, Returns
- [x] Build filter bar (date presets synced to URL params)
- [x] Dark theme (midnight-pharma color tokens)
- [x] Responsive sidebar navigation
- [x] Error boundary + loading skeletons
- [x] Docker multi-stage build (dev + production)
- [x] Playwright E2E tests (18 specs across 5 files)

### Deliverable
Interactive dashboard with 6 analytics pages, date filters, dark theme, and E2E tests.

---

## Phase 1.6: Polish & Testing [DONE]

**Goal**: Production-ready with comprehensive testing.

### Completed
- [x] Error handling and validation at all boundaries (global exception handler, health 503, ErrorBoundary)
- [x] Unit tests for all Python modules (95%+ coverage)
- [x] dbt tests for all models (~40 tests passing)
- [x] E2E tests for dashboard (Playwright — 18 specs)
- [x] Security audit: CORS, JsonDecimal, RLS, parseDecimals MAX_SAFE_INTEGER guard
- [x] Documentation: CLAUDE.md architecture guide, PLAN.md, CONTRIBUTING.md

### Deliverable
Production-ready MVP with 95%+ test coverage and comprehensive security audit.

---

## Data Summary

| Metric | Value |
|--------|-------|
| Source files | 12 quarterly Excel files (Q1.2023–Q4.2025) |
| Total rows | 1,134,799 |
| Columns | 46 |
| Raw size (Excel) | 272 MB |
| Parquet size | 57 MB |
| Database table | `bronze.sales` (typed, indexed) |

---

## Architecture Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Data architecture | Medallion (bronze/silver/gold) | Clear separation of raw, cleaned, and aggregated data |
| Data processing | Polars + PyArrow | 10x faster than pandas for large datasets |
| Storage format | Parquet (archive) + PostgreSQL (query) | Compressed archive + fast SQL queries |
| Data transform | dbt | SQL-based transforms, testable, documented |
| Bronze storage | Typed table (not JSONB) | 5-10x faster queries, proper indexes, less storage |
| Containerization | Docker Compose | Reproducible environment, isolated services |
| Excel engine | calamine (via fastexcel) | Fastest Excel reader for Polars |

---

## Success Criteria

- [x] Raw sales data loaded into PostgreSQL (1.1M+ rows)
- [x] Parquet archive created (57 MB compressed)
- [x] Docker environment running (PostgreSQL + app + pgAdmin)
- [x] dbt project configured with bronze source
- [x] Silver layer: cleaned data with dbt model passing (30 columns, derived fields)
- [x] Gold layer: aggregated tables with star schema
- [x] Dashboard: interactive charts with filters (6 pages, Recharts, date presets)
- [x] Test coverage: 95%+ on Python modules
- [x] All dbt tests passing (~40 tests)

---

## Phase 2: Automation & AI [DONE]

**Goal**: Pipeline automation, quality gates, notifications, file watcher, AI insights.

### Completed
- [x] **2.0**: Infra prep — api volumes, deps, config, CORS
- [x] **2.1**: n8n + Redis Docker infrastructure, health check workflow
- [x] **2.2**: Pipeline status tracking — pipeline_runs table + RLS, pipeline module (models/repo/service), 5 API endpoints, 53 tests
- [x] **2.3**: Webhook trigger & pipeline execution — executor module, 4 API endpoints, n8n workflow, 15 tests
- [x] **2.5**: Data quality gates — quality_checks table + RLS, quality module, 2 API endpoints, 7 check functions, 79 tests
- [x] **2.6**: Notifications — 4 n8n sub-workflows (success/failure/digest/global error), Slack webhook
- [x] **2.7**: Pipeline dashboard — /pipeline page, 5 components, 3 SWR hooks, E2E tests
- [x] **2.4**: File watcher — watchdog-based directory monitor, debounce logic, auto-triggers pipeline, Docker service
- [x] **2.8**: AI-Light — OpenRouter client, AILightService, 4 API endpoints, statistical anomaly detection + AI, /insights page, n8n daily digest

### Deliverable
Fully automated pipeline with quality gates, Slack notifications, file watcher, and AI-powered insights.

---

## Phase 4: Public Website & Landing Page [DONE]

**Goal**: Modern, conversion-optimized landing page for DataPulse SaaS platform.
**Detailed plan**: See [PHASE4_PLAN.md](./PHASE4_PLAN.md)

### Completed
- [x] Route group restructure: `(marketing)` + `(app)` separation
- [x] Marketing layout (navbar + footer, no sidebar)
- [x] Responsive navbar with anchor scroll links + mobile hamburger
- [x] Hero section: headline, CTAs, CSS-only dashboard mockup
- [x] Footer: 4 columns + copyright
- [x] Extended Tailwind tokens (gradients, glow effects)
- [x] Move all dashboard routes under `(app)/`
- [x] Features grid: 6 cards with icons (Import, Cleaning, Quality, Analytics, AI, Automation)
- [x] Pipeline visualization: 4 connected steps (Import -> Clean -> Analyze -> Visualize)
- [x] Intersection observer hook for scroll animations
- [x] Responsive: 1->2->3 column grid
- [x] Stats banner: 4 animated count-up metrics
- [x] 3 pricing cards (Starter/Pro/Enterprise), Pro highlighted
- [x] FAQ accordion (8 questions)
- [x] Tech stack badges (Next.js, PostgreSQL, dbt, Polars, FastAPI, Docker, n8n, Recharts)
- [x] Waitlist email form (idle -> loading -> success -> error states)
- [x] Next.js API route for email collection with rate limiting
- [x] Privacy policy page
- [x] Terms of service page
- [x] CTA section before footer
- [x] Meta tags + Open Graph + Twitter cards
- [x] JSON-LD structured data (Organization, WebSite, FAQPage)
- [x] Sitemap.xml + robots.txt
- [x] OG image generation (edge runtime)
- [x] Performance: Server Components first, system fonts, zero images
- [x] Playwright E2E tests (12 marketing specs + 6 SEO specs)
- [x] Accessibility: skip-to-content link, ARIA attributes, keyboard nav, reduced motion
- [x] Mobile viewport project in Playwright (iPhone 13)
- [x] Updated existing E2E tests for route group changes

### Deliverable
Modern landing page with hero, features, pricing, FAQ, waitlist, legal pages, full SEO, and 18 E2E tests. Zero new dependencies, zero images (CSS-only visuals).

### Architecture
```
src/app/
  layout.tsx              ← Minimal: html + body + metadata only
  (marketing)/            ← Public: navbar + footer
    layout.tsx
    page.tsx              ← Landing page (/)
    privacy/page.tsx
    terms/page.tsx
  (app)/                  ← Dashboard: sidebar layout
    layout.tsx
    dashboard/page.tsx
    products/page.tsx
    ...8 route directories
```

### Key Numbers
- 31 new files, 9 modified files, 8 moved directories
- 0 new npm dependencies
- 0 images (CSS-only visuals)
- 12-15 E2E test specs
