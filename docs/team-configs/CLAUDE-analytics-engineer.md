# DataPulse — Analytics Engineer

## Your Role

You own all business logic that turns gold-layer data into actionable insights: analytics queries (KPIs, trends, rankings, breakdowns), forecasting, AI light summaries via OpenRouter, sales targets, self-serve explore, SQL lab, reports, and export. The frontend's 40 SWR hooks consume your JSON responses — correctness and performance are your responsibility.

## Your Files

```
src/datapulse/analytics/
  repository.py              # Primary: KPI summary, daily/monthly trends, top-N rankings
  detail_repository.py       # Product/customer/staff/site detail pages
  breakdown_repository.py    # Billing breakdown, customer-type breakdown by month
  comparison_repository.py   # Top movers (gainers/losers vs previous period)
  hierarchy_repository.py    # Product hierarchy (category -> brand -> product)
  advanced_repository.py     # ABC analysis, heatmap, returns trend, RFM segments
  service.py                 # Business logic layer — @cached decorators, default filters
  models.py                  # All Pydantic models (frozen=True, JsonDecimal for money)
  queries.py                 # Shared helpers: build_where, build_ranking, build_trend

src/datapulse/forecasting/   # Holt-Winters, SMA, Seasonal Naive, backtest
src/datapulse/ai_light/      # OpenRouter LLM: summaries, anomaly detection, change narratives
src/datapulse/targets/       # Sales targets + alert configs + alert log CRUD
src/datapulse/explore/       # dbt catalog parser + whitelist SQL builder
src/datapulse/sql_lab/       # Interactive SQL validation + execution
src/datapulse/reports/       # Templated report generation
src/datapulse/types.py       # JsonDecimal type alias (Decimal internally, float in JSON)

src/datapulse/api/routes/
  analytics.py               # 10 core analytics endpoints under /api/v1/analytics/
  forecasting.py             # Forecasting endpoints
  ai_light.py                # AI Light endpoints
  targets.py                 # Targets + alerts endpoints
  explore.py                 # Explore / catalog endpoints
  sql_lab.py                 # SQL Lab endpoints
  reports.py                 # Reports endpoints
  export.py                  # CSV/Excel/PDF export endpoints
```

## Your Patterns

### Service-Repository with Redis Cache

The `AnalyticsService` wraps every public method with cache. Use `_cache_key()` for deterministic keys and `@cached(ttl=..., prefix=...)` decorator for filter-dependent methods.

```python
# src/datapulse/analytics/service.py
_CACHE_PREFIX = "datapulse:analytics"

def _cache_key(method: str, params: dict[str, Any] | None = None) -> str:
    if params:
        raw = json.dumps(params, sort_keys=True, default=str)
        h = hashlib.md5(raw.encode(), usedforsecurity=False).hexdigest()[:12]
        return f"{_CACHE_PREFIX}:{method}:{h}"
    return f"{_CACHE_PREFIX}:{method}"

def get_dashboard_summary(self, target_date: date | None = None) -> KPISummary:
    """KPI cards for dashboard header (cached 600s)."""
    key = _cache_key("summary", {"target_date": str(target)})
    cached_val = cache_get(key)
    if cached_val is not None:
        return KPISummary(**cached_val)
    result = self._repo.get_kpi_summary(target)
    cache_set(key, result.model_dump(mode="json"), ttl=600)
    return result

@cached(ttl=300, prefix=_CACHE_PREFIX)
def get_product_insights(self, filters: AnalyticsFilter | None = None) -> RankingResult:
    f = self._default_filter(filters)
    return self._repo.get_top_products(f)
```

### Parameterized SQL with Whitelist

All SQL uses `text()` with `:param` placeholders. Dynamic table/column names MUST be validated against allowlists before SQL construction.

```python
# src/datapulse/analytics/repository.py
from datapulse.analytics.queries import ALLOWED_RANKING_TABLES, ALLOWED_RANKING_COLUMNS

def _get_ranking(self, table: str, key_col: str, name_col: str,
                 filters: AnalyticsFilter) -> RankingResult:
    if table not in ALLOWED_RANKING_TABLES:
        raise ValueError(f"Invalid ranking table: {table}")
    if key_col not in ALLOWED_RANKING_COLUMNS:
        raise ValueError(f"Invalid ranking key column: {key_col}")

    where, params = build_where(filters, use_year_month=True)
    params["limit"] = filters.limit

    stmt = text(f"""
        SELECT {key_col}, {name_col}, SUM(total_net_amount) AS value
        FROM {table}
        WHERE {where}
        GROUP BY {key_col}, {name_col}
        ORDER BY value DESC
        LIMIT :limit
    """)
    rows = self._session.execute(stmt, params).fetchall()
    return build_ranking(list(rows))
```

### Pydantic Immutable Models

All models have `model_config = ConfigDict(frozen=True)`. Financial fields use `JsonDecimal` — `Decimal` precision in Python, `float` in JSON serialization.

```python
# src/datapulse/analytics/models.py
from datapulse.types import JsonDecimal

class KPISummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    today_net: JsonDecimal      # Decimal("1234.56") in Python, 1234.56 in JSON
    mtd_net: JsonDecimal
    ytd_net: JsonDecimal
    mom_growth_pct: JsonDecimal | None = None
    daily_transactions: int
    sparkline: list[TimeSeriesPoint] = Field(default_factory=list)
```

### Default Filter Pattern

When no filters are supplied, fall back to a 30-day window ending on the latest data date. Never hardcode dates.

```python
def _default_filter(self, filters: AnalyticsFilter | None = None) -> AnalyticsFilter:
    if filters is not None:
        return filters
    _, max_date = self._repo.get_data_date_range()
    end = max_date or date.today()
    return AnalyticsFilter(
        date_range=DateRange(
            start_date=end - timedelta(days=30),
            end_date=end,
        )
    )
```

### AI Prompt Sanitization

Strip control characters and role-injection attempts from any user-supplied text before sending to OpenRouter.

```python
# src/datapulse/ai_light/service.py
def _sanitize_input(self, raw: str) -> str:
    sanitized = re.sub(r'[\x00-\x1f\x7f]', '', raw)
    sanitized = re.sub(r'(system|user|assistant):', '', sanitized, flags=re.IGNORECASE)
    return sanitized[:1000]
```

Always have a statistical fallback: if OpenRouter is unavailable or rate-limited, return the numbers without a narrative rather than raising an error.

## Your Agents

- `/add-analytics-endpoint <name>` — Full scaffold: Pydantic model -> Repository method -> Service method (with `@cached`) -> Route handler -> Test file.
- `/coverage-check analytics` — Run tests for the analytics module, find uncovered branches, suggest targeted test cases.

## Your Commands

```bash
# Run all analytics tests
pytest tests/test_analytics*.py -v

# Run forecasting tests
pytest tests/test_forecasting*.py -v

# Run AI light tests
pytest tests/test_ai_light*.py -v

# Coverage for analytics module
pytest --cov=datapulse.analytics --cov-report=term-missing tests/test_analytics*.py

# Run all tests (full suite)
make test

# Test a specific endpoint
curl "http://localhost:8000/api/v1/analytics/summary" -H "X-API-Key: $API_KEY"
curl "http://localhost:8000/api/v1/analytics/products/top?limit=10" -H "X-API-Key: $API_KEY"
```

## Your Rules

1. **ALL SQL uses `text()` with `:param` placeholders.** Never f-string user-supplied values into SQL. Dynamic table/column names must come from an allowlist (`ALLOWED_RANKING_TABLES`, `ALLOWED_RANKING_COLUMNS`, or equivalent).

2. **All Pydantic models are `frozen=True`.** Never mutate a model instance — always return a new object.

3. **Money is `Decimal` / `JsonDecimal`.** Never use `float` for financial calculations. `JsonDecimal` serializes to float in JSON responses but preserves `Decimal` precision internally.

4. **Cache everything with appropriate TTLs.** Dashboard/summary: 600s. Trend/ranking: 300s. Filter options: 3600s. Date range: 3600s. Use `@cached(ttl=..., prefix=_CACHE_PREFIX)` for filter-dependent methods.

5. **Always provide a default date window.** Call `_default_filter()` when `filters=None`. Never let a query run against the full multi-year dataset without a date range.

6. **AI fallback is mandatory.** If OpenRouter is down, return statistical results with `narrative=None`. Never let an external LLM failure break a dashboard endpoint.

7. **Sub-repo pattern for new query domains.** If a new query area (e.g. pricing, cohorts) grows to >3 methods, create a new `*_repository.py` and inject it into `AnalyticsService.__init__`.

8. **New endpoints require tests.** 95%+ coverage is enforced in CI. At minimum: success case, empty data case, and filter-with-no-results case.

---

## Project Overview

A data analytics platform for sales data: import raw Excel/CSV files, clean and transform through a medallion architecture (bronze/silver/gold), analyze with SQL, and visualize on interactive dashboards.

**Pipeline**: Import (Bronze) -> Clean (Silver) -> Analyze (Gold) -> Dashboard

## Architecture

### Medallion Data Architecture

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

### Tech Stack

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
| DB Admin | pgAdmin 4 |
| Notebooks | JupyterLab |
| Frontend | Next.js 14 + TypeScript + Tailwind CSS |
| Charts | Recharts |
| Data Fetching | SWR |
| BI / Analytics | Power BI Desktop (Import mode, 99 DAX measures) |

## Full Project Structure

```
src/datapulse/
├── __init__.py
├── config.py                    # Pydantic settings (DB URL, limits, paths)
├── bronze/                      # Bronze layer — raw data ingestion
│   ├── column_map.py
│   └── loader.py
├── analytics/                   # Analytics module — gold layer queries
│   ├── models.py
│   ├── repository.py
│   ├── detail_repository.py
│   ├── breakdown_repository.py
│   ├── comparison_repository.py
│   ├── hierarchy_repository.py
│   ├── advanced_repository.py
│   ├── queries.py
│   └── service.py
├── pipeline/                    # Pipeline + quality gates
├── api/                         # FastAPI REST API
│   ├── app.py
│   ├── deps.py
│   └── routes/
├── forecasting/
├── ai_light/
├── targets/
├── explore/
├── sql_lab/
├── reports/
├── logging.py
└── types.py                     # JsonDecimal

dbt/models/                      # All dbt SQL models
migrations/                      # SQL migrations
n8n/workflows/                   # Automation workflows
frontend/src/                    # Next.js dashboard
tests/                           # 80 test files
```

## Docker Services

| Service | Container | Port | Purpose |
|---------|-----------|------|---------|
| `app` | datapulse-app | 8888 | Python app + JupyterLab |
| `postgres` | datapulse-db | 5432 | PostgreSQL 16 |
| `pgadmin` | datapulse-pgadmin | 5050 | Database admin UI |
| `api` | datapulse-api | 8000 | FastAPI analytics API |
| `frontend` | datapulse-frontend | 3000 | Next.js dashboard |
| `redis` | datapulse-redis | (internal) | Redis cache |
| `n8n` | datapulse-n8n | 5678 | n8n workflow automation |
| `keycloak` | datapulse-keycloak | 8080 | Auth (OAuth2/OIDC) |

```bash
docker compose up -d --build
```

## Database

### Current Tables/Views (Gold Layer — your query targets)

| Table/View | Schema | Rows | Purpose |
|-------|--------|------|---------|
| `public_marts.fct_sales` | marts | 1,134,073 | Fact table (6 FKs, 4 financial measures) |
| `public_marts.agg_sales_daily` | marts | 9,004 | Daily aggregation |
| `public_marts.agg_sales_monthly` | marts | 36 | Monthly with MoM/YoY |
| `public_marts.agg_sales_by_product` | marts | 161,703 | Product performance by month |
| `public_marts.agg_sales_by_customer` | marts | 43,674 | Customer analytics by month |
| `public_marts.agg_sales_by_site` | marts | 36 | Site performance by month |
| `public_marts.agg_sales_by_staff` | marts | 3,123 | Staff performance by month |
| `public_marts.agg_returns` | marts | 91,536 | Return analysis by product/customer |
| `public_marts.metrics_summary` | marts | 1,094 | Daily KPI with MTD/YTD running totals |
| `public_marts.dim_date` | marts | 1,096 | Calendar dimension |
| `public_marts.dim_billing` | marts | 11 | Billing dimension |
| `public_marts.dim_customer` | marts | 24,801 | Customer dimension |
| `public_marts.dim_product` | marts | 17,803 | Product dimension |
| `public_marts.dim_site` | marts | 2 | Site dimension |
| `public_marts.dim_staff` | marts | 1,226 | Staff dimension |

## Configuration

All settings via environment variables or `.env` file (Pydantic Settings):

| Setting | Default | Description |
|---------|---------|-------------|
| `DATABASE_URL` | `postgresql://datapulse:<password>@localhost:5432/datapulse` | PostgreSQL connection |
| `MAX_FILE_SIZE_MB` | 500 | Max upload file size |
| `MAX_ROWS` | 10,000,000 | Max rows per dataset |
| `CORS_ORIGINS` | `["http://localhost:3000"]` | Allowed CORS origins |

## Conventions

### Code Style (Python)
- Python 3.11+, Ruff for linting (line-length=100)
- Pydantic models for all config and data contracts (`frozen=True`)
- structlog for structured JSON logging
- Type hints on all public functions
- Small files (200-400 lines), extract when approaching 800
- Functions < 50 lines, no nesting > 4 levels
- Immutable patterns — always create new objects, never mutate

### Security
- **Authentication**: Keycloak OIDC — backend JWT, frontend NextAuth
- Tenant-scoped RLS: session variable `SET LOCAL app.tenant_id = '<id>'`
- SQL: `text()` with `:param` only — no f-string values
- Table/column names: validate against frozenset allowlist before SQL
- Financial columns: `NUMERIC(18,4)` in DB, `Decimal` / `JsonDecimal` in Python

### Testing
- pytest + pytest-cov: 80 test files, ~1,179 test functions
- Current coverage: 95%+ on `src/datapulse/` (enforced in CI)
- Run tests: `make test`

## Team Structure & Roles

| Role | Key Directories |
|------|----------------|
| **Pipeline Engineer** | `bronze/`, `pipeline/`, `dbt/`, `migrations/`, `n8n/` |
| **Analytics Engineer** | `analytics/`, `forecasting/`, `ai_light/`, `targets/`, `explore/` |
| **Platform Engineer** | `api/`, `core/`, `cache*.py`, `tasks/`, `docker-compose*.yml` |
| **Frontend Engineer** | `frontend/src/` |
| **Quality & Growth Engineer** | `tests/`, `frontend/e2e/`, `android/`, `docs/` |

## Architecture Documentation

See `docs/ARCHITECTURE.md` for system diagrams, data flow, ERD, and deployment architecture.
