<p align="center">
  <img src="https://img.shields.io/badge/DataPulse-Sales%20Analytics%20Platform-0d9488?style=for-the-badge&labelColor=0f172a" alt="DataPulse" />
</p>

<h1 align="center">DataPulse</h1>
<p align="center">
  <strong>Enterprise Sales Analytics Platform</strong><br/>
  Import &rarr; Clean &rarr; Analyze &rarr; Visualize
</p>

<p align="center">
  <a href="https://github.com/ahmed-shaaban-94/SAAS/actions/workflows/ci.yml"><img src="https://github.com/ahmed-shaaban-94/SAAS/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://github.com/ahmed-shaaban-94/SAAS/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License"></a>
  <img src="https://img.shields.io/badge/python-3.12-3776ab.svg?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/PostgreSQL-16-336791.svg?logo=postgresql&logoColor=white" alt="PostgreSQL">
  <img src="https://img.shields.io/badge/Next.js-14-000000.svg?logo=next.js&logoColor=white" alt="Next.js">
  <img src="https://img.shields.io/badge/dbt-1.8-ff694b.svg?logo=dbt&logoColor=white" alt="dbt">
  <img src="https://img.shields.io/badge/FastAPI-0.111-009688.svg?logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/coverage-95%25-brightgreen.svg" alt="Coverage">
  <img src="https://img.shields.io/badge/Docker-8%20services-2496ed.svg?logo=docker&logoColor=white" alt="Docker">
</p>

---

## Overview

DataPulse is a full-stack data analytics platform that transforms raw sales data into actionable business intelligence. Built on the **medallion architecture** (Bronze / Silver / Gold), it processes 1.1M+ sales transactions through a structured pipeline with automated quality gates, AI-powered insights, and interactive dashboards.

```
 Excel/CSV Files (12 quarterly, 272 MB)
          |
     Polars + PyArrow
          |
     +----+----+
     |         |
     v         v
  Parquet   PostgreSQL 16
  (57 MB)   bronze.sales (1.1M rows)
               |
          dbt transforms
               |
      +--------+--------+
      |                  |
      v                  v
   Silver             Gold
   (cleaned)          (aggregated)
      |                  |
      |         +--------+--------+--------+
      |         |        |        |        |
      |         v        v        v        v
      |      FastAPI  Next.js  Power BI  AI Insights
      |      REST API Dashboard 99 DAX   OpenRouter
      |         |        |
      +----+----+--------+
           |
        Analytics
```

## Quick Start

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [Git](https://git-scm.com/)

### Setup

```bash
# Clone the repository
git clone https://github.com/ahmed-shaaban-94/SAAS.git
cd SAAS

# Configure environment
cp .env.example .env
# Edit .env with your passwords (see comments in file)

# Launch all services
make up
```

### Load Data & Build Pipeline

```bash
# Import raw sales data (Bronze layer)
make load

# Run dbt transforms (Silver + Gold layers)
make dbt

# Or run everything at once
make demo
```

## Services

| Service | URL | Description |
|---------|-----|-------------|
| **Dashboard** | [`localhost:3000`](http://localhost:3000) | Next.js interactive analytics dashboard |
| **Landing Page** | [`localhost:3000`](http://localhost:3000) | Marketing website with pricing & waitlist |
| **API** | [`localhost:8000/docs`](http://localhost:8000/docs) | FastAPI with Swagger documentation |
| **Keycloak** | [`localhost:8080`](http://localhost:8080) | Authentication & SSO (OAuth2/OIDC) |
| **n8n** | [`localhost:5678`](http://localhost:5678) | Workflow automation engine |
| **pgAdmin** | [`localhost:5050`](http://localhost:5050) | Database admin interface |
| **PostgreSQL** | `localhost:5432` | Database (internal) |
| **Redis** | `localhost:6379` | Cache (internal) |

## Architecture

### Medallion Data Pipeline

| Layer | Schema | Purpose | Technology |
|-------|--------|---------|------------|
| **Bronze** | `bronze` | Raw data as-is from source | Polars + PyArrow + fastexcel |
| **Silver** | `public_staging` | Cleaned, deduplicated, type-cast | dbt staging models (7 tests) |
| **Gold** | `public_marts` | Aggregated, business-ready metrics | dbt marts models (~40 tests) |

### Gold Layer Schema

```
dim_date ─────────┐
dim_billing ──────┤
dim_customer ─────┤
dim_product ──────┼──── fct_sales (1.1M rows) ──── 8 aggregation tables
dim_site ─────────┤                                  ├── agg_sales_daily
dim_staff ────────┘                                  ├── agg_sales_monthly
                                                     ├── agg_sales_by_product
                                                     ├── agg_sales_by_customer
                                                     ├── agg_sales_by_site
                                                     ├── agg_sales_by_staff
                                                     ├── agg_returns
                                                     └── metrics_summary
```

### Tech Stack

| Layer | Technology |
|-------|-----------|
| **Data Processing** | Polars + PyArrow + fastexcel (calamine) |
| **Database** | PostgreSQL 16 with tenant-scoped RLS |
| **Transforms** | dbt-core + dbt-postgres |
| **Backend API** | FastAPI + SQLAlchemy 2.0 + Pydantic |
| **Frontend** | Next.js 14 + TypeScript + Tailwind CSS |
| **Charts** | Recharts |
| **Auth** | Keycloak (OAuth2/OIDC) + NextAuth + PyJWT |
| **Automation** | n8n (6 workflows) + watchdog file watcher |
| **AI Insights** | OpenRouter + statistical anomaly detection |
| **BI** | Power BI Desktop (99 DAX measures) |
| **Notifications** | Slack webhooks (success/failure/digest) |
| **Containers** | Docker Compose (8 services) |
| **Reverse Proxy** | Traefik (production) |
| **CI/CD** | GitHub Actions (CI + staging + production deploy) |
| **Logging** | structlog (structured JSON) |
| **Config** | Pydantic Settings |

## Project Structure

```
.
├── src/datapulse/               # Python backend
│   ├── config.py                #   Pydantic settings
│   ├── logging.py               #   structlog configuration
│   ├── bronze/                  #   Raw data ingestion (Excel -> PostgreSQL)
│   ├── import_pipeline/         #   Generic CSV/Excel reader + type detection
│   ├── analytics/               #   Business logic (models, repository, service)
│   ├── pipeline/                #   Pipeline tracking + execution + quality gates
│   └── api/                     #   FastAPI REST API (25+ endpoints)
│       └── routes/              #     health, analytics, pipeline
│
├── frontend/                    # Next.js 14 dashboard + marketing site
│   ├── src/app/
│   │   ├── (marketing)/         #   Landing page, pricing, legal
│   │   └── (app)/               #   Dashboard (8 analytics pages)
│   ├── src/components/          #   UI components (layout, charts, filters)
│   ├── src/hooks/               #   9 SWR data hooks
│   └── e2e/                     #   Playwright E2E tests (36+ specs)
│
├── dbt/                         # dbt transforms
│   └── models/
│       ├── bronze/              #   Source definitions
│       ├── staging/             #   Silver layer (cleaned, 7 tests)
│       └── marts/               #   Gold layer (dims + facts + aggs, ~40 tests)
│
├── android/                     # Android app (Kotlin + Jetpack Compose)
│
├── migrations/                  # SQL migrations (7 files)
├── n8n/workflows/               # n8n workflow definitions (6 workflows)
├── keycloak/                    # Keycloak realm configuration
├── traefik/                     # Traefik reverse proxy config
├── powerbi/                     # Power BI report + theme
├── tests/                       # Python unit tests (95%+ coverage)
├── scripts/                     # Utility scripts
│
├── docs/                        # Documentation
│   ├── plans/                   #   Phase plans (organized by topic)
│   ├── reports/                 #   Project reports & reviews
│   └── archive/                 #   Historical planning documents
│
├── docker-compose.yml           # Development environment (8 services)
├── docker-compose.prod.yml      # Production environment
├── Makefile                     # Developer commands
└── pyproject.toml               # Python project configuration
```

## Data

| Metric | Value |
|--------|-------|
| **Source** | 12 quarterly Excel files (Q1 2023 — Q4 2025) |
| **Transactions** | 1,134,799 rows |
| **Columns** | 46 raw → 35 cleaned → star schema |
| **Raw Size** | 272 MB (Excel) → 57 MB (Parquet) |
| **Dimensions** | Product (17.8K), Customer (24.8K), Staff (1.2K), Site (2), Billing (11), Date (1,096) |

## API Endpoints

### Analytics (`/api/v1/analytics/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/summary` | KPI summary (revenue, orders, customers, AOV) |
| GET | `/trends/daily` | Daily sales trend |
| GET | `/trends/monthly` | Monthly sales with MoM/YoY growth |
| GET | `/products/top` | Top products by revenue |
| GET | `/customers/top` | Top customers by revenue |
| GET | `/staff/top` | Top staff by revenue |
| GET | `/sites` | Site comparison |
| GET | `/returns` | Return analysis |
| GET | `/products/{id}` | Product detail with trend |
| GET | `/customers/{id}` | Customer detail with trend |

### Pipeline (`/api/v1/pipeline/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/trigger` | Trigger full pipeline run |
| POST | `/execute/bronze` | Execute bronze stage |
| POST | `/execute/staging` | Execute dbt staging |
| POST | `/execute/marts` | Execute dbt marts |
| GET | `/runs` | List pipeline runs |
| GET | `/runs/{id}` | Get run details |
| GET | `/quality` | Get quality check results |
| POST | `/quality-check` | Run quality checks |

### AI Insights (`/api/v1/insights/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/anomalies` | Detect statistical anomalies |
| GET | `/summary` | AI-generated narrative summary |
| GET | `/trends` | AI trend analysis |
| GET | `/recommendations` | AI business recommendations |

## Development

```bash
# Start services
make up                  # Build and start all services
make dev                 # Start + print access URLs
make status              # Show service health

# Testing
make test                # Python tests with coverage
make test-e2e            # Playwright E2E tests
make dbt-test            # dbt model tests

# Code quality
make lint                # Ruff linter
make fmt                 # Ruff formatter

# Data pipeline
make load                # Import raw Excel/CSV data
make dbt                 # Run dbt build (staging + marts)
make pipeline            # Trigger full pipeline via API

# Cleanup
make clean               # Stop services, remove volumes
```

## Security

- **Authentication**: Keycloak OIDC with JWT validation
- **Authorization**: Tenant-scoped Row Level Security (RLS) on all data layers
- **API Security**: Rate limiting (60/min analytics, 5/min mutations), CORS whitelist
- **Data Protection**: SQL column whitelist, `NUMERIC(18,4)` for financials
- **Headers**: X-Content-Type-Options, X-Frame-Options, Referrer-Policy
- **Secrets**: All credentials via `.env` (never hardcoded)
- **Network**: Docker ports bound to `127.0.0.1` only

See [SECURITY.md](./SECURITY.md) for vulnerability reporting.

## Project Status

| Phase | Status | Description |
|-------|--------|-------------|
| **1.1** Foundation | :white_check_mark: Done | Docker, Python env, import pipeline |
| **1.2** Bronze Layer | :white_check_mark: Done | 1.1M rows loaded into PostgreSQL |
| **1.3** Silver Layer | :white_check_mark: Done | Cleaned, normalized, 7 dbt tests |
| **1.4** Gold Layer | :white_check_mark: Done | Star schema, 6 dims + 1 fact + 8 aggs, FastAPI API |
| **1.5** Dashboard | :white_check_mark: Done | Next.js 14, 6 pages, Recharts, SWR, E2E tests |
| **1.6** Polish | :white_check_mark: Done | Security audit, 95%+ coverage, error handling |
| **2.0** Infra Prep | :white_check_mark: Done | API volumes, deps, CORS |
| **2.1** n8n Infrastructure | :white_check_mark: Done | n8n + Redis Docker services |
| **2.2** Pipeline Tracking | :white_check_mark: Done | pipeline_runs table, 5 API endpoints, 53 tests |
| **2.3** Webhook Execution | :white_check_mark: Done | Executor module, 4 API endpoints, n8n workflow |
| **2.4** File Watcher | :white_check_mark: Done | watchdog auto-trigger on new files |
| **2.5** Quality Gates | :white_check_mark: Done | 7 quality checks, 79 tests |
| **2.6** Notifications | :white_check_mark: Done | 4 Slack workflows (success/failure/digest/error) |
| **2.7** Pipeline Dashboard | :white_check_mark: Done | /pipeline page, 5 components, E2E tests |
| **2.8** AI-Light | :white_check_mark: Done | OpenRouter insights, anomaly detection, /insights page |
| **4.0** Public Website | :white_check_mark: Done | Landing page, pricing, SEO, waitlist, 18 E2E tests |
| **The Great Fix** | :white_check_mark: Done | 10 CRITICAL + 29 HIGH findings resolved |
| **Enhancement 2** | :white_check_mark: Done | Dark/light theme, date picker, print report, mobile |

> See [docs/plans/](./docs/plans/) for detailed phase breakdowns and implementation guides.

## Documentation

| Document | Description |
|----------|-------------|
| [docs/plans/](./docs/plans/) | Phase plans organized by topic (data pipeline, automation, website, validation) |
| [CLAUDE.md](./CLAUDE.md) | Full technical reference (architecture, tables, conventions) |
| [CONTRIBUTING.md](./CONTRIBUTING.md) | Development setup and code standards |
| [SECURITY.md](./SECURITY.md) | Security policy and vulnerability reporting |
| [CHANGELOG.md](./CHANGELOG.md) | Version history |
| [docs/reports/](./docs/reports/) | Project reviews, audits, and post-mortems |

## License

This project is licensed under the MIT License — see [LICENSE](./LICENSE) for details.

---

<p align="center">
  <sub>Built by <a href="https://github.com/ahmed-shaaban-94">Ahmed Shaaban</a></sub>
</p>
