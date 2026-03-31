# DataPulse - Architecture Flowchart

## 1. High-Level System Architecture

```mermaid
flowchart TB
    subgraph CLIENTS["Clients"]
        BROWSER["Browser<br/>Next.js Dashboard :3000"]
        POWERBI["Power BI Desktop<br/>99 DAX Measures"]
    end

    subgraph INFRA["Infrastructure (Docker Compose)"]
        subgraph AUTH["Authentication"]
            KEYCLOAK["Keycloak :8080<br/>OAuth2 / OIDC"]
        end

        subgraph API_LAYER["API Layer"]
            FASTAPI["FastAPI :8000<br/>REST API"]
        end

        subgraph AUTOMATION["Automation"]
            N8N["n8n :5678<br/>Workflow Engine"]
            REDIS["Redis<br/>Cache / Queue"]
        end

        subgraph DATA["Data Layer"]
            POSTGRES[("PostgreSQL 16 :5432<br/>Medallion Architecture")]
            PGADMIN["pgAdmin :5050"]
        end

        subgraph PROCESSING["Processing"]
            APP["Python App :8888<br/>JupyterLab + Loader"]
            DBT["dbt-core<br/>Transform Engine"]
        end
    end

    BROWSER -->|"HTTP + JWT"| FASTAPI
    BROWSER -->|"OIDC Login"| KEYCLOAK
    POWERBI -->|"Direct SQL"| POSTGRES
    FASTAPI -->|"SQLAlchemy"| POSTGRES
    FASTAPI -->|"JWT Verify"| KEYCLOAK
    N8N -->|"Webhook Trigger"| FASTAPI
    N8N --- REDIS
    APP -->|"Load Raw Data"| POSTGRES
    DBT -->|"Transform"| POSTGRES
    PGADMIN -->|"Admin"| POSTGRES

    style CLIENTS fill:#1e293b,stroke:#38bdf8,color:#f8fafc
    style INFRA fill:#0f172a,stroke:#6366f1,color:#f8fafc
    style AUTH fill:#1e1b4b,stroke:#818cf8,color:#f8fafc
    style API_LAYER fill:#1e293b,stroke:#22d3ee,color:#f8fafc
    style AUTOMATION fill:#1e293b,stroke:#f59e0b,color:#f8fafc
    style DATA fill:#1e293b,stroke:#10b981,color:#f8fafc
    style PROCESSING fill:#1e293b,stroke:#f472b6,color:#f8fafc
```

## 2. Medallion Data Pipeline (Bronze -> Silver -> Gold)

```mermaid
flowchart LR
    subgraph SOURCE["Data Source"]
        EXCEL["Excel / CSV Files<br/>Raw Sales Data"]
    end

    subgraph BRONZE["Bronze Layer (Raw)"]
        LOADER["Python Loader<br/>Polars + PyArrow"]
        PARQUET["Parquet Files"]
        BRONZE_DB[("bronze.sales<br/>2.2M rows<br/>47 columns")]
    end

    subgraph SILVER["Silver Layer (Clean)"]
        DBT_STG["dbt: stg_sales<br/>Dedup + Clean"]
        SILVER_DB[("public_staging.stg_sales<br/>~1.1M rows<br/>35 columns")]
    end

    subgraph GOLD["Gold Layer (Business)"]
        DBT_MARTS["dbt: Marts Models"]
        subgraph DIMS["Dimensions"]
            DIM_DATE["dim_date (1,096)"]
            DIM_BILLING["dim_billing (11)"]
            DIM_CUSTOMER["dim_customer (24,801)"]
            DIM_PRODUCT["dim_product (17,803)"]
            DIM_SITE["dim_site (2)"]
            DIM_STAFF["dim_staff (1,226)"]
        end
        subgraph FACTS["Facts"]
            FCT_SALES["fct_sales<br/>1.1M rows"]
        end
        subgraph AGGS["Aggregations"]
            AGG_DAILY["agg_sales_daily"]
            AGG_MONTHLY["agg_sales_monthly"]
            AGG_PRODUCT["agg_sales_by_product"]
            AGG_CUSTOMER["agg_sales_by_customer"]
            AGG_SITE["agg_sales_by_site"]
            AGG_STAFF["agg_sales_by_staff"]
            AGG_RETURNS["agg_returns"]
            METRICS["metrics_summary"]
        end
    end

    EXCEL -->|"fastexcel"| LOADER
    LOADER -->|"Write"| PARQUET
    LOADER -->|"INSERT batch 50K"| BRONZE_DB
    BRONZE_DB -->|"dbt run"| DBT_STG
    DBT_STG --> SILVER_DB
    SILVER_DB -->|"dbt run"| DBT_MARTS
    DBT_MARTS --> DIMS
    DBT_MARTS --> FACTS
    DBT_MARTS --> AGGS
    DIMS --> FCT_SALES
    FCT_SALES --> AGGS

    style SOURCE fill:#92400e,stroke:#f59e0b,color:#fef3c7
    style BRONZE fill:#7c2d12,stroke:#fb923c,color:#fff7ed
    style SILVER fill:#1e3a5f,stroke:#60a5fa,color:#eff6ff
    style GOLD fill:#14532d,stroke:#4ade80,color:#f0fdf4
```

## 3. API Request Flow

```mermaid
flowchart TD
    CLIENT["Browser / Client"] -->|"HTTP Request"| CORS["CORS Middleware"]
    CORS --> RATE["Rate Limiter<br/>60/min analytics<br/>5/min mutations"]
    RATE --> JWT["JWT Validation<br/>(Keycloak Token)"]
    JWT --> ROUTER{"Router"}

    ROUTER -->|"/health"| HEALTH["Health Check<br/>DB connectivity"]
    ROUTER -->|"/api/v1/analytics/*"| ANALYTICS["Analytics Routes<br/>10 endpoints"]
    ROUTER -->|"/api/v1/pipeline/*"| PIPELINE["Pipeline Routes<br/>11 endpoints"]

    ANALYTICS --> ANALYTICS_SVC["Analytics Service"]
    ANALYTICS_SVC --> ANALYTICS_REPO["Analytics Repository<br/>Read-only queries"]
    ANALYTICS_REPO -->|"SET LOCAL app.tenant_id"| RLS["RLS Filter"]
    RLS --> MARTS_DB[("Marts Schema<br/>Gold Layer")]

    PIPELINE --> PIPELINE_SVC["Pipeline Service"]
    PIPELINE_SVC --> PIPELINE_REPO["Pipeline Repository"]
    PIPELINE_SVC --> EXECUTOR["Pipeline Executor<br/>Bronze + dbt"]
    PIPELINE_SVC --> QUALITY["Quality Service<br/>7 Check Functions"]
    PIPELINE_REPO --> PIPELINE_DB[("pipeline_runs")]
    QUALITY --> QUALITY_DB[("quality_checks")]

    style CLIENT fill:#1e293b,stroke:#38bdf8,color:#f8fafc
    style ROUTER fill:#312e81,stroke:#818cf8,color:#f8fafc
    style MARTS_DB fill:#14532d,stroke:#4ade80,color:#f0fdf4
```

## 4. Frontend Architecture

```mermaid
flowchart TD
    subgraph NEXTJS["Next.js 14 App"]
        LAYOUT["Root Layout<br/>Sidebar + Providers"]

        subgraph PAGES["Pages"]
            DASH["/dashboard<br/>Executive Overview"]
            PROD["/products<br/>Product Analytics"]
            CUST["/customers<br/>Customer Intelligence"]
            STAFF_P["/staff<br/>Staff Performance"]
            SITES["/sites<br/>Site Comparison"]
            RET["/returns<br/>Returns Analysis"]
            PIPE_P["/pipeline<br/>Pipeline Dashboard"]
            REPORT["/dashboard/report<br/>Print Report"]
        end

        subgraph HOOKS["SWR Hooks (9)"]
            H_SUMMARY["use-summary"]
            H_DAILY["use-daily-trend"]
            H_MONTHLY["use-monthly-trend"]
            H_PRODUCTS["use-top-products"]
            H_CUSTOMERS["use-top-customers"]
            H_STAFF["use-top-staff"]
            H_SITES["use-sites"]
            H_RETURNS["use-returns"]
            H_HEALTH["use-health"]
        end

        CONTEXT["Filter Context<br/>URL Params Sync"]
        API_CLIENT["API Client<br/>fetchAPI + Decimal"]
        THEME["Theme Provider<br/>Dark / Light"]
    end

    LAYOUT --> PAGES
    PAGES --> HOOKS
    HOOKS --> API_CLIENT
    API_CLIENT -->|"HTTP GET"| FASTAPI_EXT["FastAPI :8000"]
    CONTEXT -.->|"date_from, date_to"| HOOKS
    LAYOUT --> THEME

    style NEXTJS fill:#0f172a,stroke:#6366f1,color:#f8fafc
    style PAGES fill:#1e1b4b,stroke:#818cf8,color:#f8fafc
    style HOOKS fill:#1e293b,stroke:#22d3ee,color:#f8fafc
```

## 5. n8n Automation Workflows

```mermaid
flowchart TD
    subgraph TRIGGERS["Triggers"]
        WEBHOOK["Webhook<br/>POST /pipeline/trigger"]
        CRON["Cron<br/>Daily 18:00"]
        HEALTH_CRON["Cron<br/>Every 5 min"]
    end

    subgraph PIPELINE_FLOW["Full Pipeline Workflow"]
        BRONZE_STEP["Bronze Load"]
        QC1["Quality Check 1"]
        STAGING_STEP["dbt Staging"]
        QC2["Quality Check 2"]
        MARTS_STEP["dbt Marts"]
        QC3["Quality Check 3"]
    end

    subgraph NOTIFICATIONS["Notifications (Slack)"]
        SUCCESS["Success Message"]
        FAILURE["Failure Alert<br/>@channel"]
        DIGEST["Quality Digest"]
        GLOBAL_ERR["Global Error Handler"]
    end

    WEBHOOK --> BRONZE_STEP
    BRONZE_STEP --> QC1
    QC1 -->|"Pass"| STAGING_STEP
    QC1 -->|"Fail"| FAILURE
    STAGING_STEP --> QC2
    QC2 -->|"Pass"| MARTS_STEP
    QC2 -->|"Fail"| FAILURE
    MARTS_STEP --> QC3
    QC3 -->|"Pass"| SUCCESS
    QC3 -->|"Fail"| FAILURE

    HEALTH_CRON --> HEALTH_CHECK["API Health Check"]
    HEALTH_CHECK -->|"Down"| FAILURE

    CRON --> DIGEST

    PIPELINE_FLOW -.->|"Unhandled Error"| GLOBAL_ERR

    style TRIGGERS fill:#92400e,stroke:#f59e0b,color:#fef3c7
    style PIPELINE_FLOW fill:#1e293b,stroke:#38bdf8,color:#f8fafc
    style NOTIFICATIONS fill:#1e3a5f,stroke:#60a5fa,color:#eff6ff
```

## 6. Security Architecture

```mermaid
flowchart TD
    USER["User"] -->|"Login"| KEYCLOAK_AUTH["Keycloak OIDC<br/>demo-admin / demo-viewer"]
    KEYCLOAK_AUTH -->|"JWT Token"| FRONTEND_AUTH["NextAuth<br/>Session Management"]
    FRONTEND_AUTH -->|"Authorization Header"| API_AUTH["FastAPI JWT Middleware"]

    API_AUTH -->|"Extract tenant_id"| TENANT["SET LOCAL app.tenant_id"]
    TENANT --> RLS_POLICY["Row Level Security<br/>All Tables"]

    subgraph SECURITY["Security Controls"]
        CORS_SEC["CORS<br/>localhost:3000 only"]
        HEADERS["Security Headers<br/>X-Frame-Options<br/>X-Content-Type-Options"]
        RATE_SEC["Rate Limiting<br/>60/min read, 5/min write"]
        SQL_SAFE["SQL Column Whitelist<br/>Injection Prevention"]
        NUMERIC["NUMERIC(18,4)<br/>Financial Precision"]
        DOCKER_SEC["Docker<br/>127.0.0.1 binding"]
    end

    style USER fill:#1e293b,stroke:#38bdf8,color:#f8fafc
    style SECURITY fill:#450a0a,stroke:#ef4444,color:#fef2f2
    style RLS_POLICY fill:#14532d,stroke:#4ade80,color:#f0fdf4
```

## 7. Quality Gate Flow

```mermaid
flowchart LR
    STAGE["Pipeline Stage<br/>Complete"] --> RUN_CHECKS["Run Quality Checks"]

    RUN_CHECKS --> CHECK1["row_count<br/>Min rows threshold"]
    RUN_CHECKS --> CHECK2["null_rate<br/>Max null % per column"]
    RUN_CHECKS --> CHECK3["schema_drift<br/>Expected vs actual columns"]
    RUN_CHECKS --> CHECK4["duplicate_check<br/>Unique key violations"]
    RUN_CHECKS --> CHECK5["value_range<br/>Min/Max bounds"]
    RUN_CHECKS --> CHECK6["freshness<br/>Data recency"]
    RUN_CHECKS --> CHECK7["referential<br/>FK integrity"]

    CHECK1 & CHECK2 & CHECK3 & CHECK4 & CHECK5 & CHECK6 & CHECK7 --> GATE{"Quality Gate"}

    GATE -->|"All Pass"| NEXT["Next Stage"]
    GATE -->|"Any Fail"| ALERT["Alert + Stop Pipeline"]

    style STAGE fill:#1e293b,stroke:#38bdf8,color:#f8fafc
    style GATE fill:#312e81,stroke:#818cf8,color:#f8fafc
    style NEXT fill:#14532d,stroke:#4ade80,color:#f0fdf4
    style ALERT fill:#7f1d1d,stroke:#ef4444,color:#fef2f2
```
