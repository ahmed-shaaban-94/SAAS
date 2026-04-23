<p align="center">
  <img src="https://img.shields.io/badge/DataPulse-Sales%20Analytics%20Platform-0d9488?style=for-the-badge&labelColor=0f172a&logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0id2hpdGUiPjxwYXRoIGQ9Ik0zIDEzaDJ2LTJIM3Yyem0wIDRoMnYtMkgzdjJ6bTAtOGgyVjdIM3Yyem00IDRoMTR2LTJIN3Yyem0wIDRoMTR2LTJINnYyem0wLThoMTRWN0g3djJ6Ii8+PC9zdmc+" alt="DataPulse" />
</p>

<h1 align="center">
  <img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=700&size=35&pause=1000&color=0D9488&center=true&vCenter=true&width=500&lines=DataPulse;Sales+Analytics+Platform;Medallion+Architecture;AI-Powered+Insights" alt="Typing SVG" />
</h1>

<p align="center">
  <strong>Enterprise Sales Analytics Platform</strong><br/>
  <em>Import &rarr; Clean &rarr; Analyze &rarr; Visualize</em>
</p>

<p align="center">
  <a href="https://github.com/ahmed-shaaban-94/Data-Pulse/actions/workflows/ci.yml"><img src="https://github.com/ahmed-shaaban-94/Data-Pulse/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://github.com/ahmed-shaaban-94/Data-Pulse/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg?style=flat-square" alt="License"></a>
  <img src="https://img.shields.io/badge/coverage-79%25-green.svg?style=flat-square" alt="Coverage">
  <img src="https://img.shields.io/badge/tests-1,342-blue.svg?style=flat-square" alt="Tests">
  <img src="https://img.shields.io/badge/API_endpoints-100+-orange.svg?style=flat-square" alt="API Endpoints">
  <img src="https://img.shields.io/badge/transactions-1.1M+-purple.svg?style=flat-square" alt="Transactions">
</p>

---

## <img src="https://img.shields.io/badge/-Tech%20Stack-0f172a?style=for-the-badge" alt="Tech Stack" />

<p align="center">
  <a href="https://skillicons.dev">
    <img src="https://skillicons.dev/icons?i=python,fastapi,postgres,nextjs,ts,tailwind,docker,redis,nginx,github&theme=dark" alt="Tech Stack" />
  </a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/FastAPI-0.111-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/PostgreSQL-16-336791?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL" />
  <img src="https://img.shields.io/badge/Next.js-15-000000?style=for-the-badge&logo=next.js&logoColor=white" alt="Next.js" />
  <img src="https://img.shields.io/badge/TypeScript-5.x-3178C6?style=for-the-badge&logo=typescript&logoColor=white" alt="TypeScript" />
  <img src="https://img.shields.io/badge/dbt-1.8-FF694B?style=for-the-badge&logo=dbt&logoColor=white" alt="dbt" />
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Polars-DataFrame-CD792C?style=for-the-badge&logo=polars&logoColor=white" alt="Polars" />
  <img src="https://img.shields.io/badge/SQLAlchemy-2.0-D71F00?style=for-the-badge&logo=sqlalchemy&logoColor=white" alt="SQLAlchemy" />
  <img src="https://img.shields.io/badge/Tailwind_CSS-3.x-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white" alt="Tailwind" />
  <img src="https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker" />
  <img src="https://img.shields.io/badge/Redis-Cache-DC382D?style=for-the-badge&logo=redis&logoColor=white" alt="Redis" />
  <img src="https://img.shields.io/badge/Clerk-OIDC-6C47FF?style=for-the-badge&logo=clerk&logoColor=white" alt="Clerk" />
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Recharts-Viz-22B5BF?style=for-the-badge" alt="Recharts" />
  <img src="https://img.shields.io/badge/Power_BI-99_DAX-F2C811?style=for-the-badge&logo=powerbi&logoColor=black" alt="Power BI" />
  <img src="https://img.shields.io/badge/OpenRouter-AI-7C3AED?style=for-the-badge" alt="OpenRouter" />
  <img src="https://img.shields.io/badge/Playwright-E2E-45BA4B?style=for-the-badge&logo=playwright&logoColor=white" alt="Playwright" />
  <img src="https://img.shields.io/badge/GitHub_Actions-CI/CD-2088FF?style=for-the-badge&logo=githubactions&logoColor=white" alt="GitHub Actions" />
  <img src="https://img.shields.io/badge/Nginx-Proxy-009639?style=for-the-badge&logo=nginx&logoColor=white" alt="Nginx" />
</p>

---

## <img src="https://img.shields.io/badge/-Overview-0d9488?style=for-the-badge" alt="Overview" />

DataPulse is a full-stack data analytics platform that transforms raw sales data into actionable business intelligence. Built on the **medallion architecture** (Bronze / Silver / Gold), it processes **1.1M+ sales transactions** through a structured pipeline with automated quality gates, AI-powered insights, anomaly detection, forecasting, and interactive dashboards.

### Data Pipeline Flow

```mermaid
flowchart LR
    subgraph INPUT["<b>Data Sources</b>"]
        A["Excel/CSV Files<br/>12 quarterly | 272 MB"]
    end

    subgraph BRONZE["<b>Bronze Layer</b>"]
        B["Raw Ingestion<br/>Polars + PyArrow"]
        C[("PostgreSQL<br/>1.1M rows")]
        D["Parquet<br/>57 MB"]
    end

    subgraph SILVER["<b>Silver Layer</b>"]
        E["dbt Staging<br/>Cleaned + Deduped"]
    end

    subgraph GOLD["<b>Gold Layer</b>"]
        F["Star Schema<br/>6 dims + 1 fact"]
        G["8 Aggregations<br/>+ metrics_summary"]
    end

    subgraph OUTPUT["<b>Consumers</b>"]
        H["FastAPI<br/>100 endpoints"]
        I["Next.js<br/>22 pages"]
        J["Power BI<br/>99 DAX measures"]
        K["AI Insights<br/>OpenRouter"]
    end

    A --> B
    B --> C
    B --> D
    C --> E
    E --> F
    F --> G
    G --> H
    G --> I
    G --> J
    G --> K

    style INPUT fill:#1e293b,stroke:#475569,color:#e2e8f0
    style BRONZE fill:#92400e,stroke:#b45309,color:#fef3c7
    style SILVER fill:#1e40af,stroke:#3b82f6,color:#dbeafe
    style GOLD fill:#166534,stroke:#22c55e,color:#dcfce7
    style OUTPUT fill:#581c87,stroke:#a855f7,color:#f3e8ff
```

### System Architecture

```mermaid
flowchart TB
    subgraph CLIENT["<b>Client Layer</b>"]
        WEB["Next.js Dashboard<br/>22 pages | 49 hooks"]
        MOBILE["Android App<br/>Kotlin + Compose"]
        PBI["Power BI Desktop<br/>99 DAX measures"]
    end

    subgraph API_LAYER["<b>API Layer</b>"]
        FASTAPI["FastAPI<br/>~100 endpoints | 20 route modules"]
        AUTH["Clerk OIDC<br/>JWT + API Key"]
        RATE["Rate Limiter<br/>60/min read | 5/min write"]
        CACHE["Redis Cache"]
    end

    subgraph BACKEND["<b>Backend Modules</b>"]
        ANALYTICS["Analytics<br/>queries + service"]
        PIPELINE["Pipeline<br/>executor + quality"]
        AI["AI Light<br/>OpenRouter"]
        ANOMALY["Anomalies<br/>detection + alerts"]
        FORECAST["Forecasting<br/>time-series"]
        BILLING["Billing<br/>Stripe"]
        EXPLORE["Explore<br/>SQL builder"]
        TARGETS["Targets<br/>goal tracking"]
    end

    subgraph DATA["<b>Data Layer</b>"]
        PG[("PostgreSQL 16<br/>RLS + 3 schemas")]
        DBT["dbt<br/>staging + marts"]
    end

    WEB --> FASTAPI
    MOBILE --> FASTAPI
    FASTAPI --> AUTH
    FASTAPI --> RATE
    FASTAPI --> CACHE
    FASTAPI --> ANALYTICS
    FASTAPI --> PIPELINE
    FASTAPI --> AI
    FASTAPI --> ANOMALY
    FASTAPI --> FORECAST
    FASTAPI --> BILLING
    FASTAPI --> EXPLORE
    FASTAPI --> TARGETS
    ANALYTICS --> PG
    PIPELINE --> PG
    PIPELINE --> DBT
    DBT --> PG
    PBI --> PG

    style CLIENT fill:#1e293b,stroke:#475569,color:#e2e8f0
    style API_LAYER fill:#0f766e,stroke:#14b8a6,color:#ccfbf1
    style BACKEND fill:#1e40af,stroke:#3b82f6,color:#dbeafe
    style DATA fill:#166534,stroke:#22c55e,color:#dcfce7
```

---

## <img src="https://img.shields.io/badge/-Quick%20Start-22c55e?style=for-the-badge" alt="Quick Start" />

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) <img src="https://img.shields.io/badge/-required-red?style=flat-square" />
- [Git](https://git-scm.com/) <img src="https://img.shields.io/badge/-required-red?style=flat-square" />

### Setup

```bash
# Clone the repository
git clone https://github.com/ahmed-shaaban-94/Data-Pulse.git
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

---

## <img src="https://img.shields.io/badge/-Services-3b82f6?style=for-the-badge" alt="Services" />

| Service | URL | Description |
|:--------|:----|:------------|
| <img src="https://img.shields.io/badge/-Dashboard-000000?style=flat-square&logo=next.js&logoColor=white" /> | [`localhost:3000`](http://localhost:3000) | Interactive analytics dashboard |
| <img src="https://img.shields.io/badge/-API-009688?style=flat-square&logo=fastapi&logoColor=white" /> | [`localhost:8000/docs`](http://localhost:8000/docs) | FastAPI with Swagger docs |
| <img src="https://img.shields.io/badge/-Auth-6C47FF?style=flat-square&logo=clerk&logoColor=white" /> | Clerk (managed) | Authentication & SSO |
| <img src="https://img.shields.io/badge/-PostgreSQL-336791?style=flat-square&logo=postgresql&logoColor=white" /> | `localhost:5432` | Database (internal) |
| <img src="https://img.shields.io/badge/-Redis-DC382D?style=flat-square&logo=redis&logoColor=white" /> | internal | Cache layer |

---

## <img src="https://img.shields.io/badge/-Architecture-7c3aed?style=for-the-badge" alt="Architecture" />

### Medallion Data Pipeline

| Layer | Schema | Purpose | Technology |
|:------|:-------|:--------|:-----------|
| <img src="https://img.shields.io/badge/-Bronze-B45309?style=flat-square" /> | `bronze` | Raw data as-is from source | Polars + PyArrow + fastexcel |
| <img src="https://img.shields.io/badge/-Silver-3B82F6?style=flat-square" /> | `public_staging` | Cleaned, deduplicated, type-cast | dbt staging models (7 tests) |
| <img src="https://img.shields.io/badge/-Gold-22C55E?style=flat-square" /> | `public_marts` | Aggregated, business-ready | dbt marts models (~40 tests) |

### Gold Layer Schema

```mermaid
erDiagram
    dim_date ||--o{ fct_sales : "date_key"
    dim_billing ||--o{ fct_sales : "billing_key"
    dim_customer ||--o{ fct_sales : "customer_key"
    dim_product ||--o{ fct_sales : "product_key"
    dim_site ||--o{ fct_sales : "site_key"
    dim_staff ||--o{ fct_sales : "staff_key"

    fct_sales {
        bigint id PK
        int date_key FK
        int billing_key FK
        int customer_key FK
        int product_key FK
        int site_key FK
        int staff_key FK
        numeric revenue
        numeric cost
        numeric profit
        int quantity
    }

    dim_date {
        int date_key PK
        date full_date
        int year
        int month
        int quarter
    }

    dim_customer {
        int customer_key PK
        varchar customer_name
        varchar segment
    }

    dim_product {
        int product_key PK
        varchar product_name
        varchar category
    }
```

### Tech Stack Details

| Layer | Technology | Role |
|:------|:-----------|:-----|
| <img src="https://img.shields.io/badge/-Data-CD792C?style=flat-square" /> | Polars + PyArrow + fastexcel | High-performance data processing |
| <img src="https://img.shields.io/badge/-DB-336791?style=flat-square" /> | PostgreSQL 16 + RLS | Tenant-scoped relational storage |
| <img src="https://img.shields.io/badge/-Transform-FF694B?style=flat-square" /> | dbt-core + dbt-postgres | SQL-first data transformation |
| <img src="https://img.shields.io/badge/-API-009688?style=flat-square" /> | FastAPI + SQLAlchemy 2.0 + Pydantic | REST API with validation |
| <img src="https://img.shields.io/badge/-Frontend-000000?style=flat-square" /> | Next.js 15 + TypeScript + Tailwind | Server-rendered dashboard |
| <img src="https://img.shields.io/badge/-Charts-22B5BF?style=flat-square" /> | Recharts | Interactive data visualization |
| <img src="https://img.shields.io/badge/-Auth-6C47FF?style=flat-square" /> | Clerk + PyJWT | OAuth2/OIDC authentication |
| <img src="https://img.shields.io/badge/-AI-7C3AED?style=flat-square" /> | OpenRouter + anomaly detection | AI insights and forecasting |
| <img src="https://img.shields.io/badge/-BI-F2C811?style=flat-square" /> | Power BI (99 DAX measures) | Advanced business intelligence |
| <img src="https://img.shields.io/badge/-Cache-DC382D?style=flat-square" /> | Redis | Response caching layer |
| <img src="https://img.shields.io/badge/-CI/CD-2088FF?style=flat-square" /> | GitHub Actions | Automated testing and deployment |
| <img src="https://img.shields.io/badge/-Proxy-009639?style=flat-square" /> | Nginx + Cloudflare TLS | Production reverse proxy |

---

## <img src="https://img.shields.io/badge/-Project%20Structure-f59e0b?style=for-the-badge" alt="Structure" />

```
.
├── src/datapulse/               # Python backend (135 files, 20+ modules)
│   ├── config.py                #   Pydantic settings
│   ├── logging.py               #   structlog configuration
│   ├── cache.py                 #   Redis caching layer
│   ├── bronze/                  #   Raw data ingestion (Excel -> PostgreSQL)
│   ├── import_pipeline/         #   Generic CSV/Excel reader + type detection
│   ├── analytics/               #   Core analytics (models, repository, service)
│   ├── pipeline/                #   Pipeline tracking + execution + quality gates
│   ├── ai_light/                #   AI insights via OpenRouter
│   ├── anomalies/               #   Statistical anomaly detection + calendar
│   ├── forecasting/             #   Time-series forecasting engine
│   ├── billing/                 #   Stripe subscriptions + usage metering
│   ├── targets/                 #   Goal tracking + target management
│   ├── explore/                 #   Self-service data exploration (SQL builder)
│   ├── reports/                 #   Custom report generation
│   ├── annotations/             #   Data annotations + notes
│   ├── notifications_center/    #   In-app notification system
│   ├── onboarding/              #   User onboarding flow
│   ├── views/                   #   Saved views + user preferences
│   ├── embed/                   #   Embeddable dashboard tokens
│   ├── watcher/                 #   File watcher (auto-trigger pipeline)
│   ├── tasks/                   #   Background task management
│   ├── core/                    #   Shared: config, db, security
│   └── api/                     #   FastAPI REST API
│       └── routes/              #     20 route files (~100 endpoints)
│
├── frontend/                    # Next.js 15 dashboard + marketing site
│   ├── src/app/
│   │   ├── (marketing)/         #   Landing page, pricing, legal
│   │   └── (app)/               #   Dashboard (14 analytics pages)
│   ├── src/components/          #   32 UI component directories
│   ├── src/hooks/               #   53 SWR data hooks
│   └── e2e/                     #   Playwright E2E tests (11 spec files)
│
├── dbt/models/                  # dbt transforms
│   ├── bronze/                  #   Source definitions
│   ├── staging/                 #   Silver layer (cleaned, 7 tests)
│   └── marts/                   #   Gold layer (dims + facts + aggs, ~40 tests)
│
├── android/                     # Android app (Kotlin + Jetpack Compose)
├── migrations/                  # SQL migrations (22 files)
├── n8n/workflows/               # n8n workflow definitions (7 workflows)
├── nginx/                       # Nginx reverse proxy config
├── powerbi/                     # Power BI report + theme
├── tests/                       # Python unit tests (98 files, 1,342 functions)
├── docs/                        # Architecture, plans, reports
│
├── docker-compose.yml           # Development (7 services)
├── docker-compose.prod.yml      # Production
├── Makefile                     # Developer commands
└── pyproject.toml               # Python project config
```

---

## <img src="https://img.shields.io/badge/-Data-cd792c?style=for-the-badge" alt="Data" />

| Metric | Value |
|:-------|:------|
| **Source** | 12 quarterly Excel files (Q1 2023 -- Q4 2025) |
| **Transactions** | <img src="https://img.shields.io/badge/1,134,799-rows-blue?style=flat-square" /> |
| **Columns** | 46 raw -> 35 cleaned -> star schema |
| **Raw Size** | 272 MB (Excel) -> 57 MB (Parquet) |
| **Dimensions** | Product (17.8K), Customer (24.8K), Staff (1.2K), Site (2), Billing (11), Date (1,096) |

---

## <img src="https://img.shields.io/badge/-API%20Endpoints-009688?style=for-the-badge" alt="API" />

The API exposes **~100 endpoints** across **20 route modules**:

<details>
<summary><b>Analytics</b> <code>/api/v1/analytics/</code> -- Core business metrics</summary>

| Method | Endpoint | Description |
|:-------|:---------|:------------|
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

</details>

<details>
<summary><b>Pipeline</b> <code>/api/v1/pipeline/</code> -- Data pipeline operations</summary>

| Method | Endpoint | Description |
|:-------|:---------|:------------|
| POST | `/trigger` | Trigger full pipeline run |
| POST | `/execute/bronze` | Execute bronze stage |
| POST | `/execute/staging` | Execute dbt staging |
| POST | `/execute/marts` | Execute dbt marts |
| GET | `/runs` | List pipeline runs |
| GET | `/runs/{id}` | Get run details |
| GET | `/quality` | Get quality check results |
| POST | `/quality-check` | Run quality checks |

</details>

<details>
<summary><b>AI Insights</b> <code>/api/v1/insights/</code> -- AI-powered analysis</summary>

| Method | Endpoint | Description |
|:-------|:---------|:------------|
| GET | `/anomalies` | Detect statistical anomalies |
| GET | `/summary` | AI-generated narrative summary |
| GET | `/trends` | AI trend analysis |
| GET | `/recommendations` | AI business recommendations |

</details>

<details>
<summary><b>Additional Modules</b> -- 15+ more route groups</summary>

| Route Group | Description |
|:------------|:------------|
| `/api/v1/anomalies/` | Anomaly detection with calendar-aware alerting |
| `/api/v1/forecasting/` | Time-series forecasting |
| `/api/v1/targets/` | Goal tracking and target management |
| `/api/v1/explore/` | Self-service data exploration |
| `/api/v1/reports/` | Custom report generation |
| `/api/v1/billing/` | Stripe subscription management |
| `/api/v1/annotations/` | Data annotations and notes |
| `/api/v1/notifications/` | In-app notification center |
| `/api/v1/onboarding/` | User onboarding flow |
| `/api/v1/views/` | Saved views and preferences |
| `/api/v1/search/` | Global search across entities |
| `/api/v1/embed/` | Embeddable dashboard tokens |
| `/api/v1/export/` | Data export (CSV, Excel) |
| `/api/v1/dashboard-layouts/` | Custom dashboard layouts |
| `/api/v1/queries/` | Saved SQL queries |

</details>

---

## <img src="https://img.shields.io/badge/-Dashboard%20Pages-000000?style=for-the-badge&logo=next.js&logoColor=white" alt="Dashboard" />

| Page | Path | Description |
|:-----|:-----|:------------|
| **Dashboard** | `/dashboard` | KPI overview with sparklines and comparison |
| **Products** | `/products` | Product analytics with hierarchy drill-down |
| **Customers** | `/customers` | Customer analytics with health scores |
| **Staff** | `/staff` | Staff performance metrics |
| **Sites** | `/sites` | Site comparison and breakdown |
| **Returns** | `/returns` | Return analysis and trends |
| **Pipeline** | `/pipeline` | Pipeline monitoring and run history |
| **Insights** | `/insights` | AI-powered insights and anomalies |
| **Alerts** | `/alerts` | Anomaly alerts and notifications |
| **Goals** | `/goals` | Target tracking and goal management |
| **Reports** | `/reports` | Custom report builder |
| **Custom Report** | `/custom-report` | Ad-hoc report generation |
| **Billing** | `/billing` | Subscription management |
| **Landing Page** | `/` | Marketing site with pricing and waitlist |

---

## <img src="https://img.shields.io/badge/-Development-22c55e?style=for-the-badge" alt="Dev" />

```bash
# Start services
make up                  # Build and start all services
make dev                 # Start + print access URLs
make status              # Show service health

# Testing
make test                # Python tests with coverage (~79% unit, gated at 77%)
make test-e2e            # Playwright E2E tests
make dbt-test            # dbt model tests

# Code quality
make lint                # Ruff linter
make fmt                 # Ruff formatter

# Data pipeline
make load                # Import raw Excel/CSV data
make dbt                 # Run dbt build (staging + marts)
make pipeline            # Trigger full pipeline via API

# Database
make backup              # Backup PostgreSQL database
make restore             # Restore from backup

# Cleanup
make clean               # Stop services, remove volumes
```

---

## <img src="https://img.shields.io/badge/-CI/CD-2088FF?style=for-the-badge&logo=githubactions&logoColor=white" alt="CI/CD" />

| Workflow | Trigger | Jobs |
|:---------|:--------|:-----|
| <img src="https://img.shields.io/badge/-CI-2088FF?style=flat-square" /> | Push/PR to `main` | Lint, Type Check, Test (95%+ coverage gate) |
| <img src="https://img.shields.io/badge/-Security-red?style=flat-square" /> | Scheduled | Dependency vulnerability scanning |
| <img src="https://img.shields.io/badge/-Staging-orange?style=flat-square" /> | Manual | Deploy to staging environment |
| <img src="https://img.shields.io/badge/-Production-green?style=flat-square" /> | Manual | Deploy to production |
| <img src="https://img.shields.io/badge/-Dependabot-blue?style=flat-square" /> | Dependabot PR | Auto-merge minor/patch updates |

---

## <img src="https://img.shields.io/badge/-Security-dc2626?style=for-the-badge" alt="Security" />

- **Authentication**: Clerk OIDC with JWT validation (multi-strategy: Bearer JWT + API Key + dev fallback)
- **Authorization**: Tenant-scoped Row Level Security (RLS) on all data layers
- **API Security**: Rate limiting (60/min analytics, 5/min mutations), CORS whitelist
- **Data Protection**: SQL column whitelist, `NUMERIC(18,4)` for financials
- **Headers**: X-Content-Type-Options, X-Frame-Options, Referrer-Policy
- **Secrets**: All credentials via `.env` (never hardcoded)
- **Network**: Docker ports bound to `127.0.0.1` only

See [SECURITY.md](./SECURITY.md) for vulnerability reporting.

---

## <img src="https://img.shields.io/badge/-Project%20Status-7c3aed?style=for-the-badge" alt="Status" />

| Phase | Status | Description |
|:------|:------:|:------------|
| **1.1** Foundation | ![Done](https://img.shields.io/badge/-Done-22c55e?style=flat-square) | Docker, Python env, import pipeline |
| **1.2** Bronze Layer | ![Done](https://img.shields.io/badge/-Done-22c55e?style=flat-square) | 1.1M rows loaded into PostgreSQL |
| **1.3** Silver Layer | ![Done](https://img.shields.io/badge/-Done-22c55e?style=flat-square) | Cleaned, normalized, 7 dbt tests |
| **1.4** Gold Layer | ![Done](https://img.shields.io/badge/-Done-22c55e?style=flat-square) | Star schema, 6 dims + 1 fact + 8 aggs |
| **1.5** Dashboard | ![Done](https://img.shields.io/badge/-Done-22c55e?style=flat-square) | Next.js 15, 22 pages, Recharts, E2E |
| **1.6** Polish | ![Done](https://img.shields.io/badge/-Done-22c55e?style=flat-square) | Security audit, 95%+ coverage |
| **2.0-2.7** Automation | ![Done](https://img.shields.io/badge/-Done-22c55e?style=flat-square) | n8n, pipeline tracking, quality gates |
| **2.8** AI-Light | ![Done](https://img.shields.io/badge/-Done-22c55e?style=flat-square) | OpenRouter insights, anomaly detection |
| **3.0** Enhancements | ![Done](https://img.shields.io/badge/-Done-22c55e?style=flat-square) | Theme, date picker, print, mobile |
| **4.0** Public Website | ![Done](https://img.shields.io/badge/-Done-22c55e?style=flat-square) | Landing page, pricing, SEO, waitlist |
| **The Great Fix** | ![Done](https://img.shields.io/badge/-Done-22c55e?style=flat-square) | 10 CRITICAL + 29 HIGH resolved |
| **Enh. 2-3** | ![Done](https://img.shields.io/badge/-Done-22c55e?style=flat-square) | Comparison, i18n, sparklines, search |

### Roadmap

| Phase | Description |
|:------|:------------|
| **5** ![Planned](https://img.shields.io/badge/-Planned-6366f1?style=flat-square) | Multi-tenancy & Billing -- Stripe subscriptions, usage metering |
| **6** ![Planned](https://img.shields.io/badge/-Planned-6366f1?style=flat-square) | Data Connectors -- Google Sheets, MySQL/SQL Server, Shopify |
| **7** ![Planned](https://img.shields.io/badge/-Planned-6366f1?style=flat-square) | Self-Service Analytics -- dashboard builder, scheduled reports |
| **8** ![Planned](https://img.shields.io/badge/-Planned-6366f1?style=flat-square) | AI & Intelligence -- NL queries (AR/EN), forecasting, ML |
| **9** ![Planned](https://img.shields.io/badge/-Planned-6366f1?style=flat-square) | Collaboration & Teams -- comments, sharing, workspaces |
| **10** ![Planned](https://img.shields.io/badge/-Planned-6366f1?style=flat-square) | Scale & Infra -- S3/MinIO, Celery, Kubernetes, Prometheus |

---

## <img src="https://img.shields.io/badge/-Stats-0f172a?style=for-the-badge" alt="Stats" />

<p align="center">

| Metric | Count |
|:-------|------:|
| Python source files | 135 |
| Backend modules | 20+ |
| API endpoints | ~100 |
| Frontend pages | 14 |
| SWR hooks | 53 |
| UI components | 32 dirs |
| SQL migrations | 22 |
| Test files | 98 |
| Test functions | 1,342 |
| Code coverage (unit) | ~79% (gated 77%) |
| dbt models | 16 |
| dbt tests | ~47 |
| E2E specs | 11 |
| DAX measures | 99 |

</p>

---

## <img src="https://img.shields.io/badge/-Documentation-0ea5e9?style=for-the-badge" alt="Docs" />

| Document | Description |
|:---------|:------------|
| [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) | System architecture with Mermaid diagrams |
| [docs/plans/](./docs/plans/) | Phase plans organized by topic |
| [docs/reports/](./docs/reports/) | Project reviews, audits, and post-mortems |
| [CLAUDE.md](./CLAUDE.md) | Full technical reference |
| [CONTRIBUTING.md](./CONTRIBUTING.md) | Development setup and code standards |
| [SECURITY.md](./SECURITY.md) | Security policy and vulnerability reporting |
| [CHANGELOG.md](./CHANGELOG.md) | Version history |

---

## License

This project is licensed under the MIT License -- see [LICENSE](./LICENSE) for details.

---

<p align="center">
  <sub>Built by <a href="https://github.com/ahmed-shaaban-94">Ahmed Shaaban</a></sub>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Made%20with-Python%20%7C%20TypeScript%20%7C%20SQL%20%7C%20DAX-0d9488?style=for-the-badge&labelColor=0f172a" alt="Made with" />
</p>
