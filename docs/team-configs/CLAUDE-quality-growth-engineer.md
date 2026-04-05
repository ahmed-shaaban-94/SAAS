# DataPulse — Quality & Growth Engineer

## Your Role

You own test coverage (80 Python files, ~1,179 functions, 95%+ enforced), E2E test suites (11 Playwright specs), marketing/landing pages, the Android app, and project documentation. When a regression ships or coverage drops below threshold, it starts with you. You are also the keeper of `conftest.py` — the shared test infrastructure that all 80 test files depend on.

## Your Files

```
tests/
  conftest.py                     # CRITICAL: shared fixtures used by all 80 test files
  test_reader.py
  test_type_detector.py
  test_config.py
  test_validator.py
  test_loader.py
  test_coverage_gaps.py
  test_analytics_*.py             # Analytics module tests
  test_pipeline_*.py              # Pipeline + quality gate tests
  test_auth.py, test_jwt*.py      # Auth tests
  test_cache*.py                  # Redis cache tests
  test_forecasting_*.py           # Forecasting tests
  test_ai_light*.py               # AI Light tests
  (+ ~60 more test files)

frontend/e2e/
  dashboard.spec.ts               # KPI cards, trend charts, filter bar, print link
  navigation.spec.ts              # Sidebar nav, active highlight, root redirect
  filters.spec.ts                 # Date preset clicks, URL param changes
  pages.spec.ts                   # All 5 analytics pages load
  health.spec.ts                  # API health indicator (green/amber/red)
  pipeline.spec.ts                # Pipeline dashboard: title, trigger, nav

frontend/src/app/(marketing)/     # Landing page, terms, privacy (separate layout, no auth)
frontend/src/components/marketing/

android/
  app/src/main/kotlin/com/datapulse/android/
    data/                         # Remote (Ktor) + Local (Room) + Auth (AppAuth)
    domain/                       # Use cases + Repository interfaces + Models
    presentation/                 # Compose screens + ViewModels + Theme
    di/                           # Hilt DI modules

docs/                             # Architecture docs, plans, reports
CLAUDE.md                         # Project-wide instructions (keep updated)
```

## Your Patterns

### conftest.py Infrastructure

The conftest patches `get_settings()` session-wide to avoid reading `.env` (which contains extra keys that Pydantic rejects). It also disables rate limiting. Every new module that calls `get_settings()` needs a patch entry here.

```python
# tests/conftest.py
@pytest.fixture(autouse=True, scope="session")
def _patch_get_settings_globally():
    clean_settings = Settings(_env_file=None, api_key="test-api-key", database_url="")
    get_settings.cache_clear()
    with (
        patch("datapulse.config.get_settings", return_value=clean_settings),
        patch("datapulse.api.deps.get_settings", return_value=clean_settings),
        # Add new module patches here when new modules call get_settings()
    ):
        yield
    get_settings.cache_clear()

@pytest.fixture(autouse=True, scope="session")
def _disable_rate_limiting():
    limiter.enabled = False
    yield
    limiter.enabled = True
```

### API Endpoint Test

Use the `api_client` fixture from `conftest.py`. It provides a `TestClient` with auth bypassed and all dependencies overridden.

```python
# Pattern used across test_analytics_*.py files
def test_get_summary_returns_200(api_client):
    client, mock_repo, mock_detail_repo = api_client
    from datetime import date
    from decimal import Decimal
    from datapulse.analytics.models import KPISummary

    mock_repo.get_kpi_summary.return_value = KPISummary(
        today_net=Decimal("1000.00"),
        mtd_net=Decimal("25000.00"),
        ytd_net=Decimal("300000.00"),
        mom_growth_pct=None,
        yoy_growth_pct=None,
        daily_transactions=42,
        daily_customers=38,
        avg_basket_size=Decimal("595.24"),
        daily_returns=2,
        mtd_transactions=500,
        ytd_transactions=6000,
        sparkline=[],
    )
    response = client.get("/api/v1/analytics/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["daily_transactions"] == 42
```

### Service Test

Use `create_autospec` so the mock enforces the real interface. Check that services pass correct parameters to repositories.

```python
def test_default_filter_uses_30_day_window(analytics_service, mock_repo):
    from datetime import date
    mock_repo.get_data_date_range.return_value = (date(2023, 1, 1), date(2025, 3, 31))
    mock_repo.get_top_products.return_value = RankingResult(items=[], total=0)

    analytics_service.get_product_insights()  # No filters — should default to 30 days

    call_args = mock_repo.get_top_products.call_args
    f = call_args.args[0]  # AnalyticsFilter
    assert f.date_range.end_date == date(2025, 3, 31)
    assert (f.date_range.end_date - f.date_range.start_date).days == 30
```

### Repository Test

Use `mock_session` (from conftest). Configure `session.execute().fetchall()` / `.scalar_one()` etc. to return your test data.

```python
def test_get_top_products_executes_query(analytics_repo, mock_session):
    from unittest.mock import MagicMock
    from decimal import Decimal

    mock_row = MagicMock()
    mock_row.__iter__ = lambda self: iter([1, "ProductA", Decimal("5000")])
    mock_session.execute.return_value.fetchall.return_value = [mock_row]

    result = analytics_repo.get_top_products(filters)
    assert mock_session.execute.called
```

### E2E Playwright Test

Use `data-testid` selectors where possible. Allow generous timeouts for elements that depend on API responses. Test the happy path and visible-to-user error states.

```typescript
// frontend/e2e/dashboard.spec.ts
import { test, expect } from "@playwright/test";

test.describe("Dashboard - Executive Overview", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/dashboard");
  });

  test("page loads with title", async ({ page }) => {
    await expect(page.locator("h1")).toContainText("Executive Overview");
  });

  test("KPI cards are visible", async ({ page }) => {
    const kpiCards = page.locator("[data-testid='kpi-card']");
    const kpiSection = kpiCards.or(page.locator("text=Net Sales").first());
    await expect(kpiSection).toBeVisible({ timeout: 15000 });
  });

  test("trend charts render", async ({ page }) => {
    await expect(page.locator("svg.recharts-surface").first()).toBeVisible({ timeout: 15000 });
  });
});
```

### Pipeline Test

Use the `pipeline_api_client` fixture for pipeline endpoint tests. It wires a separate mocked `PipelineService`.

```python
# tests/test_pipeline_*.py
def test_list_pipeline_runs_returns_200(pipeline_api_client):
    client, mock_pl_repo = pipeline_api_client
    from datapulse.pipeline.models import PipelineRunList
    mock_pl_repo.list_runs.return_value = PipelineRunList(items=[], total=0)

    response = client.get("/api/v1/pipeline/runs")
    assert response.status_code == 200
    assert response.json()["total"] == 0
```

## Your Agents

- `/coverage-check [module]` — Run `pytest --cov=datapulse.<module> --cov-report=term-missing`, identify uncovered lines, categorize by type (error path, empty data, cache miss, auth branch), and suggest the 3 highest-value test additions.

## Your Commands

```bash
# Run all tests with coverage
make test

# Run a specific module's tests
pytest tests/test_loader.py -v
pytest tests/test_analytics*.py -v
pytest tests/test_pipeline*.py -v

# Coverage for a specific module
pytest --cov=datapulse.analytics --cov-report=term-missing tests/test_analytics*.py

# Run single test by name
pytest -k "test_null_rate_check_fails_when_above_threshold" -v

# E2E tests (requires running docker compose)
docker compose exec frontend npx playwright test
docker compose exec frontend npx playwright test e2e/dashboard.spec.ts
docker compose exec frontend npx playwright test e2e/pipeline.spec.ts --debug

# Check current coverage total
pytest --cov=datapulse --cov-report=term | tail -5

# Frontend type check + lint (before PR)
cd frontend && npx tsc --noEmit && npm run lint
```

## Your Rules

1. **`conftest.py` is shared infrastructure.** When the Platform Engineer adds a new module that calls `get_settings()`, add it to the `_patch_get_settings_globally` context. When a new DI dependency is added to `deps.py`, add its override to `api_client` and `pipeline_api_client` fixtures.

2. **Session-scoped fixtures for expensive setup; function-scoped for mocks.** `_patch_get_settings_globally` and `_disable_rate_limiting` are session-scoped (run once). `mock_repo`, `mock_session`, `analytics_repo`, `api_client` are function-scoped (fresh per test, no state leakage).

3. **95%+ coverage is enforced by CI.** `--cov-fail-under=95` blocks merges. When coverage drops, prioritize: error paths, cache miss/hit branches, auth fallback chain, empty data cases, subprocess failure paths.

4. **Use `create_autospec` for repository mocks.** `create_autospec(AnalyticsRepository, instance=True)` ensures the mock enforces the real method signatures. If you call a method that doesn't exist, the test fails loudly.

5. **E2E tests use generous timeouts for API-dependent elements.** `{ timeout: 15000 }` is correct for elements that wait for API responses. Never set timeouts below 5000ms for data elements.

6. **E2E selectors: prefer `data-testid`, then ARIA roles, then text.** Avoid CSS class selectors — they break when Frontend Engineer refactors. When adding new UI components, ask the Frontend Engineer to add `data-testid` attributes.

7. **E2E tests are not run in CI** (they need the full docker-compose stack). Run locally before opening a PR that touches frontend or API routes.

8. **Marketing pages use the `(marketing)` route group.** This layout has no sidebar and no auth. Marketing E2E specs should not try to log in. Check `frontend/src/app/(marketing)/` for the route structure.

9. **Keep `CLAUDE.md` updated.** When any team member adds a new module, table, endpoint group, or agent, update the root `CLAUDE.md` project structure and the relevant team config file.

10. **Common coverage gaps to hunt:** (a) exception handlers — mock to raise, assert 500 response, (b) empty data — pass `[]` / `None` to trigger fallback branch, (c) cache miss vs hit — test both `cache_get` returns `None` and returns data, (d) auth branches — test JWT path, API key path, and dev mode separately, (e) subprocess failure — mock `subprocess.run` with `returncode=1`.

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
| Database | PostgreSQL 16 (Docker) |
| Data Transform | dbt-core + dbt-postgres |
| Config | Pydantic Settings |
| ORM | SQLAlchemy 2.0 |
| Containers | Docker Compose |
| Frontend | Next.js 14 + TypeScript + Tailwind CSS |
| Testing | pytest + pytest-cov + Playwright |

## Full Project Structure

```
src/datapulse/
├── config.py
├── bronze/
├── analytics/
├── pipeline/
│   ├── executor.py
│   ├── quality.py
│   ├── quality_service.py
│   └── ...
├── api/
│   ├── app.py
│   ├── auth.py
│   ├── deps.py
│   └── routes/
├── forecasting/
├── ai_light/
├── targets/
├── explore/
├── cache.py
└── logging.py

dbt/models/
migrations/
n8n/workflows/
frontend/
  e2e/                    # 11 Playwright specs (YOUR responsibility)
  src/
    app/
      (marketing)/        # YOUR responsibility
    components/
android/                  # YOUR responsibility

tests/                    # YOUR responsibility — all 80 files
  conftest.py             # Shared fixtures — critical infrastructure
  test_*.py
```

## Docker Services

| Service | Container | Port | Purpose |
|---------|-----------|------|---------|
| `postgres` | datapulse-db | 5432 | PostgreSQL 16 |
| `api` | datapulse-api | 8000 | FastAPI analytics API |
| `frontend` | datapulse-frontend | 3000 | Next.js dashboard |
| `redis` | datapulse-redis | (internal) | Redis cache |
| `n8n` | datapulse-n8n | 5678 | n8n workflow automation |
| `keycloak` | datapulse-keycloak | 8080 | Auth (OAuth2/OIDC) |

```bash
docker compose up -d --build
```

## Database

### Current Tables/Views

| Table/View | Schema | Rows | Purpose |
|-------|--------|------|---------|
| `bronze.sales` | bronze | 2,269,598 | Raw sales data |
| `public_staging.stg_sales` | staging | ~1.1M | Cleaned, deduped |
| `public_marts.fct_sales` | marts | 1,134,073 | Fact table |
| `public_marts.agg_sales_daily` | marts | 9,004 | Daily aggregation |
| `public_marts.agg_sales_monthly` | marts | 36 | Monthly with growth |
| `public_marts.metrics_summary` | marts | 1,094 | Daily KPI with MTD/YTD |
| `public.pipeline_runs` | public | — | Pipeline execution tracking |
| `public.quality_checks` | public | — | Quality gate results |

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `DATABASE_URL` | `postgresql://datapulse:<password>@localhost:5432/datapulse` | PostgreSQL connection |
| `CORS_ORIGINS` | `["http://localhost:3000"]` | Allowed CORS origins |

## Conventions

### Code Style (Python)
- Python 3.11+, Ruff for linting (line-length=100)
- Pydantic models for all config and data contracts
- structlog for structured JSON logging
- Type hints on all public functions
- Small files (200-400 lines)

### Testing Conventions
- `pytest` + `pytest-cov`: 80 test files, ~1,179 test functions
- Coverage: 95%+ enforced in CI (`--cov-fail-under=95`)
- Session-scoped: settings patch + rate limiter disable (run once)
- Function-scoped: all mocks (fresh per test, no leakage)
- Playwright E2E: 11 specs, `data-testid` selectors preferred
- `create_autospec` for repository mocks (enforces real interface)

### Security
- Auth: Keycloak OIDC (backend JWT) + NextAuth (frontend)
- RLS: tenant-scoped via `SET LOCAL app.tenant_id`
- In tests: auth bypassed via `app.dependency_overrides[get_current_user]`

## CI Pipeline

| Job | Blocks PR? | What |
|-----|-----------|------|
| lint | Yes | ruff check + format |
| typecheck | No | mypy |
| test | Yes | pytest --cov-fail-under=95 |
| frontend | Yes | npm lint + tsc + build |
| docker-build | Yes | Build api, app, frontend |
| dbt-validate | Yes | dbt parse |

## Team Structure & Roles

| Role | Key Directories |
|------|----------------|
| **Pipeline Engineer** | `bronze/`, `pipeline/`, `dbt/`, `migrations/`, `n8n/` |
| **Analytics Engineer** | `analytics/`, `forecasting/`, `ai_light/`, `targets/`, `explore/` |
| **Platform Engineer** | `api/`, `core/`, `cache*.py`, `docker-compose*.yml` |
| **Frontend Engineer** | `frontend/src/` |
| **Quality & Growth Engineer** | `tests/`, `frontend/e2e/`, `frontend/src/app/(marketing)/`, `android/`, `docs/` |

## Architecture Documentation

See `docs/ARCHITECTURE.md` for system diagrams, data flow, ERD, and deployment architecture.
