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

## Phase 1.4: Gold Layer — Business Metrics [PLANNED]

**Goal**: Aggregated tables for analytics and dashboards.

### Tasks
- [ ] Create dbt mart models in `dbt/models/marts/`:
  - `fct_sales.sql` — fact table with cleaned sales transactions
  - `dim_product.sql` — product dimension (material, brand, category, subcategory)
  - `dim_customer.sql` — customer dimension (customer, site, buyer)
  - `dim_date.sql` — date dimension (calendar table)
  - `dim_personnel.sql` — personnel dimension
  - `agg_sales_daily.sql` — daily sales aggregation
  - `agg_sales_monthly.sql` — monthly sales aggregation
  - `agg_sales_by_category.sql` — sales by product category
  - `agg_sales_by_site.sql` — sales by site/location
- [ ] Add dbt documentation and tests for all mart models
- [ ] Run `dbt build` and verify gold layer
- [ ] Create Python analysis utilities for ad-hoc queries

### Deliverable
Business-ready aggregated tables. Star schema with facts and dimensions.

---

## Phase 1.5: Dashboard & Visualization [PLANNED]

**Goal**: Interactive web dashboard for sales analytics.

### Tasks
- [ ] Initialize Next.js 14 project with TypeScript, Tailwind CSS, App Router
- [ ] Install and configure shadcn/ui
- [ ] Build API layer connecting to PostgreSQL gold schema
- [ ] Build chart components (Recharts):
  - Bar chart, Line chart, Pie chart, KPI cards
- [ ] Build dashboard grid (react-grid-layout) with drag-and-drop
- [ ] Build filter bar (date range, category, site, brand)
- [ ] Build dashboard CRUD (save/load layouts)
- [ ] Add export: PNG and PDF
- [ ] Add light/dark theme

### Deliverable
Interactive dashboard with multiple chart types, filters, and export.

---

## Phase 1.6: Polish & Testing [PLANNED]

**Goal**: Production-ready with comprehensive testing.

### Tasks
- [ ] Add error handling and validation at all boundaries
- [ ] Write unit tests for all Python modules (80%+ coverage)
- [ ] Write dbt tests for all models
- [ ] Write E2E tests for dashboard (Playwright)
- [ ] Performance testing with full dataset (1.1M rows)
- [ ] Documentation: setup guide, architecture diagram

### Deliverable
Production-ready MVP with comprehensive test coverage.

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
- [ ] Gold layer: aggregated tables with star schema
- [ ] Dashboard: interactive charts with filters
- [ ] Test coverage: 80%+ on Python modules
- [ ] All dbt tests passing
