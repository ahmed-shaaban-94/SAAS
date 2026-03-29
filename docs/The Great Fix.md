# The Great Fix — DataPulse Full Project Remediation Plan

## EXECUTION DIRECTIVE
**ALL work MUST use Opus model at maximum power.**
- Every Agent call: `model: "opus"`
- Every subagent: `model: "opus"`
- No haiku, no sonnet — Opus only for all phases
- Use parallel agents where phases are independent (C, D, E can run simultaneously)
- Each agent gets full, detailed context — no shortcuts

---

## Context

A comprehensive 6-agent Opus scan of the DataPulse SaaS project identified **10 CRITICAL, 29 HIGH, 44 MEDIUM, and 15 LOW** findings across security, architecture, database, Docker, frontend, and Python code quality. This plan addresses all CRITICAL and HIGH issues, plus impactful MEDIUM fixes, organized into 6 phases with ~31 commits.

**Scan date:** 2026-03-29
**Scan agents:** Architecture, Security, Python Quality, Database, TypeScript/Frontend, Docker Infrastructure
**All agents used:** Claude Opus 4.6 (1M context)

**Key blockers:** No API authentication, RLS bypassed at app layer, bronze loader blocks API, dim_site bug causes silent data loss, KPI cards ignore filters, no fetch timeout.

---

## Scan Results Summary

| Severity | Count | Examples |
|----------|-------|---------|
| CRITICAL | 10 | No API auth, RLS bypassed, dim_site NULL tenant_id, no fetch timeout, no .dockerignore |
| HIGH | 29 | No rate limiting, single Uvicorn worker, missing indexes, KPI filter bug, no mobile nav |
| MEDIUM | 44 | Duplicate code, error message leaks, missing ARIA labels, intermediate column leak |
| LOW | 15 | Cosmetic issues, minor inconsistencies |

### Bugs Found
| Bug | Severity | Location |
|-----|----------|----------|
| KPI cards ignore date filters | HIGH | `frontend/src/hooks/use-summary.ts` |
| dim_site Unknown member invisible to RLS readers | CRITICAL | `dbt/models/marts/dims/dim_site.sql:215` |
| daily_unique_customers double-counts across grain | MEDIUM | `dbt/models/marts/aggs/metrics_summary.sql:14` |

### What's Done Well
- Immutable Pydantic models (`frozen=True` everywhere)
- Parameterized SQL (zero user input interpolated into SQL)
- Column whitelist in bronze loader prevents injection
- Path traversal protection (`_jail_source_dir` validator)
- Docker ports all bound to `127.0.0.1`
- RLS design: `FORCE ROW LEVEL SECURITY`, fail-closed `NULLIF` pattern
- Financial precision: `NUMERIC(18,4)` + `Decimal` throughout
- dbt organization follows Kimball methodology
- No XSS vectors: no `dangerouslySetInnerHTML` in React
- 95%+ Python test coverage

---

## Phase A: Shared Infrastructure (3 commits, no dependencies)

### A1. Extract shared types + fix path traversal
**Create** `src/datapulse/types.py`:
- Move `JsonDecimal = Annotated[Decimal, PlainSerializer(float, return_type=float)]` from `analytics/models.py:16` and `pipeline/models.py:15`
- Extract `validate_source_dir(v: str, allowed_root: str) -> str` from `pipeline/models.py:88-100,121-133`
- **Security fix**: replace `str(normalized).startswith(str(allowed_root))` with `PurePosixPath.is_relative_to()` (Python 3.9+)

**Modify** `src/datapulse/analytics/models.py`: import `JsonDecimal` from `datapulse.types`, remove local definition
**Modify** `src/datapulse/pipeline/models.py`: import both, simplify both `_jail_source_dir` validators to call shared function

### A2. Fix config.py security + add pool settings
**Modify** `src/datapulse/config.py`:
- Remove default from `database_url` (currently `"postgresql://datapulse:CHANGEME@..."` at line 13) — make required with no default
- Add: `db_pool_size: int = 10`, `db_pool_max_overflow: int = 20`, `db_pool_timeout: int = 30`, `db_pool_recycle: int = 1800`
- Add: `log_format: str = "console"`, `api_key: str = ""`
- Add `API_KEY=` to `.env`

**Modify** `src/datapulse/logging.py`: accept `log_format` param instead of `os.getenv("LOG_FORMAT")`

### A3. Fix deps.py — pooling, engine, logging init
**Modify** `src/datapulse/api/deps.py`:
- Rename `_get_engine` -> `get_engine` (public — imported by `health.py:8`)
- Add pool params to `create_engine()`: `pool_size`, `max_overflow`, `pool_timeout`, `pool_recycle` from config
**Modify** `src/datapulse/api/routes/health.py`: update import `_get_engine` -> `get_engine`
**Modify** `src/datapulse/api/app.py`: call `setup_logging(settings.log_format)` at top of `create_app()`

---

## Phase B: API Security (5 commits, depends on A2)

### B1. Add API key authentication
**Create** `src/datapulse/api/auth.py`:
- `require_api_key` dependency: check `X-API-Key` header vs `settings.api_key`
- Skip auth if `api_key` is empty (dev mode)
**Modify** `src/datapulse/api/routes/pipeline.py`: apply to POST/PATCH endpoints (lines 98, 106, 120, 170, 182, 192, 218)

### B2. Add webhook secret validation
**Modify** `src/datapulse/api/auth.py`: add `require_pipeline_token` dependency checking `X-Pipeline-Token`
**Modify** `src/datapulse/api/routes/pipeline.py`: apply to `/execute/*` and `/trigger` endpoints

### B3. Fix CORS + add security headers
**Modify** `src/datapulse/api/app.py`:
- Line 33: `allow_headers=["*"]` -> `["Content-Type", "Authorization", "X-API-Key", "X-Pipeline-Token"]`
- Add security headers middleware: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`

### B4. Add rate limiting
**Modify** `pyproject.toml`: add `slowapi>=0.1.9` dependency
**Modify** `src/datapulse/api/app.py`: configure limiter (60/min analytics, 5/min pipeline mutations, 30/min pipeline reads)

### B5. Sanitize error messages
**Modify** `src/datapulse/pipeline/quality_service.py:97`: generic message, log full exc server-side
**Modify** `src/datapulse/pipeline/executor.py`: add `_sanitize_error()` helper, apply at lines 60, 93-100, 111, 121
**Modify** `src/datapulse/api/routes/pipeline.py`: redact `.error` field before returning to clients

---

## Phase C: Database + dbt (8 commits, independent — can run parallel with B, D, E)

### C1. Fix dim_site NULL tenant_id bug (CRITICAL)
**Modify** `dbt/models/marts/dims/dim_site.sql:215`: `NULL::INT AS tenant_id` -> `1 AS tenant_id`

### C2. Tenant-scope fct_sales JOINs
**Modify** `dbt/models/marts/facts/fct_sales.sql`:
- Add `tenant_id` to dim_product, dim_customer, dim_site, dim_staff CTEs (lines 26-44)
- Add `AND s.tenant_id = X.tenant_id` to 4 JOIN conditions (lines 76-79)
- dim_billing JOIN stays unchanged (no tenant_id in dim_billing)

### C3. Add tenant_id + RLS to all 8 agg tables
**Modify** all 8 files in `dbt/models/marts/aggs/`:
- Add `f.tenant_id` (or appropriate source) to SELECT + GROUP BY
- Carry `tenant_id` through intermediate CTEs to final SELECT
- Add 6-statement RLS post_hook (use optimized `(SELECT ...)` wrapper from start):
```sql
post_hook=[
    "ALTER TABLE {{ this }} ENABLE ROW LEVEL SECURITY",
    "ALTER TABLE {{ this }} FORCE ROW LEVEL SECURITY",
    "DROP POLICY IF EXISTS owner_all ON {{ this }}",
    "CREATE POLICY owner_all ON {{ this }} FOR ALL TO datapulse USING (true) WITH CHECK (true)",
    "DROP POLICY IF EXISTS reader_tenant ON {{ this }}",
    "CREATE POLICY reader_tenant ON {{ this }} FOR SELECT TO datapulse_reader USING (tenant_id = (SELECT NULLIF(current_setting('app.tenant_id', true), '')::INT))"
]
```
- Files: `agg_sales_daily.sql`, `agg_sales_monthly.sql`, `agg_sales_by_product.sql`, `agg_sales_by_customer.sql`, `agg_sales_by_site.sql`, `agg_sales_by_staff.sql`, `agg_returns.sql`, `metrics_summary.sql`

### C4. Fix RLS performance on existing models
**Modify** 5 files: `dim_customer.sql`, `dim_product.sql`, `dim_site.sql`, `dim_staff.sql`, `fct_sales.sql`
- In each `reader_tenant` policy USING clause: wrap `current_setting(...)` in `(SELECT ...)` subquery
- Before: `USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT)`
- After: `USING (tenant_id = (SELECT NULLIF(current_setting('app.tenant_id', true), '')::INT))`

### C5. Add indexes to fct_sales
**Modify** `dbt/models/marts/facts/fct_sales.sql`: append to post_hook array:
```sql
"CREATE INDEX IF NOT EXISTS idx_fct_sales_date_key ON {{ this }} (date_key)",
"CREATE INDEX IF NOT EXISTS idx_fct_sales_tenant_id ON {{ this }} (tenant_id)",
"CREATE INDEX IF NOT EXISTS idx_fct_sales_product_key ON {{ this }} (product_key)",
"CREATE INDEX IF NOT EXISTS idx_fct_sales_customer_key ON {{ this }} (customer_key)"
```

### C6. Fix metrics_summary daily_unique_customers double-count
**Modify** `dbt/models/marts/aggs/metrics_summary.sql:14-15`:
- Replace `SUM(a.unique_customers)` with subquery: `(SELECT COUNT(DISTINCT customer_key) FROM {{ ref('fct_sales') }} WHERE date_key = d.date_key)`
- This fixes the double-count where a customer at 2 sites on the same day was counted twice

### C7. Fix agg_sales_monthly intermediate column leak
**Modify** `dbt/models/marts/aggs/agg_sales_monthly.sql:54-55`:
- Replace `SELECT g.*` with explicit column list
- Exclude `prev_month_net` and `prev_year_net` (intermediate LAG values only needed for growth calculation)

### C8. Tenant isolation middleware
**Modify** `src/datapulse/api/deps.py` `get_db_session()`:
- After creating session, execute: `session.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": str(tenant_id)})`
- `tenant_id` derived from authenticated context (Phase B auth) with fallback to `1` for dev

---

## Phase D: Docker Infrastructure (4 commits, independent — can run parallel with B, C, E)

### D1. Create root .dockerignore
**Create** `.dockerignore`:
```
.env
.env.*
.git
data/
notebooks/
frontend/
htmlcov/
.coverage
.pytest_cache/
__pycache__
*.pyc
docs/
n8n/
```

### D2. Multi-stage Dockerfile
**Modify** `Dockerfile`: split into 3 targets:
- `base`: python:3.12-slim-bookworm, git, pip, copy pyproject.toml + src/
- `api`: extends base, `pip install "."` (no jupyterlab), non-root user, uvicorn CMD
- `app`: extends base, `pip install "." jupyterlab`, non-root user, tail CMD
**Modify** `docker-compose.yml`:
- `api` service: add `target: api`
- `app` service: add `target: app`

### D3. Frontend Dockerfile non-root user
**Modify** `frontend/Dockerfile` production stage (line 20+):
```dockerfile
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
COPY --from=builder --chown=nextjs:nodejs /app/public ./public
USER nextjs
```

### D4. Docker-compose hardening
**Modify** `docker-compose.yml`:
- Add `deploy.resources.limits` to all 7 services (postgres 2G, api 512M, app 2G, frontend 512M, n8n 512M, redis 256M, pgadmin 256M)
- Add network segmentation: `backend` network (postgres, redis, app, api, n8n, pgadmin), `frontend-net` (api, frontend)
- Line 70: `pg_isready -U datapulse` -> `pg_isready -U ${POSTGRES_USER:-datapulse}`
- Line 76: `dpage/pgadmin4:latest` -> `dpage/pgadmin4:8.14`
- Line 128: Redis healthcheck: replace `-a ${REDIS_PASSWORD}` with `REDISCLI_AUTH` env var
- Add healthcheck to `app` service

---

## Phase E: Frontend (8 commits, independent — can run parallel with B, C, D)

### E1. Add fetch timeout (CRITICAL)
**Modify** `frontend/src/lib/api-client.ts`:
- In both `fetchAPI` and `postAPI`: create `AbortController`, set 15s timeout via `setTimeout(() => controller.abort(), 15_000)`, pass `{ signal: controller.signal }` to `fetch()`, `clearTimeout` after response

### E2. Fix useSummary filter bug (HIGH — functional bug: KPI cards ignore date filters)
**Modify** `frontend/src/hooks/use-summary.ts`:
- Accept `filters?: FilterParams` parameter
- Build query string from filters using `buildQueryString`
- Include filters in SWR key
**Modify** `frontend/src/components/dashboard/kpi-grid.tsx:9`:
- Import and call `useFilters()` from filter context
- Pass `filters` to `useSummary(filters)`

### E3. Add mobile navigation (HIGH — no nav below 1024px)
**Modify** `frontend/src/components/layout/sidebar.tsx`:
- Add state: `const [mobileOpen, setMobileOpen] = useState(false)`
- Add hamburger button: visible on `lg:hidden`, toggles `mobileOpen`
- Add overlay + slide-out drawer for mobile, closes on nav item click
- Keep existing `hidden lg:flex` for desktop sidebar

### E4. Fix ErrorBoundary logging
**Modify** `frontend/src/components/error-boundary.tsx`:
- Add `componentDidCatch(error: Error, errorInfo: React.ErrorInfo)` method
- Log: `console.error("ErrorBoundary caught:", error, errorInfo)`

### E5. Fix trigger-button setTimeout leak
**Modify** `frontend/src/components/pipeline/trigger-button.tsx`:
- Add `const timeoutRef = useRef<NodeJS.Timeout | null>(null)`
- Store timeout: `timeoutRef.current = setTimeout(...)`
- Add cleanup: `useEffect(() => () => { if (timeoutRef.current) clearTimeout(timeoutRef.current) }, [])`

### E6. Extract formatDuration to formatters.ts
**Modify** `frontend/src/lib/formatters.ts`: add:
```ts
export function formatDuration(seconds: number | null): string {
  if (seconds == null) return "-";
  if (seconds < 60) return `${Math.round(seconds)}s`;
  const mins = Math.floor(seconds / 60);
  const secs = Math.round(seconds % 60);
  return secs > 0 ? `${mins}m ${secs}s` : `${mins}m`;
}
```
**Modify** `frontend/src/components/pipeline/pipeline-overview.tsx`: remove local `formatDuration` (lines 5-9), import from formatters
**Modify** `frontend/src/components/pipeline/run-history-table.tsx`: remove local `formatDuration` (lines 16-21), import from formatters

### E7. Tailwind + CSS cleanup
**Modify** `frontend/src/app/globals.css`: remove duplicate `@keyframes fadeIn` and `@keyframes slideUp` (lines ~45-58) and manual `.animate-fade-in`/`.animate-slide-up` classes — already defined in `tailwind.config.ts`
**Modify** `frontend/tailwind.config.ts:19-20`: rename `blue: "#2196F3"` -> `chart-blue: "#2196F3"`, `amber: "#FFB300"` -> `chart-amber: "#FFB300"` to avoid overriding Tailwind built-in color scales
**Modify** all files referencing `bg-blue`/`text-blue`/`bg-amber`/`text-amber` -> `bg-chart-blue`/`text-chart-blue`/`bg-chart-amber`/`text-chart-amber`
**Modify** `frontend/src/lib/date-utils.ts:1`: remove unused `parse` import from date-fns

### E8. Sanitize error display + remove console.error
**Modify** 4 overview components:
- `frontend/src/components/products/product-overview.tsx:33,38`: remove `console.error`, replace `error.message` with `"Failed to load data. Please try again."`
- `frontend/src/components/customers/customer-overview.tsx:33,38`: same
- `frontend/src/components/staff/staff-overview.tsx:33,38`: same
- `frontend/src/components/sites/site-overview.tsx:32,38`: same

---

## Phase F: Python Code Quality (3 commits, depends on A1)

### F1. Deduplicate analytics repository
**Modify** `src/datapulse/analytics/repository.py`:
- Extract `_get_ranking(self, table: str, key_col: str, name_col: str, filters: AnalyticsFilter | None) -> RankingResult` helper
- Replace `get_top_products` (line 306), `get_top_customers` (323), `get_top_staff` (341), `get_site_performance` (359) with calls to `_get_ranking`
- Add whitelist: `_ALLOWED_DATE_COLUMNS = frozenset({"date_key"})` and validate `date_column` in `_build_where`

### F2. Pipeline model validation
**Modify** `src/datapulse/pipeline/models.py`:
- Add `VALID_RUN_TYPES = frozenset({"full", "bronze", "staging", "marts"})` and `field_validator("run_type")` on `PipelineRunCreate`
- Add `field_validator("status")` on `PipelineRunUpdate` using existing `VALID_STATUSES`
**Modify** `src/datapulse/pipeline/repository.py:46`: type `_row_to_response(row: Any)`
**Modify** `src/datapulse/pipeline/quality_repository.py:38`: type `_row_to_response(row: Any)`

### F3. Batch quality check inserts
**Modify** `src/datapulse/pipeline/quality_repository.py:80-91`:
- Build all params upfront in a list
- Use multi-row VALUES INSERT or `executemany` pattern
- Single `commit()` at end (already exists at line 93)

---

## Execution Order & Parallelism

```
SEQUENTIAL (must run in order):
  A1 -> A2 -> A3 -> B1 -> B2 -> B3 -> B4 -> B5
  A1 -> F1 -> F2 -> F3

PARALLEL (independent file domains — launch as parallel Opus agents):
  C1 -> C2 -> C3 -> C4 -> C5 -> C6 -> C7 -> C8   (dbt/SQL files only)
  D1 -> D2 -> D3 -> D4                              (Docker files only)
  E1 -> E2 -> E3 -> E4 -> E5 -> E6 -> E7 -> E8     (frontend/src files only)
```

**Strategy**: Run Phase A first (foundation). Then launch C, D, E as parallel Opus agents in worktrees. Then B sequentially (needs A). Then F (needs A1).

---

## Verification

| Phase | Verification Command |
|-------|---------------------|
| A | `python -c "from datapulse.types import JsonDecimal, validate_source_dir"` + `pytest tests/ -v` |
| B | `curl -X POST localhost:8000/api/v1/pipeline/trigger` -> expect 401/403 |
| C | `dbt run && dbt test` — all models build, verify `SELECT * FROM public_marts.dim_site WHERE site_key = -1` shows tenant_id=1 |
| D | `docker compose build && docker compose up -d` — all 7 services healthy within 60s |
| E | `cd frontend && npm run build && npx playwright test` — build clean, E2E pass, KPI responds to filters |
| F | `pytest tests/ -v --tb=short` — all pass, coverage >=80% |
| **Full** | `docker compose down -v && docker compose up -d --build` -> load bronze -> run dbt -> verify dashboard |

---

## Files Modified/Created (Complete List)

### Created (new files)
- `src/datapulse/types.py`
- `src/datapulse/api/auth.py`
- `.dockerignore`

### Modified (Python — 12 files)
- `src/datapulse/config.py`
- `src/datapulse/logging.py`
- `src/datapulse/analytics/models.py`
- `src/datapulse/analytics/repository.py`
- `src/datapulse/pipeline/models.py`
- `src/datapulse/pipeline/executor.py`
- `src/datapulse/pipeline/quality_service.py`
- `src/datapulse/pipeline/repository.py`
- `src/datapulse/pipeline/quality_repository.py`
- `src/datapulse/api/app.py`
- `src/datapulse/api/deps.py`
- `src/datapulse/api/routes/pipeline.py`
- `src/datapulse/api/routes/health.py`

### Modified (dbt/SQL — 14 files)
- `dbt/models/marts/dims/dim_site.sql`
- `dbt/models/marts/dims/dim_customer.sql`
- `dbt/models/marts/dims/dim_product.sql`
- `dbt/models/marts/dims/dim_staff.sql`
- `dbt/models/marts/facts/fct_sales.sql`
- `dbt/models/marts/aggs/agg_sales_daily.sql`
- `dbt/models/marts/aggs/agg_sales_monthly.sql`
- `dbt/models/marts/aggs/agg_sales_by_product.sql`
- `dbt/models/marts/aggs/agg_sales_by_customer.sql`
- `dbt/models/marts/aggs/agg_sales_by_site.sql`
- `dbt/models/marts/aggs/agg_sales_by_staff.sql`
- `dbt/models/marts/aggs/agg_returns.sql`
- `dbt/models/marts/aggs/metrics_summary.sql`

### Modified (Docker — 3 files)
- `Dockerfile`
- `frontend/Dockerfile`
- `docker-compose.yml`

### Modified (Frontend — 14 files)
- `frontend/src/lib/api-client.ts`
- `frontend/src/lib/formatters.ts`
- `frontend/src/lib/date-utils.ts`
- `frontend/src/hooks/use-summary.ts`
- `frontend/src/components/dashboard/kpi-grid.tsx`
- `frontend/src/components/layout/sidebar.tsx`
- `frontend/src/components/error-boundary.tsx`
- `frontend/src/components/pipeline/trigger-button.tsx`
- `frontend/src/components/pipeline/pipeline-overview.tsx`
- `frontend/src/components/pipeline/run-history-table.tsx`
- `frontend/src/components/products/product-overview.tsx`
- `frontend/src/components/customers/customer-overview.tsx`
- `frontend/src/components/staff/staff-overview.tsx`
- `frontend/src/components/sites/site-overview.tsx`
- `frontend/src/app/globals.css`
- `frontend/tailwind.config.ts`

### Modified (Config)
- `.env`
- `pyproject.toml`

**Total: ~48 files modified/created across 31 commits in 6 phases**
