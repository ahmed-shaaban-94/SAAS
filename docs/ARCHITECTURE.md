# DataPulse — System Architecture

## High-Level Overview

```mermaid
graph TB
    subgraph External
        CLERK[Clerk OIDC]
        OPENROUTER[OpenRouter AI]
        SLACK[Slack Webhooks]
    end

    subgraph "Docker Network: frontend-net"
        FE[Next.js Frontend<br/>:3000]
        API[FastAPI API<br/>:8000]
    end

    subgraph "Docker Network: backend"
        API
        PG[(PostgreSQL 16<br/>:5432)]
        REDIS[(Redis 7<br/>Cache + Broker)]
        CELERY[Celery Worker<br/>Async Queries]
        N8N[n8n Workflows<br/>:5678]
    end

    USER((User)) --> FE
    FE -->|Next.js rewrites| API
    API --> PG
    API --> REDIS
    API --> CLERK
    API --> OPENROUTER
    CELERY --> REDIS
    CELERY --> PG
    N8N --> API
    N8N --> PG
    N8N --> SLACK
```

## Data Flow

```mermaid
flowchart LR
    FILES[Excel/CSV Files] --> BRONZE[Bronze Loader<br/>Polars + PyArrow]
    BRONZE --> PARQUET[Parquet Files]
    BRONZE --> BT[(bronze.sales<br/>2.27M rows)]
    BT --> DBT_STG[dbt Staging<br/>stg_sales view]
    DBT_STG --> ST[(public_staging<br/>1.1M rows)]
    ST --> DBT_MARTS[dbt Marts]
    DBT_MARTS --> DIMS[(6 Dimensions)]
    DBT_MARTS --> FACT[(fct_sales<br/>1.13M rows)]
    DBT_MARTS --> AGGS[(8 Aggregations)]
    AGGS --> CACHE[(Redis Cache<br/>300-600s TTL)]
    CACHE --> API_LAYER[FastAPI<br/>84 Endpoints]
    API_LAYER --> FRONTEND[Next.js<br/>26 Pages]
```

## Request Flow (API Call)

```mermaid
sequenceDiagram
    participant Browser
    participant NextJS as Next.js (SSR)
    participant FastAPI
    participant Clerk
    participant Redis
    participant PostgreSQL

    Browser->>NextJS: GET /dashboard
    NextJS->>Browser: HTML (SSR shell)
    Browser->>NextJS: GET /api/v1/analytics/dashboard
    NextJS->>FastAPI: Proxy (INTERNAL_API_URL)
    FastAPI->>Clerk: Verify JWT (JWKS cache)
    Clerk-->>FastAPI: Valid claims
    FastAPI->>FastAPI: SET LOCAL app.tenant_id
    FastAPI->>Redis: Cache lookup
    alt Cache hit
        Redis-->>FastAPI: Cached data
    else Cache miss
        FastAPI->>PostgreSQL: SQL query (RLS filtered)
        PostgreSQL-->>FastAPI: Results
        FastAPI->>Redis: Store (TTL 600s)
    end
    FastAPI-->>NextJS: JSON response
    NextJS-->>Browser: JSON (SWR updates UI)
```

## Database Schema (ERD)

```mermaid
erDiagram
    BRONZE_SALES {
        text reference_no
        date date
        text material
        text customer
        numeric net_sales
        text tenant_id
    }

    DIM_DATE {
        int date_key PK
        date full_date
        int year_num
        int month_num
        int quarter_num
    }

    DIM_CUSTOMER {
        int customer_key PK
        text customer_name
        text tenant_id
    }

    DIM_PRODUCT {
        int product_key PK
        text drug_code
        text brand
        text category
        text tenant_id
    }

    DIM_SITE {
        int site_key PK
        text site_name
        text area_manager
        text tenant_id
    }

    DIM_STAFF {
        int staff_key PK
        text person_name
        text position
        text tenant_id
    }

    DIM_BILLING {
        int billing_key PK
        text billing_type
        text billing_group
    }

    FCT_SALES {
        int date_key FK
        int customer_key FK
        int product_key FK
        int site_key FK
        int staff_key FK
        int billing_key FK
        numeric quantity
        numeric gross_amount
        numeric discount
        numeric net_amount
        text tenant_id
    }

    FCT_SALES }o--|| DIM_DATE : date_key
    FCT_SALES }o--|| DIM_CUSTOMER : customer_key
    FCT_SALES }o--|| DIM_PRODUCT : product_key
    FCT_SALES }o--|| DIM_SITE : site_key
    FCT_SALES }o--|| DIM_STAFF : staff_key
    FCT_SALES }o--|| DIM_BILLING : billing_key

    AGG_SALES_MONTHLY ||--|| DIM_DATE : "year, month"
    AGG_SALES_BY_PRODUCT ||--|| DIM_PRODUCT : product_key
    AGG_SALES_BY_CUSTOMER ||--|| DIM_CUSTOMER : customer_key
    METRICS_SUMMARY ||--|| DIM_DATE : date_key
```

## Module Dependency Map

```mermaid
graph TB
    subgraph "API Layer"
        APP[app.py<br/>Factory + Middleware]
        AUTH[auth.py + jwt.py<br/>Authentication]
        DEPS[deps.py<br/>Dependency Injection]
        ROUTES[13 Route Files<br/>84 Endpoints]
    end

    subgraph "Business Logic"
        ANALYTICS[Analytics<br/>7 Repos + Service]
        FORECAST[Forecasting<br/>3 Methods + Service]
        AI[AI-Light<br/>OpenRouter + Service]
        TARGETS[Targets<br/>Alerts + Service]
        EXPLORE[Explore<br/>SQL Builder + Catalog]
    end

    subgraph "Data Pipeline"
        BRONZE[Bronze Loader<br/>Polars + Parquet]
        PIPELINE[Pipeline<br/>Executor + Quality]
        DBT[dbt Models<br/>Staging + Marts]
    end

    subgraph "Infrastructure"
        CACHE[Redis Cache<br/>Graceful Degradation]
        CELERY_MOD[Celery Tasks<br/>Async Queries]
        CONFIG[Config<br/>Pydantic Settings]
        DB[Core DB<br/>Engine + Sessions]
    end

    ROUTES --> DEPS --> AUTH
    DEPS --> ANALYTICS & FORECAST & AI & TARGETS & EXPLORE & PIPELINE
    ANALYTICS --> CACHE
    FORECAST --> CACHE
    PIPELINE --> BRONZE & DBT
    PIPELINE -->|invalidate| CACHE
    ANALYTICS --> DB
    CELERY_MOD --> DB & CACHE
    ALL_SERVICES[All Services] --> CONFIG
```

## Deployment Architecture

```mermaid
graph TB
    subgraph "Host Machine"
        NGINX[Nginx Reverse Proxy<br/>:80, :443]
    end

    subgraph "Docker Compose"
        FE[Frontend :3000]
        API[API :8000<br/>4 workers]
        PG[PostgreSQL :5432<br/>2GB RAM]
        REDIS[Redis<br/>256MB RAM]
        CELERY[Celery<br/>4 concurrency]
        N8N[n8n :5678]
    end

    subgraph "External SaaS"
        CF[Cloudflare CDN]
        CLERK[Clerk]
        SENTRY[Sentry]
        OR[OpenRouter]
    end

    CF --> NGINX
    NGINX -->|/_next/static| FE
    NGINX -->|/api/v1/*| API
    NGINX -->|/api/auth/*| FE
    API --> PG & REDIS
    CELERY --> PG & REDIS
    N8N --> API
    API --> CLERK & SENTRY & OR
```

## Security Architecture

### Multi-Tenant Row-Level Security (RLS)

```
JWT Token → tenant_id claim → SET LOCAL app.tenant_id → PostgreSQL RLS Policy
```

Every table with `tenant_id` has:
```sql
ALTER TABLE <table> ENABLE ROW LEVEL SECURITY;
ALTER TABLE <table> FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON <table>
    FOR ALL USING (tenant_id::text = current_setting('app.tenant_id', true));
```

### Auth Flow
1. **Browser** → Clerk login → JWT token (template `datapulse` emits `tenant_id` + `roles`)
2. **Next.js** → `@clerk/nextjs` session → Bearer header
3. **FastAPI** → Verify JWT (JWKS) → Extract tenant_id
4. **PostgreSQL** → `SET LOCAL app.tenant_id` → RLS filters all queries

### API Security Layers
- CORS: restricted origins + headers
- Rate limiting: 5-60 req/min per endpoint
- Security headers: CSP, X-Frame-Options, X-Content-Type-Options
- SQL: parameterized queries only (whitelist for dynamic identifiers)
- Input: Pydantic validation on all inputs
- Errors: sanitized (no stack traces, paths, or connection strings)

## Tech Stack Summary

| Layer | Technology | Version |
|-------|-----------|---------|
| API | FastAPI + Uvicorn | ≥0.111, 4 workers |
| ORM | SQLAlchemy (raw SQL via text()) | 2.0 |
| Validation | Pydantic | ≥2.5 |
| Database | PostgreSQL + RLS | 16 |
| Cache | Redis | 7 |
| Async Tasks | Celery | ≥5.3 |
| Data Pipeline | Polars + PyArrow + dbt | ≥1.0, ≥1.8 |
| Forecasting | statsmodels | ≥0.14 |
| AI | OpenRouter (free tier) | - |
| Auth | Clerk OIDC + PyJWT | - |
| Frontend | Next.js 15 + TypeScript | ^15.3.0 |
| State | SWR + React Context | 2.3.3 |
| Charts | Recharts | 2.15.3 |
| Styling | Tailwind CSS | 3.4.17 |
| Monitoring | Sentry + structlog | ≥2.0 |
| Automation | n8n | 2.13.4 |
| CI | GitHub Actions | 6 jobs |
