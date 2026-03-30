# DataPulse API Layer & Infrastructure Exploration Report
## Foundation for Phase 2.2 Pipeline Tracking

**Date**: March 28, 2026  
**Scope**: Complete audit of FastAPI application structure, database design, session management, and existing infrastructure patterns  
**Purpose**: Provide technical blueprint for Phase 2.2 pipeline status tracking implementation  

---

## 1. API Endpoints Inventory

### 1.1 Health Check Endpoint
**File**: `src/datapulse/api/routes/health.py`

| Property | Value |
|----------|-------|
| **Method** | GET |
| **Path** | `/health` |
| **Purpose** | Application and database connectivity status monitoring |
| **Response** | `{status: string, db: string}` |
| **Status Codes** | 200 (healthy), 503 (degraded) |
| **Implementation** | Attempts `SELECT 1` query; returns connected/disconnected based on result |

**Response Examples**:
```json
// Healthy
{"status": "ok", "db": "connected"}

// Degraded
{"status": "degraded", "db": "disconnected"}
```

### 1.2 Analytics Endpoints
**File**: `src/datapulse/api/routes/analytics.py`  
**Base Path**: `/analytics`  
**Pattern**: All endpoints return analytics data filtered by optional date range and dimension filters

#### Common Query Parameters
All analytics endpoints support:
- `start_date` (optional, YYYY-MM-DD): Must be paired with `end_date`
- `end_date` (optional, YYYY-MM-DD): Must be paired with `start_date`
- `category` (optional, string): Product category filter
- `brand` (optional, string): Brand filter
- `site_key` (optional, string): Site identifier
- `staff_key` (optional, string): Staff member identifier
- `limit` (optional, int 1-100, default varies): Results limit

#### Analytics Endpoint Details

| Endpoint | Method | Purpose | Response Model | Status |
|----------|--------|---------|-----------------|--------|
| `/analytics/summary` | GET | KPI snapshot (revenue, orders, customers, returns) | `KPISummary` | ✓ Implemented |
| `/analytics/trends/daily` | GET | Daily revenue trend with growth % | `list[TimeSeriesPoint]` | ✓ Implemented |
| `/analytics/trends/monthly` | GET | Monthly revenue trend with growth % | `list[TimeSeriesPoint]` | ✓ Implemented |
| `/analytics/products/top` | GET | Top products by revenue | `RankingResult` | ✓ Implemented |
| `/analytics/customers/top` | GET | Top customers by spend | `RankingResult` | ✓ Implemented |
| `/analytics/staff/top` | GET | Staff performance leaderboard | `StaffPerformance` | ✓ Implemented |
| `/analytics/sites` | GET | Site comparison (revenue, order count) | `list[ProductPerformance]` | ✓ Implemented |
| `/analytics/returns` | GET | Return analysis (count, rate, value) | `ReturnAnalysis` | ✓ Implemented |
| `/analytics/products/{product_key}` | GET | Product deep-dive (detail not specified) | — | ✗ Not Implemented (501) |
| `/analytics/customers/{customer_key}` | GET | Customer deep-dive (detail not specified) | — | ✗ Not Implemented (501) |

**Filter Validation Logic** (`_to_filter()` helper):
- If `start_date` provided, `end_date` is required (vice versa)
- If neither provided, service applies 30-day default range
- Returns `AnalyticsFilter` model with defaults applied

### 1.3 Route Registration Pattern
**File**: `src/datapulse/api/app.py`

Routers are registered in application factory with prefix:
```python
app.include_router(health_router, prefix="/api", tags=["health"])
app.include_router(analytics_router, prefix="/api", tags=["analytics"])
```

**Resulting API Structure**:
- All endpoints prefixed with `/api`
- Health check: `GET /api/health`
- Analytics routes: `GET /api/analytics/*`

---

## 2. Database Schema Design

### 2.1 Schema Architecture Overview

The database uses a medallion (bronze/silver/gold) architecture with multi-schema design:

```
bronze/        → Raw data (from imports, n8n)
staging/       → Intermediate transformations (dbt views)
public/        → Clean, public schema
marts/         → Analytics layer (dimensions, facts, aggregates)
n8n/           → n8n workflow orchestration objects
schema_migrations/ → Migration tracking
```

### 2.2 Core Bronze Schema
**File**: `migrations/001_create_bronze_schema.sql`

**Table**: `bronze.sales` (1.1M+ rows)

**Purpose**: Immutable raw transaction data; source of truth for all downstream analytics

**Column Structure** (80+ columns organized by domain):

| Domain | Key Columns | Type | Purpose |
|--------|-------------|------|---------|
| **Metadata** | id, source_file, source_quarter, loaded_at | BIGSERIAL, TEXT, CHAR, TIMESTAMPTZ | Row identity and load tracking |
| **Temporal** | date, date_key (YYYYMMDD int) | DATE, INT | Transaction date; int key for fast mart joins |
| **Product** | material, material_desc, category, subcategory, brand | VARCHAR | Product identification and classification |
| **Customer** | customer, customer_name, customer_segment, customer_region | VARCHAR | Customer identification and demographics |
| **Financials** | net_sales, total_costs, gross_profit, quantity, discount_pct | DECIMAL, INT | Revenue, margins, units moved |
| **Personnel** | site, site_name, staff_key, sales_person | VARCHAR | Location and sales attribution |
| **Returns** | return_qty, return_reason, is_return | INT, VARCHAR, BOOLEAN | Return tracking |
| **Operational** | quarter, month_num, days_to_delivery, lead_source | CHAR, INT, VARCHAR | Operational dimensions |

**Indexing Strategy** (8 indexes for query optimization):
- `idx_bronze_sales_date`: Fast temporal filtering
- `idx_bronze_sales_quarter`: Quarterly reports
- `idx_bronze_sales_customer`: Customer-scoped analytics
- `idx_bronze_sales_material`: Product analysis
- `idx_bronze_sales_category`: Category rollups
- `idx_bronze_sales_brand`: Brand performance
- `idx_bronze_sales_site`: Multi-location queries
- `idx_bronze_sales_loaded_at`: Incremental load tracking

### 2.3 Multi-Tenancy & Row Level Security
**Files**: `migrations/002_add_rls_and_roles.sql`, `migrations/003_add_tenant_id.sql`

**Tenant Table**: `bronze.tenants`
```sql
CREATE TABLE bronze.tenants (
    tenant_id INT PRIMARY KEY,
    tenant_name VARCHAR NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
-- Seeds: tenant_id=1 (default)
```

**RLS Implementation**:

1. **Two Database Roles**:
   - `datapulse` (owner): Full access, no RLS restrictions
   - `datapulse_reader` (web frontend): Read-only with RLS filtering

2. **Two RLS Policies on `bronze.sales`**:
   - **owner_all_access**: Allows datapulse role to read all rows (USING (true))
   - **reader_select_access**: Filters datapulse_reader to session variable:
     ```sql
     USING (tenant_id = current_setting('app.tenant_id')::int)
     ```

3. **Tenant Isolation Pattern**:
   - Session variable set before each datapulse_reader query:
     ```sql
     SET LOCAL app.tenant_id = '1';
     SELECT * FROM bronze.sales;  -- Auto-filtered to tenant_id=1
     ```
   - `LOCAL` scopes to transaction only; no connection state pollution
   - Index on `tenant_id` ensures efficient row filtering

**Schema Grants**:
- `datapulse_reader` has SELECT on bronze, public, public_staging, marts schemas
- Enables read-only analytics consumption

### 2.4 n8n Integration Schema
**File**: `migrations/004_create_n8n_schema.sql`

**Purpose**: Dedicated namespace for n8n workflow orchestration

**Structure**:
```sql
CREATE SCHEMA n8n;
GRANT ALL ON SCHEMA n8n TO datapulse;
ALTER DEFAULT PRIVILEGES IN SCHEMA n8n GRANT ALL ON TABLES TO datapulse;
```

**Use Cases**:
- n8n workflow state/execution logs
- Pipeline orchestration artifacts
- Integration with Phase 2.2 pipeline tracking

### 2.5 Schema Migration Tracking
**File**: `migrations/000_create_schema_migrations.sql`

**Table**: `public.schema_migrations`

| Column | Type | Purpose |
|--------|------|---------|
| id | SERIAL | Auto-increment sequence |
| filename | VARCHAR UNIQUE | Migration file identifier |
| applied_at | TIMESTAMPTZ | When migration executed |
| checksum | TEXT | File integrity verification |

**Pattern**: Enables idempotent migration execution; prevents duplicate applies

---

## 3. Session & Tenant Management Architecture

### 3.1 Dependency Injection Container
**File**: `src/datapulse/api/deps.py`

**Pattern**: FastAPI dependency injection using generator functions + global session factory

#### Database Connection Pool
```python
_engine = None  # Global singleton
_session_factory = None  # Global singleton

def _get_engine() -> Engine:
    """Create or return singleton SQLAlchemy engine"""
    global _engine
    if _engine is None:
        _engine = create_engine(
            settings.database_url,
            pool_pre_ping=True,  # Verify connection health before use
            poolclass=NullPool,  # PostgreSQL-recommended pool
        )
    return _engine

def _get_session_factory() -> sessionmaker:
    """Create or return singleton session factory"""
    global _session_factory
    if _session_factory is None:
        engine = _get_engine()
        _session_factory = sessionmaker(bind=engine, class_=Session)
    return _session_factory
```

**Key Features**:
- **pool_pre_ping=True**: Executes `SELECT 1` before using pooled connection; recovers from stale connections
- **Global singletons**: Engine and session factory created once per app lifetime
- **Lazy initialization**: Created on first request, not at startup

#### Session Dependency
```python
def get_db_session() -> Generator[Session, None, None]:
    """Provide SQLAlchemy session to route handlers"""
    session = _session_factory()
    try:
        yield session
    finally:
        session.close()
```

**Pattern**: Generator-based dependency ensures session cleanup via try/finally

#### Service Factory
```python
def get_analytics_service(
    db: Session = Depends(get_db_session)
) -> AnalyticsService:
    """Create analytics service with injected session"""
    repo = AnalyticsRepository(db)
    return AnalyticsService(repo)
```

**Composition**: Repository wraps session; service wraps repository

### 3.2 Session Usage in Route Handlers
**File**: `src/datapulse/api/routes/analytics.py`

```python
@analytics_router.get("/summary")
async def get_summary(
    filter: AnalyticsFilter = Depends(AnalyticsFilter),
    service: AnalyticsService = Depends(get_analytics_service)
) -> KPISummary:
    return service.get_dashboard_summary(filter)
```

**Dependency Resolution**:
1. FastAPI resolves `AnalyticsFilter` from query params
2. FastAPI creates `get_db_session()` generator, yields session
3. Service factory creates `AnalyticsRepository(session)`
4. Service factory creates `AnalyticsService(repo)`
5. Route handler executes with fully-composed service
6. Response returned; session closed in finally block

### 3.3 Tenant-Scoped Session Pattern (Currently Not Implemented)

**Current State**: RLS policies exist but session variables are NOT being set by the application

**Pattern for Future Implementation**:
```python
def get_db_session_with_tenant(
    tenant_id: int,  # From request context/JWT/header
) -> Generator[Session, None, None]:
    session = _session_factory()
    try:
        # Set tenant context for RLS filtering
        session.execute(text("SET LOCAL app.tenant_id = :tenant_id"), {"tenant_id": tenant_id})
        yield session
    finally:
        session.close()
```

**Note**: Phase 2.2 should implement tenant extraction (JWT, header, or session) and pass through deps chain

---

## 4. Application Factory & Middleware Architecture

**File**: `src/datapulse/api/app.py`

### 4.1 Application Factory Pattern
```python
def create_app() -> FastAPI:
    """Create and configure FastAPI application instance"""
    app = FastAPI(
        title="DataPulse API",
        version="0.1.0",
        description="Analytics and pipeline orchestration API"
    )
```

### 4.2 CORS Configuration
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,  # ["http://localhost:3000"]
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["*"],
)
```

**Purpose**: Enable browser-based frontend at localhost:3000 to call backend API

**Methods Allowed**: GET (read), POST (create), PATCH (update); DELETE not exposed

### 4.3 Global Exception Handler
```python
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Log and return formatted error response"""
    logger.exception("Unhandled exception", error=str(exc))
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )
```

**Purpose**: Catch unexpected errors; log with request context; return sanitized response

### 4.4 Request Logging Middleware
```python
@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """Log request/response with timing"""
    start_time = time.time()
    response = await call_next(request)
    elapsed = time.time() - start_time
    logger.info(
        "HTTP request",
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        elapsed_ms=elapsed * 1000,
    )
    return response
```

**Purpose**: Track API performance; identify slow endpoints

### 4.5 Router Registration
```python
app.include_router(health_router, prefix="/api", tags=["health"])
app.include_router(analytics_router, prefix="/api", tags=["analytics"])
```

**Result**: Nested endpoint structure under `/api` namespace

---

## 5. Data Models & Response Types

**File**: `src/datapulse/analytics/models.py`

### 5.1 Model Design Pattern
All response models use Pydantic with frozen=True (immutable):

```python
class DateRange(BaseModel):
    model_config = ConfigDict(frozen=True)
    start_date: date
    end_date: date
```

**Rationale**: Immutable models prevent accidental mutation in response pipeline; match REST semantics of read-only responses

### 5.2 Analytics Filter Model
```python
class AnalyticsFilter(BaseModel):
    model_config = ConfigDict(frozen=True)
    date_range: DateRange | None = None
    site_key: str | None = None
    category: str | None = None
    brand: str | None = None
    staff_key: str | None = None
    limit: int = Field(default=10, ge=1, le=100)
```

**Validation**:
- limit bounded 1-100 via Field validators
- Optional fields allow flexible filtering
- Default limit=10 applied if not specified

### 5.3 Financial Precision Pattern
```python
class JsonDecimal:
    """Serialize Decimal to float for JSON"""
    @staticmethod
    def serialize(value: Decimal | None) -> float | None:
        return float(value) if value else None

class TimeSeriesPoint(BaseModel):
    model_config = ConfigDict(frozen=True)
    date: date
    revenue: Decimal = Field(decimal_places=2)
    growth_pct: float | None = None
    
    @field_serializer("revenue")
    def serialize_revenue(self, value: Decimal):
        return JsonDecimal.serialize(value)
```

**Rationale**: Decimal type preserves financial precision in Python; custom JSON serializer converts to float for REST consumers

### 5.4 Response Models

| Model | Purpose | Key Fields |
|-------|---------|-----------|
| `KPISummary` | Dashboard snapshot | total_revenue, order_count, unique_customers, return_count |
| `TimeSeriesPoint` | Trend data | date, revenue, growth_pct |
| `RankingItem` | Ranked entity | rank, name, value, pct_of_total |
| `RankingResult` | Ranking list | items, generated_at |
| `StaffPerformance` | Leaderboard | staff_key, name, total_sales, rank |
| `ProductPerformance` | Product metrics | product_key, name, revenue, order_count |
| `CustomerAnalytics` | Customer metrics | customer_key, name, total_spend, order_count |
| `ReturnAnalysis` | Return metrics | return_count, return_rate_pct, return_value |

---

## 6. Repository & Service Layer Architecture

### 6.1 Analytics Repository Pattern
**File**: `src/datapulse/analytics/repository.py`

**Purpose**: Read-only data access layer querying marts (gold) schema

#### Query Pattern: Parameterized SQL via SQLAlchemy
```python
def get_kpi_summary(self, filter: AnalyticsFilter) -> KPISummary:
    """Query KPI aggregate from marts.fct_daily_sales"""
    where_clauses = ["1=1"]
    params = {}
    
    if filter.date_range:
        where_clauses.append(
            f"date_key BETWEEN :start_date AND :end_date"
        )
        start_int = int(filter.date_range.start_date.strftime("%Y%m%d"))
        end_int = int(filter.date_range.end_date.strftime("%Y%m%d"))
        params["start_date"] = start_int
        params["end_date"] = end_int
    
    # Additional WHERE clauses for category, brand, site, staff...
    
    query = text(f"""
        SELECT 
            SUM(net_sales) as total_revenue,
            COUNT(DISTINCT order_id) as order_count,
            COUNT(DISTINCT customer_key) as unique_customers,
            SUM(CASE WHEN is_return THEN 1 ELSE 0 END) as return_count
        FROM marts.fct_daily_sales
        WHERE {' AND '.join(where_clauses)}
    """)
    
    result = self.db.execute(query, params).fetchone()
    return KPISummary(
        total_revenue=Decimal(result.total_revenue or 0),
        order_count=result.order_count or 0,
        unique_customers=result.unique_customers or 0,
        return_count=result.return_count or 0,
    )
```

**Security Pattern**: 
- Uses SQLAlchemy `text()` with named parameters (`:start_date`, `:end_date`)
- Never concatenates user input directly into SQL
- Prevents SQL injection via parameterization

**Date Handling**:
- Python `date` objects converted to YYYYMMDD integer format (20260328)
- Matches date_key columns in marts schema for fast joins
- Localized handling keeps business logic and SQL separate

#### Helper Methods
```python
def _build_where_clauses(self, filter: AnalyticsFilter) -> tuple[list, dict]:
    """Construct WHERE conditions and parameter dict"""
    # Returns: (["date_key >= :start_date", ...], {"start_date": 20260228, ...})
    
def _safe_growth_calc(prev: Decimal | None, curr: Decimal) -> float | None:
    """Safely calculate growth % handling None/zero cases"""
    if prev is None or prev == 0:
        return None
    return float((curr - prev) / prev * 100)
```

### 6.2 Analytics Service Layer
**File**: `src/datapulse/analytics/service.py`

**Purpose**: Business logic orchestration; applies defaults and service-level transformations

#### Default Date Range Application
```python
class AnalyticsService:
    def __init__(self, repo: AnalyticsRepository):
        self.repo = repo
    
    def _apply_default_range(
        self, filter: AnalyticsFilter
    ) -> AnalyticsFilter:
        """Apply 30-day default if no date range specified"""
        if filter.date_range is None:
            end_date = date.today()
            start_date = end_date - timedelta(days=30)
            filter.date_range = DateRange(
                start_date=start_date,
                end_date=end_date
            )
        return filter
    
    def get_dashboard_summary(self, filter: AnalyticsFilter) -> KPISummary:
        filter = self._apply_default_range(filter)
        return self.repo.get_kpi_summary(filter)
```

**Design Benefits**:
- Single responsibility: Service applies defaults, repository queries
- Composable: Service wraps repository; can chain multiple repos
- Testable: Repository can be mocked for unit testing service logic

#### Service Methods (Facade)
```python
# Service wraps 7 repository methods:
- get_dashboard_summary(filter) → KPISummary
- get_revenue_trends(filter) → list[TimeSeriesPoint]
- get_product_insights(filter) → RankingResult
- get_customer_insights(filter) → RankingResult
- get_site_comparison(filter) → list[ProductPerformance]
- get_staff_leaderboard(filter) → list[StaffPerformance]
- get_return_report(filter) → ReturnAnalysis
```

---

## 7. Logging Architecture

**File**: `src/datapulse/logging.py`

### 7.1 structlog Configuration

**Framework**: structlog with environment-based renderers

```python
def configure_logging():
    """Setup structured logging for JSON or console output"""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            (
                structlog.processors.JSONRenderer()
                if settings.environment == "production"
                else structlog.dev.ConsoleRenderer()
            ),
        ],
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )
```

### 7.2 Log Output Formats

**Development (console)**:
```
[2026-03-28 13:55:30.123 +00:00] HTTP request | method='GET' path='/api/health' status=200 elapsed_ms=1.23
```

**Production (JSON)**:
```json
{
  "timestamp": "2026-03-28T13:55:30.123Z",
  "level": "info",
  "event": "HTTP request",
  "method": "GET",
  "path": "/api/health",
  "status": 200,
  "elapsed_ms": 1.23
}
```

### 7.3 Context Merging
```python
# In request handler:
structlog.contextvars.bind_contextvars(tenant_id=1, user_id=42)
logger.info("user action", action="view_dashboard")
# Output includes tenant_id and user_id automatically
```

**Use Case**: Bind tenant/user context once per request; all downstream logs inherit it

---

## 8. Configuration & Settings

**File**: `src/datapulse/config.py`

### 8.1 Settings Class
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application configuration from environment variables"""
    
    # Database
    database_url: str
    
    # File Storage
    raw_data_dir: str
    processed_data_dir: str
    parquet_dir: str
    max_file_size_mb: int = 500
    max_rows: int = 100000
    max_columns: int = 200
    
    # Bronze Loader
    bronze_batch_size: int = 50000
    
    # API
    cors_origins: list[str] = ["http://localhost:3000"]
    
    # n8n Integration
    n8n_webhook_url: str | None = None
    
    # AI Services
    openrouter_api_key: str | None = None
    openrouter_model: str = "meta-llama/llama-2-70b-chat"
    
    # Notifications
    slack_webhook_url: str | None = None
    notification_email: str | None = None

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return singleton Settings instance"""
    return Settings()
```

### 8.2 Usage Pattern
```python
from datapulse.config import get_settings

settings = get_settings()
print(settings.database_url)  # Cached on first call
```

---

## 9. Existing Infrastructure Available for Phase 2.2

### 9.1 Health Check Pattern
**What Exists**:
- `GET /api/health` endpoint with database connectivity check
- Returns structured status response: `{status, db}`
- Pattern: Query database; return status based on result

**Leverage for Phase 2.2**:
- Extend health endpoint to include pipeline status checks
- Add pipeline schema tables to the SELECT 1 verification
- Response could include pipeline_runs last_status, quality_checks pending count, etc.

### 9.2 Session Management Pattern
**What Exists**:
- Generator-based session dependency injection
- SQLAlchemy session factory with pool_pre_ping
- RLS policies with tenant isolation via session variables
- Pattern: Clean session lifecycle via try/finally

**Leverage for Phase 2.2**:
- Reuse `get_db_session()` dependency for pipeline tables
- Tenant isolation already architected; apply to pipeline_runs table
- Create `get_pipeline_service(db=Depends(get_db_session))` following existing pattern

### 9.3 Repository/Service Pattern
**What Exists**:
- Read-only repository querying marts (analytics views)
- Service layer wrapping repository with defaults
- Parameterized SQL preventing injection
- Frozen Pydantic models for immutable responses

**Leverage for Phase 2.2**:
- Create `PipelineRepository(db: Session)` with methods:
  - `get_pipeline_runs(filter) → list[PipelineRun]`
  - `get_quality_checks(filter) → list[QualityCheck]`
  - `get_processed_files(filter) → list[ProcessedFile]`
- Create `PipelineService(repo)` with caching/orchestration
- Extend models to include `PipelineRun`, `QualityCheck`, `ProcessedFile` frozen dataclasses

### 9.4 API Endpoint Pattern
**What Exists**:
- Route handlers with dependency injection
- Query parameter parsing via Pydantic models
- Standardized response formats
- Tags for OpenAPI documentation

**Leverage for Phase 2.2**:
- Create `src/datapulse/api/routes/pipeline.py` router
- Implement 5 endpoints (from PHASE2_PLAN.md):
  - `GET /api/pipeline/runs` - List pipeline executions
  - `GET /api/pipeline/runs/{run_id}` - Pipeline execution detail
  - `GET /api/pipeline/quality-checks` - List quality check results
  - `POST /api/pipeline/runs/{run_id}/status` - Update run status
  - `POST /api/pipeline/quality-checks` - Create quality check result
- Reuse `AnalyticsFilter` pattern for `PipelineFilter(date_range, status, pipeline_name, etc.)`

### 9.5 Database Schema for Pipeline Tables
**What Exists**:
- Migration tracking system (`public.schema_migrations`)
- n8n schema prepared for workflow objects
- RLS infrastructure and tenant_id pattern
- Indexing best practices (date, tenant, status columns)

**Leverage for Phase 2.2**:
- Create migration `005_create_pipeline_tracking_schema.sql`:
  ```sql
  CREATE TABLE public.pipeline_runs (
      run_id BIGSERIAL PRIMARY KEY,
      pipeline_name VARCHAR NOT NULL,
      tenant_id INT NOT NULL REFERENCES bronze.tenants(tenant_id),
      started_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
      completed_at TIMESTAMPTZ,
      status VARCHAR(20) CHECK (status IN ('pending', 'running', 'success', 'failed')),
      error_message TEXT,
      n8n_execution_id VARCHAR,
      created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
  );
  
  CREATE TABLE public.quality_checks (
      check_id BIGSERIAL PRIMARY KEY,
      run_id BIGINT NOT NULL REFERENCES public.pipeline_runs(run_id) ON DELETE CASCADE,
      check_name VARCHAR NOT NULL,
      status VARCHAR(20) CHECK (status IN ('pending', 'passed', 'failed', 'warning')),
      details JSONB,
      created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
  );
  
  CREATE TABLE public.processed_files (
      file_id BIGSERIAL PRIMARY KEY,
      run_id BIGINT NOT NULL REFERENCES public.pipeline_runs(run_id) ON DELETE CASCADE,
      file_name VARCHAR NOT NULL,
      row_count INT,
      processed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
  );
  
  -- RLS: Enable for datapulse_reader
  ALTER TABLE public.pipeline_runs ENABLE ROW LEVEL SECURITY;
  CREATE POLICY reader_pipeline_runs ON public.pipeline_runs
      FOR SELECT USING (tenant_id = current_setting('app.tenant_id')::int);
  ```
- Indexes: run_id, pipeline_name, status, created_at, tenant_id for efficient filtering

### 9.6 Exception Handling & Logging
**What Exists**:
- Global exception handler returning sanitized JSON
- Request logging middleware with timing
- structlog with context variable support
- Pattern: Exceptions logged with context before returning response

**Leverage for Phase 2.2**:
- Log pipeline state transitions: `logger.info("pipeline status change", run_id=123, old_status="running", new_status="success")`
- Catch and log pipeline errors: `logger.exception("pipeline failed", run_id=123, pipeline_name="bronze_loader")`
- structlog's context merging means tenant_id/user_id automatically included in all logs

### 9.7 n8n Integration Hook
**What Exists**:
- n8n schema prepared in database
- `settings.n8n_webhook_url` configured
- Pattern: n8n can call API webhooks to report status

**Leverage for Phase 2.2**:
- Create `POST /api/pipeline/runs/{run_id}/webhook` endpoint for n8n status callbacks
- Webhook handler updates pipeline_runs table with execution result from n8n
- n8n returns run_id in response; phases pipeline execution tracking

---

## 10. Recommended Architecture for Phase 2.2

### 10.1 File Structure
```
src/datapulse/
├── api/
│   ├── routes/
│   │   ├── analytics.py        (existing)
│   │   ├── health.py           (existing)
│   │   └── pipeline.py         (NEW: 5 endpoints)
│   ├── app.py                  (existing: extend router registration)
│   └── deps.py                 (existing: add pipeline service factory)
├── pipeline/
│   ├── models.py               (NEW: PipelineRun, QualityCheck, ProcessedFile)
│   ├── repository.py           (NEW: pipeline data access)
│   ├── service.py              (NEW: pipeline orchestration)
│   └── schemas.py              (NEW: PipelineFilter, etc.)
└── migrations/
    └── 005_create_pipeline_tracking_schema.sql (NEW)
```

### 10.2 Dependency Injection Extension
```python
# In src/datapulse/api/deps.py

def get_pipeline_service(
    db: Session = Depends(get_db_session)
) -> PipelineService:
    """Create pipeline service with injected session"""
    repo = PipelineRepository(db)
    return PipelineService(repo)

# In src/datapulse/api/routes/pipeline.py

@pipeline_router.get("/runs")
async def list_pipeline_runs(
    filter: PipelineFilter = Depends(PipelineFilter),
    service: PipelineService = Depends(get_pipeline_service)
) -> list[PipelineRun]:
    return service.get_pipeline_runs(filter)
```

### 10.3 Response Models (Frozen)
```python
# In src/datapulse/pipeline/models.py

@dataclass(frozen=True)
class PipelineRun:
    run_id: int
    pipeline_name: str
    status: str  # 'pending', 'running', 'success', 'failed'
    started_at: datetime
    completed_at: datetime | None
    error_message: str | None
    duration_seconds: int | None
    n8n_execution_id: str | None

@dataclass(frozen=True)
class QualityCheck:
    check_id: int
    run_id: int
    check_name: str
    status: str  # 'pending', 'passed', 'failed', 'warning'
    details: dict | None
    created_at: datetime

@dataclass(frozen=True)
class ProcessedFile:
    file_id: int
    run_id: int
    file_name: str
    row_count: int
    processed_at: datetime
```

### 10.4 Integration Points with Existing Code

| Component | Integration |
|-----------|-------------|
| **Database Session** | Reuse `get_db_session()` dependency |
| **Tenant Isolation** | Set `app.tenant_id` session variable before queries (currently missing) |
| **Error Handling** | Global exception handler catches pipeline errors; logged via structlog |
| **Logging Context** | structlog.contextvars.bind_contextvars(run_id=X, pipeline_name=Y) in middleware |
| **Configuration** | Add pipeline settings to Settings class |
| **CORS** | Extend allow_methods if POST/PATCH needed for run status updates |
| **Health Check** | Optional: extend GET /health to include pipeline queue status |
| **n8n Webhook** | POST endpoint accepts n8n execution callbacks; updates run status |

---

## 11. Security Considerations for Phase 2.2

### 11.1 RLS & Multi-Tenancy
- **Current Gap**: Session variables (app.tenant_id) not being set by application
- **Phase 2.2 Action**: Implement tenant extraction (JWT, header, or session)
- **Pattern**: Before yielding session in get_db_session_with_tenant, execute:
  ```python
  session.execute(text("SET LOCAL app.tenant_id = :tenant_id"), {"tenant_id": tenant_id})
  ```

### 11.2 Query Parameterization
- **Pattern**: All pipeline queries should use SQLAlchemy text() with named parameters
- **Example**:
  ```python
  query = text("""
      SELECT * FROM pipeline_runs 
      WHERE status = :status AND created_at > :since_date
  """)
  results = db.execute(query, {"status": "failed", "since_date": since_date})
  ```

### 11.3 Input Validation
- **Pattern**: Pydantic models validate all query parameters
- **Example**: PipelineFilter should bound status choices, date ranges, limit values

### 11.4 n8n Webhook Authentication
- **Pattern**: Verify webhook requests are from trusted n8n instance
- **Implementation**: Use API key header or HMAC signature validation before processing

---

## 12. Performance Considerations

### 12.1 Indexing Strategy
Create indexes on:
- `pipeline_runs(status, created_at)` - Fast filtering by status and date
- `pipeline_runs(tenant_id, created_at)` - RLS filtering with temporal queries
- `quality_checks(run_id)` - Fast cascade on deletion/lookup
- `processed_files(run_id)` - Fast file listing per run

### 12.2 Query Patterns
- **List endpoint**: Use LIMIT with pagination; avoid full table scans
- **Detail endpoint**: Use run_id primary key; single row lookup
- **Status updates**: Use WHERE run_id = ? to target single row

### 12.3 Connection Pooling
- Reuse `pool_pre_ping=True` pattern from analytics
- Pool verifies stale connections before use
- Prevents "connection lost" errors during pipeline status polling

---

## Summary Table: Phase 2.2 Build-Upon Infrastructure

| Infrastructure | Type | Location | Reusable For Phase 2.2 |
|---|---|---|---|
| FastAPI factory with middleware | Pattern | src/datapulse/api/app.py | ✓ Extend router registration |
| Session dependency injection | Pattern | src/datapulse/api/deps.py | ✓ Add pipeline service factory |
| Parameterized SQL queries | Pattern | src/datapulse/analytics/repository.py | ✓ Clone for PipelineRepository |
| Repository/Service composition | Pattern | analytics/ module | ✓ Create pipeline/ module |
| Frozen Pydantic models | Pattern | src/datapulse/analytics/models.py | ✓ Create PipelineRun, QualityCheck, etc. |
| structlog context binding | Pattern | src/datapulse/logging.py | ✓ Bind run_id, pipeline_name to logs |
| Health check endpoint | Pattern | src/datapulse/api/routes/health.py | ✓ Extend for pipeline queue status |
| RLS with tenant_id | Infrastructure | migrations/003 | ✓ Apply to pipeline_runs table |
| n8n schema | Schema | migrations/004 | ✓ Link to pipeline execution logs |
| Exception handling | Pattern | src/datapulse/api/app.py | ✓ Reuse global handler for pipeline errors |
| Request logging middleware | Pattern | src/datapulse/api/app.py | ✓ Logs pipeline API calls automatically |
| Settings/configuration | Pattern | src/datapulse/config.py | ✓ Add pipeline batch_size, retry limits |
| Migration tracking system | Infrastructure | migrations/000 | ✓ Use for pipeline schema migration |

---

## Conclusion

The DataPulse project provides a robust, production-ready foundation for Phase 2.2 pipeline tracking:

1. **API Layer**: Established patterns for dependency injection, error handling, CORS, and request logging
2. **Database**: Multi-schema architecture with RLS, tenant isolation, and indexed tables ready for pipeline tables
3. **Service Layer**: Repository/Service separation enabling clean unit testing and composability
4. **Logging**: Structured logging with context variable support for pipeline execution tracking
5. **Session Management**: Generator-based cleanup pattern preventing connection leaks
6. **Configuration**: Environment-driven settings for pipelines batch size, timeouts, n8n URLs

Phase 2.2 should follow the established patterns in analytics module to achieve consistency. The RLS infrastructure requires one fix: tenant context setting in session initialization. The n8n schema is prepared; webhook endpoints can integrate pipeline status callbacks.

**Estimated effort**: 3-5 days to implement 5 pipeline endpoints + 3 database tables + service layer + tests, leveraging existing patterns.
