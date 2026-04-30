# Dragon Roar — Full Project Audit Execution Plan

**Date:** 2026-04-06 | **Branch:** `claude/admiring-shaw` | **Codebase:** DataPulse SaaS
**Scope:** 80+ findings across 6 sprints | **Estimated total:** ~80 hours

---

## Context

A comprehensive project audit (initiated by an external LLM checkup + our own deep scan) uncovered critical data integrity issues, security gaps, testing failures, performance bottlenecks, and frontend quality problems. The most urgent: quality gate checks reference a phantom `net_sales` column that blocks every pipeline run, dimension date range ends in 2025 (today is 2026-04-06), and the backend test suite is broken by a bad conftest patch.

This plan addresses ALL findings except 6 deferred items (Next.js 15, ESLint 9, NextAuth v5, psycopg3, APScheduler 4, autocommit sessions) which are documented at the end for future execution.

---

## Sprint 1: Pipeline & Data Integrity (CRITICAL)
**Priority:** P0 — Data is currently broken | **Est:** ~12 hours
**Dependencies:** None — this sprint unblocks everything else

### 1.1 Fix `net_sales` phantom column in quality checks
**Files:**
- `src/datapulse/pipeline/quality.py`
  - Line 29: `CRITICAL_COLUMNS = ("reference_no", "date", "net_sales", "quantity")` → change `net_sales` to `sales`
  - Line 304: SQL `SIGN(net_sales::numeric)` → `SIGN(sales::numeric)`
  - Audit all other `net_sales` references in file
- `src/datapulse/pipeline/quality_engine.py`
  - Line 38: DEFAULT_RULES bronze null_rate columns — keep `net_sales` (exists in bronze)
  - Line 52: DEFAULT_RULES silver null_rate columns — change `net_sales` to `sales`
  - Line 83: Add `"sales"` to `_ALLOWED_COLUMNS` frozenset
- `tests/test_quality_checks.py` — update any test assertions referencing `net_sales` for silver stage
**Risk:** LOW — direct column rename, no behavioral change
**Est:** 1.5h

### 1.2 Add `net_amount` column to dbt models
**Decision:** ADD the column (not remove YAML entries) — downstream BI and dashboards need it.
**Formula:** `ROUND((sales + discount)::NUMERIC, 2)` (discount is negative in the ERP, so addition is correct)

**Files:**
- `dbt/models/staging/stg_sales.sql` — Add after line 158 (after `discount`):
  ```sql
  ROUND(({{ gross_sales_col }} + {{ discount_col }})::NUMERIC, 2) AS net_amount,
  ```
  (Use the actual column references from the existing SELECT, likely `gross_sales + subtotal5_discount`)
- `dbt/models/marts/facts/fct_sales.sql` — Add `s.net_amount` to the SELECT from stg_sales (after `discount`)
- `dbt/models/marts/aggs/agg_sales_daily.sql` — Add `ROUND(SUM(f.net_amount)::NUMERIC, 2) AS total_net_amount`
- `dbt/models/marts/aggs/agg_sales_by_customer.sql` — Same
- `dbt/models/marts/aggs/agg_sales_monthly.sql` — Same + update MoM/YoY LAG to use `total_net_amount`
- `dbt/models/marts/aggs/metrics_summary.sql` — Replace deprecated aliases:
  - Line 58: `daily_gross_amount AS daily_net_amount` → compute real `daily_net_amount` from net_amount
  - Line 79: Same for `mtd_net_amount`
  - Line 101: Same for `ytd_net_amount`
- Schema YAMLs — verify descriptions match: `_staging__sources.yml`, `_facts__models.yml`, `_aggs__models.yml`
**Risk:** MEDIUM — changes gold layer schema; Power BI model may need refresh
**Est:** 3h

### 1.3 Update dim_date YAML description
**File:** `dbt/models/marts/dims/_dims__models.yml` line 6
- Change "2023-2025" description to "2023-2030" (SQL already generates through 2030)
**Risk:** NONE
**Est:** 5m

### 1.4 Fix conftest.py scheduler patch (P0 — unblocks all backend tests)
**File:** `tests/conftest.py` line 67
- The `patch("datapulse.scheduler.get_settings", ...)` fails if `apscheduler` import fails
- **Fix approach:** Wrap in try/except or use `create=True` parameter on the patch:
  ```python
  patch("datapulse.scheduler.get_settings", return_value=clean_settings, create=True),
  ```
  Or better: conditionally include the patch only if the module is importable:
  ```python
  _optional_patches = []
  try:
      import datapulse.scheduler  # noqa: F401
      _optional_patches.append("datapulse.scheduler.get_settings")
  except ImportError:
      pass
  ```
**Risk:** LOW — test infrastructure only
**Est:** 30m

### 1.5 Fix frontend TypeScript check
**File:** `frontend/src/__tests__/hooks/use-returns.test.ts` line 15
- Change `result.current.data?.[0].product_name` → `result.current.data?.[0].drug_name`
- Check MSW mock handler (likely in `frontend/src/__tests__/mocks/`) — update mock data to use `drug_name`
**Risk:** NONE
**Est:** 15m

### 1.6 Fix auth environment detection
**Files:**
- `src/datapulse/api/auth.py` line 136: `os.getenv("SENTRY_ENVIRONMENT", "development")` → `settings.sentry_environment`
  (`settings` is already available in scope from line 108: `settings = get_settings()`)
- `src/datapulse/api/deps.py` line 56: Same change. Need to get settings first (import and call `get_settings()`)
- `src/datapulse/core/config.py` line 149 in `warn_if_auth_disabled`: Same change (use `self.sentry_environment`)
**Risk:** LOW — settings field already exists at `config.py:97`
**Est:** 30m

### 1.7 Pass tenant_id to forecasting execution
**Files:**
- `src/datapulse/api/routes/pipeline.py` line 412-413:
  Current: `executor.run_forecasting(run_id=body.run_id)`
  Fix: Need to extract tenant_id from auth context. Check how `execute_bronze` (line ~370) gets it.
  Likely: Add `tenant_id: str = Depends(get_tenant_id)` or extract from request.
  Change to: `executor.run_forecasting(run_id=body.run_id, tenant_id=body.tenant_id)` (if `ExecuteRequest` has `tenant_id`)
  Or: Add `current_user: dict = Depends(get_current_user)` and pass `current_user["tenant_id"]`
**Risk:** LOW — parameter already exists on `executor.run_forecasting` (line 168), just needs passing
**Est:** 30m

### 1.8 Fix bronze loader path traversal
**File:** `src/datapulse/bronze/loader.py` line 52
- Change: `if not str(resolved).startswith(str(resolved_root)):`
- To: `if not resolved.is_relative_to(resolved_root):` (Python 3.9+, project requires 3.11+)
**Risk:** NONE — strictly safer check
**Est:** 10m

### 1.9 Add tenant_id to dedup PARTITION BY
**File:** `dbt/models/staging/stg_sales.sql` line 81
- Change: `PARTITION BY reference_no, date, material, customer, site, quantity`
- To: `PARTITION BY tenant_id, reference_no, date, material, customer, site, quantity`
**Risk:** LOW — may change dedup behavior if cross-tenant duplicates existed (would now be kept)
**Est:** 15m

### 1.10 Fix scheduler tenant hardcoding
**File:** `src/datapulse/scheduler.py` line 193
- Change: `session.execute(sa_text("SET LOCAL app.tenant_id = '1'"))`
- To: Parameterized query. The `_quality_digest` function needs a `tenant_id` parameter (default `"1"` for backward compat).
  For multi-tenant: loop over tenants from a tenant registry query, or accept tenant_id as parameter.
  Minimum fix: `session.execute(sa_text("SET LOCAL app.tenant_id = :tid"), {"tid": tenant_id})`
**Risk:** LOW
**Est:** 30m

### Sprint 1 Verification
```bash
# Backend tests pass
cd /path/to/SAAS && uv run pytest --maxfail=5 -x
# Frontend type check passes
cd frontend && npx tsc --noEmit
# Frontend tests pass
npx vitest run
# dbt models parse successfully
cd dbt && dbt parse
# Quality checks reference correct columns
grep -n "net_sales" src/datapulse/pipeline/quality*.py  # should only appear in bronze context
```

---

## Sprint 2: Security Hardening
**Priority:** P1 — production safety | **Est:** ~10 hours
**Dependencies:** Sprint 1 (auth fix in 1.6)

### 2.1 Docker env vars — fail-fast on missing secrets
**Files:**
- `docker-compose.yml`:
  - `API_KEY: ${API_KEY:-}` → `API_KEY: ${API_KEY:?API_KEY is required}`
  - `AUTH0_CLIENT_SECRET: ${AUTH0_CLIENT_SECRET:-}` → `AUTH0_CLIENT_SECRET: ${AUTH0_CLIENT_SECRET:?AUTH0_CLIENT_SECRET is required}`
  - `PIPELINE_WEBHOOK_SECRET: ${PIPELINE_WEBHOOK_SECRET:-}` → `PIPELINE_WEBHOOK_SECRET: ${PIPELINE_WEBHOOK_SECRET:?PIPELINE_WEBHOOK_SECRET is required}`
- `docker-compose.prod.yml`:
  - Add under `api.environment`: `SENTRY_ENVIRONMENT: production`
  - Change: `image: ...${IMAGE_TAG:-latest}` → `image: ...${IMAGE_TAG:?IMAGE_TAG is required for production}`
**Risk:** MEDIUM — will break `docker compose up` if env vars not set. Update `.env.example` with instructions.
**Est:** 1h

### 2.2 Health endpoint — gate infrastructure details
**File:** `src/datapulse/api/routes/health.py` lines 105-135
- Import `get_current_user` from auth module
- Add optional auth: try to get user from Authorization header; if no header or invalid, return minimal `{"status": overall}`
- If authenticated, return full `{"status": overall, "checks": checks}`
- Keep `/health/live` and `/health/ready` unauthenticated (needed for orchestrator probes)
**Risk:** LOW — additive behavior, existing callers still get status
**Est:** 1.5h

### 2.3 CORS default to empty list
**File:** `src/datapulse/core/config.py` line 55
- Change: `cors_origins: list[str] = ["http://localhost:3000"]`
- To: `cors_origins: list[str] = []`
- Update `.env.example` to document: `CORS_ORIGINS=http://localhost:3000` for dev
- Add warning log in `warn_if_auth_disabled` if cors_origins is empty
**Risk:** MEDIUM — breaks dev setup if CORS_ORIGINS not in .env. Must update docs.
**Est:** 30m

### 2.4 Embed session hardening
**File:** `src/datapulse/api/routes/embed.py`
- After session creation (line ~84), add: `session.execute(text("SET LOCAL statement_timeout = '30s'"))`
- In the `except Exception` block (around line 144), add `session.rollback()` before raising
**Risk:** LOW
**Est:** 30m

### 2.5 Billing webhook session timeout
**File:** `src/datapulse/api/routes/billing.py` after session creation (~line 100)
- Add: `session.execute(text("SET LOCAL statement_timeout = '30s'"))`
**Risk:** LOW
**Est:** 15m

### 2.6 Async SQL blocklist improvements
**File:** `src/datapulse/api/routes/queries.py` lines 39-50
- Add to `_BLOCKED_KEYWORDS` regex: `VACUUM|ANALYZE|LOCK|COMMENT|LISTEN|NOTIFY|PREPARE|DEALLOCATE`
- Add semicolon check: reject queries containing `;` (prevents statement stacking)
- Add comment stripping or rejection: reject queries containing `--` or `/*`
**Risk:** LOW — tightens restrictions only
**Est:** 45m

### 2.7 Notifications SSE — add statement timeout
**File:** `src/datapulse/api/routes/notifications.py` line ~92
- After `SET LOCAL app.tenant_id`, add: `session.execute(sa_text("SET LOCAL statement_timeout = '10s'"))`
- Consider: persistent session per SSE connection (close on disconnect) instead of per-poll creation
**Risk:** LOW
**Est:** 45m

### 2.8 .gitignore additions
**File:** `.gitignore`
- Add:
  ```
  # TLS/SSL certificates and keys
  *.pem
  *.key
  *.crt
  *.p12
  ```
**Risk:** NONE
**Est:** 5m

### 2.9 Sanitize .env.example
**Files:**
- `.env.example`:
  - Lines 42-45: Replace real Sentry DSNs with `https://your-dsn@o0.ingest.sentry.io/0`
  - Line 13: Replace `RAW_SALES_PATH=E:/Data Analysis/sales/RAW FULL` with `RAW_SALES_PATH=/path/to/your/sales/data`
- `frontend/.env.example`: Replace Sentry DSN similarly
**Risk:** NONE
**Est:** 15m

### Sprint 2 Verification
```bash
# Docker compose validates (with .env set)
docker compose config --quiet
docker compose -f docker-compose.yml -f docker-compose.prod.yml config --quiet
# Health endpoint without auth returns minimal response
curl http://localhost:8000/health | jq '.checks'  # should be absent
# CORS empty default
grep "cors_origins.*\[\]" src/datapulse/core/config.py
# Blocklist rejects semicolons
echo "SELECT 1; DROP TABLE x" | python -c "import re; ..."
```

---

## Sprint 3: Testing & CI/CD
**Priority:** P1 — build reliability | **Est:** ~16 hours
**Dependencies:** Sprint 1 (conftest fix in 1.4)

### 3.1 Generate and commit uv.lock
```bash
uv lock
git add uv.lock
```
- Update `Dockerfile` to copy `uv.lock` and use it: `COPY pyproject.toml uv.lock ./` then `uv sync --frozen`
  Or if staying with pip: `uv export --format requirements-txt > requirements.txt` and use that in Dockerfile
**Est:** 1h

### 3.2 Add E2E tests to CI
**File:** `.github/workflows/ci.yml`
- Add new job `e2e` after `frontend` job
- Needs: Playwright browsers installed, frontend dev server running, API mock or real backend
- Use `npx playwright install --with-deps chromium` + `npm run build` + `npx playwright test`
- Start with `continue-on-error: true` initially, then remove once stable
**Est:** 3h

### 3.3 Remove mypy continue-on-error
**File:** `.github/workflows/ci.yml` line ~45
- Remove `continue-on-error: true` from the typecheck job
- May need to fix mypy errors first — run `uv run mypy src/datapulse/` locally to see current state
**Est:** 2h (including fixing any mypy errors)

### 3.4 Raise frontend coverage thresholds
**File:** `frontend/vitest.config.ts` line 16
- Change: `{ statements: 3, branches: 3, functions: 3 }`
- To: `{ statements: 20, branches: 15, functions: 20 }` (realistic starting point)
- Add `lines: 20`
**Est:** 30m

### 3.5 Write tests for scheduler.py
**New file:** `tests/test_scheduler.py`
- Test `run_pipeline` with mocked executor and session
- Test `start_scheduler` / `stop_scheduler` lifecycle
- Test `_health_check` with mocked DB/Redis
- Test `_quality_digest` with mocked session
- Test `_ai_digest` with mocked httpx
- Mock APScheduler to avoid real scheduling
**Est:** 4h

### 3.6 Write tests for async_executor.py
**New file:** `tests/test_async_executor_core.py`
- Test `_run_query_sync` with mocked session and Redis
- Test `submit_query` with mocked thread executor
- Test `get_job_result` with various Redis states
- Test staleness detection
- Test the `_serialise` helper function
**Est:** 3h

### 3.7 Write tests for notifications.py (Slack helpers)
**New file:** `tests/test_notifications_slack.py`
- Mock `httpx.post` and `get_settings().slack_webhook_url`
- Test each notification function
- Test failure handling (webhook URL missing, POST fails)
**Est:** 1.5h

### 3.8 Improve conftest patch robustness
**File:** `tests/conftest.py`
- Replace hardcoded 12-module patch list with dynamic discovery:
  ```python
  import importlib, pkgutil
  _modules_with_get_settings = []
  for importer, modname, ispkg in pkgutil.walk_packages(datapulse.__path__, "datapulse."):
      try:
          mod = importlib.import_module(modname)
          if hasattr(mod, 'get_settings'):
              _modules_with_get_settings.append(f"{modname}.get_settings")
      except ImportError:
          pass
  ```
  Or simpler: just wrap each patch in `contextlib.suppress(Exception)` if the module can't be imported.
**Risk:** MEDIUM — changes test infrastructure
**Est:** 1h

### Sprint 3 Verification
```bash
# All backend tests pass with coverage >= 80%
uv run pytest --cov --cov-fail-under=80
# Frontend tests pass with new thresholds
cd frontend && npx vitest run --coverage
# CI pipeline green (push and check)
git push && gh run watch
# uv.lock exists and is valid
uv sync --frozen
```

---

## Sprint 4: Performance & Architecture
**Priority:** P2 — scalability | **Est:** ~22 hours
**Dependencies:** Sprint 1 (net_amount must exist before optimizing queries that use it)

### 4.1 Rewrite EXTRACT queries to range predicates
**Files:**
- `src/datapulse/analytics/advanced_repository.py` lines 167-175 (heatmap):
  ```sql
  -- FROM:
  WHERE EXTRACT(YEAR FROM full_date) = :year
  -- TO:
  WHERE full_date >= MAKE_DATE(:year, 1, 1)
    AND full_date < MAKE_DATE(:year + 1, 1, 1)
  ```
- `src/datapulse/analytics/repository.py` lines 333-351 (significance):
  Rewrite MoM/YoY queries to use date arithmetic instead of EXTRACT
**Est:** 2h

### 4.2 Reduce Why-Changed from 12 to 4 queries
**File:** `src/datapulse/analytics/diagnostics.py` lines 115-193
- For each dimension, fold `c_total_stmt` and `p_total_stmt` into the main FULL OUTER JOIN CTE as aggregate window functions
- Result: 1 query per dimension instead of 3
**Est:** 3h

### 4.3 Wire with_retry into executor + kill-on-timeout
**Files:**
- `src/datapulse/pipeline/executor.py`:
  - Import `with_retry` from `pipeline.retry`
  - Apply `@with_retry(max_retries=3, transient_exceptions=(ConnectionError, OSError))` to the internal `_load_bronze` helper
  - For `run_dbt`: use `subprocess.Popen` instead of `subprocess.run`, add explicit `proc.kill()` on TimeoutExpired
**Est:** 2h

### 4.4 Add expression indexes for agg table queries
**New file:** `migrations/023_add_expression_indexes.sql`
```sql
CREATE INDEX IF NOT EXISTS idx_agg_product_ym ON public_marts.agg_sales_by_product ((year * 100 + month));
CREATE INDEX IF NOT EXISTS idx_agg_customer_ym ON public_marts.agg_sales_by_customer ((year * 100 + month));
CREATE INDEX IF NOT EXISTS idx_agg_monthly_ym ON public_marts.agg_sales_monthly ((year * 100 + month));
```
**Est:** 30m

### 4.5 Cache get_site_detail
**File:** `src/datapulse/analytics/service.py` line 382
- Add `@cached(ttl=300, prefix=_CACHE_PREFIX)` decorator (same as all other detail methods)
**Est:** 5m

### 4.6 Deterministic dimension keys
**Files:** All 4 dim models:
- `dbt/models/marts/dims/dim_product.sql` line 46
- `dbt/models/marts/dims/dim_customer.sql` line 37
- `dbt/models/marts/dims/dim_staff.sql` line 37
- `dbt/models/marts/dims/dim_site.sql` line 40

Replace `ROW_NUMBER() OVER (ORDER BY ...)::INT AS xxx_key` with:
```sql
-- Option A: Hash-based (deterministic, collision-resistant)
ABS(('x' || LEFT(MD5(r.tenant_id::text || '|' || r.drug_code), 8))::BIT(32)::INT) AS product_key

-- Option B: dbt_utils surrogate key
{{ dbt_utils.generate_surrogate_key(['tenant_id', 'drug_code']) }} AS product_key
```
**Risk:** HIGH — changes ALL foreign keys in fct_sales and agg tables. Requires full refresh of entire marts layer. Power BI model needs reconnecting.
**Mitigation:** Run `dbt run --full-refresh` after changes. Coordinate with BI team.
**Est:** 4h

### 4.7 Pipeline concurrency lock
**File:** `src/datapulse/scheduler.py`
- At start of `run_pipeline`, acquire PostgreSQL advisory lock:
  ```python
  session.execute(sa_text("SELECT pg_try_advisory_lock(42)"))
  # Check result; if False, another pipeline is running — abort or queue
  ```
- Release in finally block: `SELECT pg_advisory_unlock(42)`
**Est:** 1.5h

### 4.8 Bind run_id to structlog context
**File:** `src/datapulse/scheduler.py` line ~62
- After creating `run_id_str`, add:
  ```python
  from structlog.contextvars import bind_contextvars, clear_contextvars
  bind_contextvars(run_id=run_id_str, tenant_id=str(tenant_id))
  ```
- In finally block: `clear_contextvars()`
**File:** `src/datapulse/logging.py` — ensure `merge_contextvars` is in the processor chain (already is, line 41)
**Est:** 30m

### 4.9 Unify quality.py and quality_engine.py
**Files:**
- `src/datapulse/pipeline/quality_engine.py` — make this the canonical implementation
- `src/datapulse/pipeline/quality.py` — keep as thin wrapper that delegates to engine
- `src/datapulse/pipeline/quality_service.py` — update `run_checks_for_stage` to use `quality_engine.run_configurable_checks`
- Move freshness check from engine defaults into `STAGE_CHECKS` in service
- Deprecate duplicate functions in `quality.py` (or delete)
**Risk:** MEDIUM — changes quality gate behavior
**Est:** 4h

### 4.10 KPI summary query consolidation
**File:** `src/datapulse/analytics/repository.py`
- Unify `get_kpi_summary` (line 158) and `get_kpi_summary_range` (line 394) via shared CTE builder
- Fold `_compute_growth_significance` queries into main CTE (reduces 3 round-trips to 1)
**Est:** 4h

### Sprint 4 Verification
```bash
# Performance: compare query explain plans before/after
EXPLAIN ANALYZE SELECT ... FROM metrics_summary WHERE full_date >= ... ;
# Dimension keys are stable across rebuilds
dbt run --full-refresh && dbt run --full-refresh  # keys should be identical
# Pipeline concurrency: try running 2 pipelines simultaneously
# Quality checks: run pipeline through all stages, verify quality gate passes
# All tests still pass
uv run pytest --cov --cov-fail-under=80
```

---

## Sprint 5: Frontend Quality
**Priority:** P2 — UX and accessibility | **Est:** ~14 hours
**Dependencies:** Sprint 1 (test fix in 1.5)

### 5.1 Extract shared ChartTooltip component
**New file:** `frontend/src/components/shared/chart-tooltip.tsx`
- Create parameterized `<ChartTooltip>` accepting: `active`, `payload`, `label`, `valueFormatter`, `accentClass`
- Update 5 chart files to import and use it:
  - `dashboard/daily-trend-chart.tsx` (delete lines ~44-64)
  - `dashboard/monthly-trend-chart.tsx` (delete lines ~44-64)
  - `dashboard/billing-breakdown-chart.tsx` (delete lines ~22-40)
  - `dashboard/customer-type-chart.tsx` (delete lines ~22-40)
  - `shared/ranking-chart.tsx` (delete lines ~23-40)
**Also extract:**
- `frontend/src/components/shared/chart-type-switcher.tsx` — from daily/monthly trend charts
- `frontend/src/lib/chart-utils.ts` — extract `findPeakValley()` function
**Est:** 2h

### 5.2 Delete dead hooks
**Delete files:**
- `frontend/src/hooks/use-monthly-trend.ts`
- `frontend/src/hooks/use-ai-status.ts`
- `frontend/src/hooks/use-track.ts`
**Verification:** `grep -r "use-monthly-trend\|use-ai-status\|use-track" frontend/src/` returns empty
**Est:** 10m

### 5.3 Fix use-billing.ts fetcher
**File:** `frontend/src/hooks/use-billing.ts` line ~7
- Change: `fetchAPI<BillingStatus>`
- To: `() => fetchAPI<BillingStatus>("/api/v1/billing/status")`
**Est:** 5m

### 5.4 Reuse types/api.ts in use-dashboard.ts
**File:** `frontend/src/hooks/use-dashboard.ts`
- Import `KPISummary`, `TrendResult`, `RankingResult`, `RankingItem`, `TimeSeriesPoint` from `@/types/api`
- Replace inline `DashboardData` sub-types with imported types
- Keep `filter_options` type inline (no equivalent in api.ts)
**Est:** 1h

### 5.5 Add error states to 8 components
**Pattern:** Import `ErrorRetry` from `@/components/error-retry`, check hook's `error` return, show `<ErrorRetry>` on error.

**Files to modify:**
1. `frontend/src/components/customers/rfm-matrix.tsx`
2. `frontend/src/components/customers/segment-funnel.tsx`
3. `frontend/src/components/dashboard/customer-type-chart.tsx`
4. `frontend/src/components/dashboard/insight-chips.tsx`
5. `frontend/src/components/staff/gamified-leaderboard.tsx`
6. `frontend/src/components/customers/health-dashboard.tsx`
7. `frontend/src/components/alerts/alerts-overview.tsx`
8. `frontend/src/components/goals/goals-overview.tsx`

For each: add `if (error) return <ErrorRetry title="Failed to load" onRetry={() => mutate()} />;` after the loading check.
**Est:** 3h

### 5.6 Add aria-current to sidebar nav
**File:** `frontend/src/components/layout/sidebar.tsx` around line 120
- On the active `<Link>`, add: `aria-current={isActive ? "page" : undefined}`
**Est:** 15m

### 5.7 Accessible color indicators
**Files:**
- `frontend/src/components/customers/health-dashboard.tsx`:
  - Add descriptive icon (e.g., shield-check for Thriving, alert-triangle for At Risk) next to each band
  - Add `aria-label` to the color band divs
- `frontend/src/components/alerts/alerts-overview.tsx`:
  - Add `aria-label={severity}` to severity icon container
**Est:** 1.5h

### 5.8 Standardize chart colors on CSS variables
**Files:** Multiple chart components
- Create `frontend/src/lib/chart-colors.ts`:
  ```ts
  export const CHART_COLORS = {
    blue: "var(--chart-blue)",
    amber: "var(--chart-amber)",
    green: "var(--growth-green)",
    red: "var(--growth-red)",
  } as const;
  ```
- Replace hardcoded hex values in: `customer-type-chart.tsx`, `segment-funnel.tsx`, `rfm-matrix.tsx`, `pareto-chart.tsx`, `abc-summary.tsx`, `goals-overview.tsx`, `gamified-leaderboard.tsx`, `return-rate-gauge.tsx`
- Note: Recharts SVG `fill`/`stroke` requires resolved hex values, not CSS vars. Use `useChartTheme` hook or resolve vars at render time via `getComputedStyle`.
**Est:** 3h

### 5.9 Fix use-forecast error handling
**File:** `frontend/src/hooks/use-forecast.ts`
- Ensure `error` is returned and consumers check it
- In `ForecastCard` and other consuming components: add error state rendering
**Est:** 45m

### 5.10 Delete dead backend code
**Files to delete:**
- `src/datapulse/pipeline/anomaly.py` — superseded by `anomalies/` package, zero imports in src/
**Files to document (NOT delete — they'll be wired in Sprint 4):**
- `src/datapulse/pipeline/rollback.py` — add docstring noting it's available for manual use
- `src/datapulse/pipeline/retry.py` — will be wired into executor in Sprint 4.3
**Est:** 15m

### Sprint 5 Verification
```bash
# Frontend builds without errors
cd frontend && npm run build
# Type check passes
npx tsc --noEmit
# Unit tests pass
npx vitest run
# No dead hook imports
grep -r "use-monthly-trend\|use-ai-status\|use-track" frontend/src/
# Accessibility audit (manual)
# Open dashboard in browser, use Lighthouse accessibility audit
```

---

## Sprint 6: Documentation & Polish
**Priority:** P3 — maintainability | **Est:** ~8 hours
**Dependencies:** Sprints 1-5

### 6.1 Fix README claims
**File:** `README.md`
- Update page count from 14 to 22
- Clarify Silver/Staging naming: add note that "Silver layer" = `staging/` directory and `public_staging` schema
- Update any other stale numbers
**Est:** 30m

### 6.2 Update CHANGELOG
**File:** `CHANGELOG.md`
- Add `[v0.7.0]` section documenting all features added since v0.6.0:
  billing, annotations, embed, onboarding, notifications_center, forecasting, targets, views, android app, explore, dashboard_layouts
- Fix path reference for "The Great Fix" (spaces → kebab-case)
**Est:** 1h

### 6.3 Backend DRY improvements
**Files:**
- Extract shared `_serialise()` from `reports/template_engine.py:340` and `tasks/async_executor.py:55` into `src/datapulse/core/serializers.py`
- Both files import from new location
**Est:** 1h

### 6.4 Move misplaced dbt model
- Move `dbt/models/marts/aggs/feat_customer_health.sql` to `dbt/models/marts/features/`
- Add entry to `_features__models.yml`
- Remove any entry from `_aggs__models.yml` (if present)
**Est:** 30m

### 6.5 Logger improvements
**File:** `src/datapulse/logging.py`
- In `get_logger(name)`: bind the module name to the event dict:
  ```python
  def get_logger(name: str):
      return structlog.get_logger().bind(module=name)
  ```
- Enhance `_mask_sensitive_fields` to recursively check nested dicts:
  ```python
  def _mask_sensitive_fields(logger, method_name, event_dict):
      for key, value in event_dict.items():
          if key.lower() in _SENSITIVE_KEYS:
              event_dict[key] = "***REDACTED***"
          elif isinstance(value, dict):
              event_dict[key] = _mask_sensitive_fields(logger, method_name, dict(value))
      return event_dict
  ```
**Est:** 1h

### 6.6 Import pipeline alignment
**File:** `src/datapulse/import_pipeline/validator.py` line 8
- Remove `.xls` from `ALLOWED_EXTENSIONS`: `{".csv", ".xlsx"}`
- Or: implement actual `.xls` reading support in reader.py (lower priority)
**Est:** 15m

### 6.7 Frontend polish (lower priority items)
- Loading skeleton shape-matching for chart components
- Dark mode chart contrast audit (run Lighthouse, fix <4.5:1 contrast ratios)
- KPI card visual hierarchy (make total revenue card larger/more prominent)
**Est:** 3h

### 6.8 Wire dbt test into quality gate
**File:** `dbt/tests/assert_unknown_dimension_below_threshold.sql`
- Add `tags: ['quality_gate']` in test config
- Or: in `quality.py` STAGE_CHECKS["gold"], add explicit call with `--select test_type:singular`
**Est:** 30m

### Sprint 6 Verification
```bash
# README accuracy
grep -c "page.tsx" frontend/src/app/**/page.tsx  # should match README count
# CHANGELOG completeness
cat CHANGELOG.md | head -100
# Logger test
uv run python -c "from datapulse.logging import get_logger; l = get_logger('test'); l.info('hello', database_url='secret')"
# dbt test runs quality gate test
dbt test --select tag:quality_gate
```

---

## Deferred Items (Future Reference)

These are documented for future planning but explicitly excluded from current execution.

### D1. Next.js 14 → 15 Upgrade
**Rationale:** Next.js 14 is in maintenance. v15 brings React 19, Turbopack stable, improved caching.
**Effort:** ~16h (breaking changes in route handlers, metadata API, caching defaults)
**When:** After Sprint 6, in a dedicated migration sprint
**Key risks:** `next-auth` v4 incompatible with Next.js 15; must migrate to Auth.js v5 first (D2)

### D2. NextAuth v4 → Auth.js v5 (next-auth@5)
**Rationale:** NextAuth v4 is EOL. Auth.js v5 has different API surface, different config pattern.
**Effort:** ~12h (new `auth.ts` config, middleware changes, session handling)
**When:** Before Next.js 15 upgrade (D1). Can be done independently.
**Files:** `frontend/src/lib/auth.ts`, `frontend/src/middleware.ts`, API route handlers

### D3. ESLint 8 → 9 (Flat Config)
**Rationale:** ESLint 8 EOL October 2024. v9 uses flat config system.
**Effort:** ~4h (rewrite `.eslintrc.json` to `eslint.config.mjs`, update plugins)
**When:** Can be done anytime. Low risk.

### D4. psycopg2-binary → psycopg3
**Rationale:** psycopg2-binary warned against for production by maintainers. psycopg3 is the modern successor.
**Effort:** ~8h (different API, async support, connection pool changes)
**When:** During a backend-focused sprint. Test thoroughly with all SQL queries.
**Key risks:** Different parameter substitution syntax, pool configuration

### D5. APScheduler 3 → 4
**Rationale:** APScheduler 3.x is maintenance-only. v4 has new architecture (data stores, event brokers).
**Effort:** ~6h (new API, different job store configuration)
**When:** After scheduler tests are written (Sprint 3.5). The tests will catch regressions.

### D6. Autocommit for Read-Only Analytics Sessions
**Rationale:** Every analytics query currently opens a transaction. Autocommit would reduce overhead.
**Effort:** ~4h (create separate engine with `isolation_level="AUTOCOMMIT"`, use for read-only deps)
**When:** During performance optimization. Profile first to confirm actual benefit.

---

## Execution Order & Dependencies

```
Sprint 1 (CRITICAL)  ──────────────────────────┐
  No dependencies                                │
                                                  v
Sprint 2 (Security)  ←── depends on 1.6 (auth) ──┤
                                                  │
Sprint 3 (Testing)   ←── depends on 1.4 (conftest)│
                                                  v
Sprint 4 (Performance) ←── depends on 1.2 (net_amount exists)
                                                  │
Sprint 5 (Frontend)  ←── depends on 1.5 (type fix)│
                                                  v
Sprint 6 (Docs/Polish) ←── depends on all above
```

Sprints 2, 3, and 5 can run in parallel after Sprint 1 completes.
Sprint 4 should wait for Sprint 1 (needs net_amount column to exist).
Sprint 6 runs last as cleanup.

---

## Risk Summary

| Risk | Severity | Mitigation |
|------|----------|------------|
| Sprint 1.2 changes gold layer schema | HIGH | Run `dbt run --full-refresh` after; coordinate with BI team |
| Sprint 4.6 changes ALL dimension keys | HIGH | Full refresh required; Power BI model needs reconnecting |
| Sprint 2.1 breaks `docker compose up` without .env | MEDIUM | Update .env.example with required vars and instructions |
| Sprint 2.3 breaks dev CORS without .env | MEDIUM | Document in .env.example |
| Sprint 4.9 changes quality gate behavior | MEDIUM | Test pipeline end-to-end before merging |
| Sprint 3.3 may surface hidden mypy errors | MEDIUM | Fix errors before removing continue-on-error |

---

## Total Effort Estimate

| Sprint | Hours | Priority |
|--------|:-----:|----------|
| Sprint 1: Pipeline & Data | 12h | P0 |
| Sprint 2: Security | 10h | P1 |
| Sprint 3: Testing & CI/CD | 16h | P1 |
| Sprint 4: Performance | 22h | P2 |
| Sprint 5: Frontend | 14h | P2 |
| Sprint 6: Docs & Polish | 8h | P3 |
| **Total** | **~82h** | |
