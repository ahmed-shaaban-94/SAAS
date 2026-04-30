# Iron Curtain — DataPulse Hardening Plan

**Date:** 2026-04-09 | **Branch:** `claude/mystifying-swanson` | **Codebase:** DataPulse SaaS
**Scope:** 6 Tiers, ~49 hours | **Goal:** Strengthen, harden, fortify — ZERO new features

---

## Context

A deep 6-layer audit (backend, frontend, database, CI/CD, security, testing) identified 260+ findings across the full stack. Dragon Roar (the previous audit plan) was ~95% completed, fixing data integrity and pipeline issues. What remains are structural weaknesses: auth bypass risk, 51 broad exception catches that hide failures, 312 untyped functions, missing database indexes on tenant queries, frontend components too large to test, and a 39% untested Python module gap.

This plan addresses ALL actionable findings. Items verified as already fixed (pipeline source_dir validation, audit_log RLS, embed token hardening, LIMIT ordering in kpi_repository) are documented in the Deferred section with evidence.

---

## Graph-Validated Findings (via `dp_impact` + `dp_context` MCP tools)

| Symbol | Graph Result | Plan Impact |
|--------|-------------|-------------|
| `require_permission` | 104 downstream symbols; already used on `analytics.py`, `gamification.py` | T1.2 is safe — same pattern, just 5 more routers |
| `get_current_user` | Imported by 26 route modules; tested via 14 endpoint tests | T1.2 swap is backwards-compatible — `require_permission` chains through it |
| `cache_get` | 4 downstream dependents (`cache_decorator`, `cached`, `ChurnRepository`) | T2.1 is low-risk — narrow blast radius |
| Graph orphans | 250 remaining (323→250 after analyzer fixes earlier today) | Not addressed by Iron Curtain — separate graph optimization track |

---

## Pre-Audit Verification (Confirmed Safe — SKIP)

| Finding | Verification | Status |
|---------|-------------|--------|
| Pipeline `source_dir` path traversal | `src/datapulse/types.py:19-43` has `validate_source_dir()` blocking `..` and enforcing `/app/data` root | SAFE |
| `audit_log` missing RLS | Migration `014_add_audit_log_tenant_user.sql` retroactively enables RLS + FORCE | FIXED |
| Embed token weak secret | `src/datapulse/embed/token.py:46` checks environment, raises `ValueError` in prod | HARDENED |
| LIMIT without ORDER BY | `kpi_repository.py` lines 61,70,79,88 — each sub-SELECT has ORDER BY within UNION ALL | FALSE POSITIVE |

---

## T1: Security Shield (CRITICAL)
**Priority:** P0 | **Est:** ~6 hours | **Dependencies:** None

### T1.1 Harden dev-mode auth fallback
**Files:**
- `src/datapulse/api/auth.py`
  - Line 165: `"roles": ["admin"]` → `"roles": ["viewer"]` — dev mode must never grant admin
- `src/datapulse/core/config.py`
  - Add `@model_validator(mode="after")` to `Settings` class: if `sentry_environment not in ("development", "test")` AND both `api_key` and `auth0_domain` are empty → raise `ValueError("Auth must be configured in production/staging")`
  - This catches misconfiguration at startup, not per-request
**Risk:** LOW — only changes behavior when auth is misconfigured
**Est:** 1.5h

### T1.2 Add RBAC permission guards to 5 unprotected routers
**Pattern:** `require_permission()` already exists at `src/datapulse/rbac/dependencies.py:120-136` and is used on `members.py`. It internally calls `get_access_context` which calls `get_current_user`, so auth is still enforced.

**Files:**
- `src/datapulse/api/routes/upload.py`
  - Line 8: add `from datapulse.rbac.dependencies import require_permission`
  - Line 16: change `dependencies=[Depends(get_current_user)]` → `dependencies=[Depends(require_permission("pipeline:run"))]`
- `src/datapulse/api/routes/explore.py`
  - Line 37: → `dependencies=[Depends(require_permission("analytics:custom_query"))]`
- `src/datapulse/api/routes/export.py`
  - Line 28: → `dependencies=[Depends(require_permission("analytics:export"))]`
- `src/datapulse/api/routes/ai_light.py`
  - Line 27: → `dependencies=[Depends(require_permission("insights:view"))]`
- `src/datapulse/api/routes/reports.py`
  - Line 27: → `dependencies=[Depends(require_permission("reports:view"))]`
  - POST render endpoint: add endpoint-level `dependencies=[Depends(require_permission("reports:create"))]`
- Verify permissions exist in RBAC seed migration (`024_create_rbac_tables.sql`). If not, add them.
**Risk:** MEDIUM — users without the permission will get 403.
**Rollout strategy:** Default `member` role includes ALL 5 new permissions (safe rollout). Existing users keep full access. Admins can restrict per-user via RBAC panel later. Add a migration or seed script to INSERT the new permissions into the default role's permission set in `024_create_rbac_tables.sql` seed data (or a new migration `035_seed_iron_curtain_permissions.sql`).
**Est:** 2.5h

### T1.3 File upload content-type validation + per-tenant temp dirs
**Files:**
- `src/datapulse/upload/service.py`
  - Line 29 (after extension check): add magic-byte validation:
    - `.xlsx`/`.xls`: first 4 bytes = `PK\x03\x04` (OOXML) or `\xd0\xcf\x11\xe0` (OLE2)
    - `.csv`: first 1KB must be valid UTF-8 with no null bytes
  - Line 33: change `dest = TEMP_DIR / f"{file_id}{ext}"` → `dest = TEMP_DIR / tenant_id / f"{file_id}{ext}"`
  - Constructor: accept `tenant_id` param, create subdirectory
- `src/datapulse/api/routes/upload.py`
  - Pass `tenant_id` from user claims into `UploadService`
**Risk:** MEDIUM — existing uploads must still work
**Est:** 2h

### T1 Verification
```bash
pytest -m unit -k "test_auth" --no-header -q
# Manual: SENTRY_ENVIRONMENT=production + empty API_KEY → app refuses to start
# Each of 5 routers returns 403 for user lacking permission
# Upload .xlsx with CSV content → rejected
```

---

## T2: Exception Fortress (HIGH)
**Priority:** P1 | **Est:** ~8 hours | **Dependencies:** None (parallel with T1)

### T2.1 Narrow cache.py exceptions (7 catches)
**File:** `src/datapulse/cache.py`
- Top of file: add `import json` (if not present), conditional `try: import redis; except ImportError: redis = None`
- Line 44: `except Exception:` → `except (redis.ConnectionError, redis.TimeoutError, OSError):`
- Line 71: → `except (redis.ConnectionError, redis.TimeoutError, redis.RedisError, OSError) as exc:`
- Line 92: → `except (redis.RedisError, json.JSONDecodeError, OSError) as exc:`
- Line 106: → `except (redis.RedisError, TypeError, OSError) as exc:`
- Line 125: → `except (redis.RedisError, OSError) as exc:`
- Line 147: → `except (redis.RedisError, OSError) as exc:`
- Line 159: → `except (redis.RedisError, OSError):`
**Risk:** LOW — cache is graceful-degradation by design
**Est:** 1h

### T2.2 Narrow scheduler.py exceptions (5 catches)
**File:** `src/datapulse/scheduler.py`
- Add imports: `import sqlalchemy.exc`, `import httpx`
- Line 147 (advisory lock): → `except (sqlalchemy.exc.SQLAlchemyError, OSError):`
- Line 205 (pipeline crash): → `except (sqlalchemy.exc.SQLAlchemyError, OSError, RuntimeError, subprocess.SubprocessError) as exc:`
- Line 216 (unlock): → `except (sqlalchemy.exc.SQLAlchemyError, OSError):`
- Line 280 (quality digest): → `except (sqlalchemy.exc.SQLAlchemyError, OSError) as exc:`
- Line 320 (AI digest): → `except (httpx.HTTPError, httpx.TimeoutException, OSError, KeyError) as exc:`
**Risk:** MEDIUM
**Est:** 1h

### T2.3 Narrow executor.py exceptions (3 catches)
**File:** `src/datapulse/pipeline/executor.py`
- Add imports: `import sqlalchemy.exc`; guard: `try: import polars.exceptions; except ImportError: pass`
- Line 84: → `except (OSError, RuntimeError, sqlalchemy.exc.SQLAlchemyError, ValueError) as exc:`
- Line 164: → `except (OSError, subprocess.SubprocessError, FileNotFoundError) as exc:`
- Line 212: → `except (sqlalchemy.exc.SQLAlchemyError, OSError, RuntimeError, ValueError) as exc:`
**Risk:** MEDIUM
**Est:** 45m

### T2.4 Narrow health.py exceptions (7 catches)
**File:** `src/datapulse/api/routes/health.py`
- Lines 37, 126, 154, 182 (DB checks): → `except (sqlalchemy.exc.SQLAlchemyError, OSError) as exc:`
- Lines 54, 71 (Redis checks): → `except (redis.RedisError, OSError) as exc:`
- Line 112 (pool check): → `except (sqlalchemy.exc.SQLAlchemyError, AttributeError, OSError) as exc:`
**Risk:** LOW
**Est:** 45m

### T2.5 Narrow async_executor.py exceptions (4 catches)
**File:** `src/datapulse/tasks/async_executor.py`
- Line 47: → `except (redis.ConnectionError, redis.RedisError, OSError) as exc:`
- Line 116: → `except (sqlalchemy.exc.SQLAlchemyError, OSError) as exc:`
- Line 134: → `except (redis.RedisError, OSError) as redis_exc:`
- Line 218: → `except (redis.RedisError, json.JSONDecodeError, OSError) as exc:`
**Risk:** MEDIUM
**Est:** 45m

### T2.6 Narrow remaining broad exceptions (~25 catches)
**Files and patterns:**

| File | Lines | New except clause |
|------|-------|-------------------|
| `api/routes/export.py` | 193, 228, 249, 270 | `(sqlalchemy.exc.SQLAlchemyError, OSError, ValueError)` |
| `api/routes/ai_light.py` | 53, 69, 85 | `(httpx.HTTPError, OSError, ValueError)` |
| `bronze/loader.py` | 109, 222, 250, 309 | `(OSError, ValueError, sqlalchemy.exc.SQLAlchemyError)` |
| `notifications.py` | 35 | `(httpx.HTTPError, OSError)` |
| `api/routes/explore.py` | 130 | `(sqlalchemy.exc.SQLAlchemyError, ValueError, OSError)` |
| `api/routes/embed.py` | 147 | `(jwt.InvalidTokenError, ValueError)` |
| `api/routes/billing.py` | 119 | `(ValueError, OSError)` + stripe-specific if available |
| `api/routes/pipeline.py` | 153 | `(sqlalchemy.exc.SQLAlchemyError, OSError)` |
| `forecasting/methods.py` | 125 | `(ArithmeticError, ValueError, RuntimeError)` |
| `watcher/handler.py` | 92 | `(httpx.HTTPError, OSError)` |
| `api/limiter.py` | 33 | `(redis.RedisError, OSError)` |
| `explore/manifest_parser.py` | 161 | `(OSError, json.JSONDecodeError, KeyError)` |
| `reports/template_engine.py` | 319 | `(sqlalchemy.exc.SQLAlchemyError, ValueError, KeyError)` |
| `pipeline/quality*.py` | various | `(sqlalchemy.exc.SQLAlchemyError, OSError)` |
| `pipeline/rollback.py` | 35, 56 | `(sqlalchemy.exc.SQLAlchemyError, OSError)` |
| `rbac/dependencies.py` | 89 | `(sqlalchemy.exc.SQLAlchemyError, OSError)` |
| `bronze/__main__.py` | 10 | `(OSError, RuntimeError, ValueError)` |

**Risk:** LOW-MEDIUM
**Est:** 3h

### T2 Verification
```bash
grep -r "except Exception" src/datapulse/ | wc -l  # target: 0
ruff check src/
pytest -m unit --no-header -q
```

---

## T3: Type Armor (HIGH)
**Priority:** P1 | **Est:** ~10 hours | **Dependencies:** T2

### T3.1 Extract hardcoded magic numbers into Settings
**File:** `src/datapulse/core/config.py` — add to `Settings` class:

| New field | Type | Default | Source file | Source line |
|-----------|------|---------|-------------|-------------|
| `redis_socket_timeout` | `int` | `2` | `cache.py` | 64-65 |
| `redis_retry_interval` | `int` | `15` | `cache.py` | 29 |
| `jwks_cache_ttl` | `int` | `3600` | `api/jwt.py` | 24 |
| `query_job_ttl` | `int` | `3600` | `tasks/async_executor.py` | 31 |
| `query_execution_timeout` | `int` | `300` | `tasks/async_executor.py` | 33 |
| `sse_poll_interval` | `int` | `2` | `api/routes/pipeline.py` | 131 |
| `sse_max_duration` | `int` | `600` | `api/routes/pipeline.py` | 132 |

After adding fields, update each source file to read from `get_settings()`.
**Risk:** LOW
**Est:** 2h

### T3.2 Add return type annotations to critical modules
**Strategy:** Run `mypy src/datapulse/ --no-error-summary 2>&1 | grep "missing return type"` and fix by module priority.

**Batch 1 — API routes** (~40 functions): add `-> dict`, `-> list[dict]`, or response model types
**Batch 2 — Analytics repositories** (~30 functions): add `-> list[dict[str, Any]]` or specific return types
**Batch 3 — Pipeline** (~20 functions): add `-> ExecutionResult`, `-> None`, etc.
**Batch 4 — Services** (~20 functions): add service-specific return types
**Batch 5 — Remaining** (~200 functions): internal helpers, mostly `-> None` or `-> dict`
**Risk:** LOW
**Est:** 5h

### T3.3 Narrow `Any` types (critical instances)
**Files:**
- `frontend/src/components/dashboard/monthly-trend-chart.tsx` line 83:
  `props: any` → `props: { payload?: Array<{ color: string; dataKey: string; value: string }> }`
- `frontend/src/components/dashboard/monthly-trend-chart.tsx` line 88:
  `entry: any` → `entry: { color: string; dataKey: string; value: string }`
- Python: focus on `api/filters.py:69`, `api/pagination.py:49`, `api/sorting.py:91` — replace `Any` with `Sequence[dict]` or appropriate Protocol type
**Risk:** LOW
**Est:** 3h

### T3 Verification
```bash
mypy src/datapulse/ --strict 2>&1 | tail -5  # count should decrease
npx tsc --noEmit  # frontend passes
pytest -m unit --no-header -q
```

---

## T4: Database Fortification (HIGH)
**Priority:** P1 | **Est:** ~5 hours | **Dependencies:** None (parallel)

### T4.1 Add composite indexes for RLS tenant queries
**Files:**
- `dbt/models/marts/aggs/agg_sales_daily.sql` post_hook:
  Add `"CREATE INDEX IF NOT EXISTS idx_agg_daily_tenant_date ON {{ this }} (tenant_id, date_key)"`
- `dbt/models/marts/aggs/agg_sales_by_product.sql` post_hook:
  Add `"CREATE INDEX IF NOT EXISTS idx_agg_product_tenant_cat ON {{ this }} (tenant_id, drug_category)"`
- `dbt/models/marts/aggs/agg_sales_by_staff.sql` post_hook:
  Add `"CREATE INDEX IF NOT EXISTS idx_agg_staff_tenant_key ON {{ this }} (tenant_id, staff_key)"`
**Risk:** LOW — CREATE INDEX IF NOT EXISTS is safe; brief lock during creation
**Est:** 1h

### T4.2 Add missing dbt tests
**File:** `dbt/models/marts/features/_features__models.yml`
- `feat_customer_health`: add `not_null` on `tenant_id`, `customer_key`, `health_score`, `health_band`; add `accepted_values` on `health_band` (`Thriving, Healthy, Needs Attention, At Risk, Critical`); add `relationships` on `customer_key` → `dim_customer`
- `feat_revenue_site_rolling`: add `not_null` on `daily_gross_amount`, `daily_transactions`; add `relationships` on `site_key` → `dim_site`, `date_key` → `dim_date`
**Risk:** LOW
**Est:** 1.5h

### T4.3 Convert dim_product and dim_customer to incremental
**Files:**
- `dbt/models/marts/dims/dim_product.sql`:
  - Change `materialized='table'` → `materialized='incremental', unique_key=['tenant_id', 'product_key'], incremental_strategy='merge'`
  - Add `{% if is_incremental() %} AND s.loaded_at >= (SELECT MAX(loaded_at) - INTERVAL '7 days' FROM {{ this }}) {% endif %}` to the source CTE
  - Guard Unknown member UNION ALL with `{% if not is_incremental() %}...{% endif %}`
- `dbt/models/marts/dims/dim_customer.sql`: same pattern
- **NOTE:** First deploy requires `dbt run --full-refresh --select dim_product dim_customer`
**Risk:** HIGH — changes materialization. Test thoroughly. **APPROVED by user** — included despite risk because it saves 5-10min per dbt run.
**Est:** 2.5h

### T4 Verification
```bash
dbt test --select feat_customer_health feat_revenue_site_rolling
dbt run --select dim_product dim_customer  # incremental
dbt run --full-refresh --select dim_product dim_customer  # verify full works too
# EXPLAIN ANALYZE on tenant-scoped query → should show index scan
```

---

## T5: Frontend Steel (MEDIUM)
**Priority:** P2 | **Est:** ~8 hours | **Dependencies:** None (parallel)

### T5.1 Extract 3 large components
**Files:**
- `frontend/src/components/goals/goals-overview.tsx` (430 lines) → extract:
  - `goals-budget-card.tsx` — budget summary section
  - `goals-quarterly-chart.tsx` — quarterly bar chart
  - `goals-target-summary.tsx` — target progress cards
- `frontend/src/components/dashboard/daily-trend-chart.tsx` (422 lines) → extract:
  - `daily-trend-tooltip.tsx` — custom tooltip
  - `daily-trend-legend.tsx` — custom legend renderer
- `frontend/src/components/dashboard/monthly-trend-chart.tsx` (411 lines) → extract:
  - `monthly-trend-legend.tsx` — the `renderMonthlyLegend` function (line 83+) → proper component
  - `monthly-trend-tooltip.tsx` — custom tooltip
**Risk:** MEDIUM — must preserve exact rendering behavior
**Est:** 3h

### T5.2 Add list virtualization to ranking components
**Files:**
- `frontend/src/components/dashboard/quick-rankings.tsx`
- `frontend/src/components/shared/ranking-table.tsx`
- Install `@tanstack/react-virtual` if not present
- Wrap list rendering in `useVirtualizer` when `items.length > 30`
**Risk:** MEDIUM
**Est:** 2h

### T5.3 Fix TypeScript `any` types in chart legends
**File:** `frontend/src/components/dashboard/monthly-trend-chart.tsx`
- Line 83: `props: any` → proper `MonthlyLegendProps` interface
- Line 88: `entry: any` → typed `LegendPayloadEntry`
**Risk:** LOW
**Est:** 30m

### T5.4 Add missing aria-labels and semantic roles
**Files:**
- Chart type switcher containers: add `role="tablist"`, buttons add `role="tab"` + `aria-selected`
- KPI grid cards: add `aria-label` with metric name + value
- Ranking lists: add `role="list"` + `role="listitem"`
**Risk:** LOW
**Est:** 1h

### T5.5 Replace index-based keys in chart components
**Files:**
- `daily-trend-chart.tsx` line 255: `key={i}` → `key={entry.dataKey}`
- `monthly-trend-chart.tsx` line 89: `key={i}` → `key={entry.dataKey}`
- `insight-chips.tsx` line 79: `key={i}` → `key={chip.label}`
- Skip skeleton loading `key={i}` (static lists, acceptable)
**Risk:** LOW
**Est:** 1.5h

### T5 Verification
```bash
npm run build  # zero warnings
npx tsc --noEmit
npx vitest run
# Manual: Lighthouse accessibility audit ≥ 90 on dashboard
```

---

## T6: Test Rampart (HIGH)
**Priority:** P1 | **Est:** ~12 hours | **Dependencies:** T1, T2

### T6.1 Test `sql_builder.py` (critical untested module)
**New file:** `tests/test_sql_builder.py`
- Test: basic query → valid SQL, multiple dims + GROUP BY, filter parameterization, invalid column → ValueError, SQL injection attempt → safe, empty query, all metric aggregation types, LIMIT + ORDER BY
**Est:** 2h

### T6.2 Test `quality_engine.py` (extend existing)
**File:** extend `tests/test_quality_engine.py`
- Test: default rules, each check type (row_count, null_rate, duplicate_check), custom rule override, severity levels (error blocks, warning passes), safe identifier regex, empty table edge case
**Est:** 2h

### T6.3 Test `executor.py` (extend existing)
**File:** extend `tests/test_pipeline_executor.py`
- Test: `_sanitize_error()` (connection strings redacted, paths stripped), `run_bronze()` success/failure, `run_dbt()` timeout + non-zero exit, `run_forecasting()` session cleanup
**Est:** 1.5h

### T6.4 Enable CI coverage gates
**File:** `.github/workflows/ci.yml`
- Line 61: `--cov-fail-under=0` → `--cov-fail-under=60`
- Line 111: `--cov-fail-under=0` → `--cov-fail-under=50`
**Risk:** MEDIUM — CI may fail if coverage drops
**Est:** 30m

### T6.5 Make dbt failure block staging deploy
**File:** `.github/workflows/deploy-staging.yml`
- Line 281: `|| echo "::warning::dbt run failed"` → `|| { echo "::error::dbt run FAILED"; exit 1; }`
**Risk:** MEDIUM — staging deploys will fail on dbt errors (intended)
**Est:** 30m

### T6.6 Frontend: test critical hooks and components
**New files:**
- `frontend/src/__tests__/hooks/use-targets.test.ts`
- `frontend/src/__tests__/hooks/use-chart-theme.test.ts`
- `frontend/src/__tests__/hooks/use-comparison-trend.test.ts`
- `frontend/src/__tests__/components/kpi-grid.test.tsx`
- `frontend/src/__tests__/components/quick-rankings.test.tsx`
**Est:** 5h

### T6 Verification
```bash
pytest -m unit --cov --cov-fail-under=60
pytest -m integration --cov --cov-fail-under=50
npx vitest run --coverage
gh run watch  # CI green with new gates
```

---

## Dependencies Map

```
T1 (Security Shield)       ──┐
T2 (Exception Fortress)    ──┼──→ T6 (Test Rampart)
T3 (Type Armor)            ──┤
T4 (Database Fortification)──┤
T5 (Frontend Steel)        ──┘
```

T1–T5 can all proceed **in parallel**. T6 depends on T1+T2 completion (tests must cover new guards and narrowed exceptions).

---

## Deferred Items (with evidence)

| Item | Why Deferred | Evidence |
|------|-------------|----------|
| Pipeline `source_dir` path traversal | Already validated | `types.py:19-43` blocks `..`, enforces `/app/data` root |
| `audit_log` RLS | Already fixed | Migration 014 enables RLS + FORCE |
| Embed token weak secret | Already hardened | `embed/token.py:46` checks environment in prod |
| LIMIT without ORDER BY | False positive | Lines 61,70,79,88 all have ORDER BY in sub-SELECT |
| 162 untested frontend components | Scope too large | T6.6 covers top 5; ratchet coverage quarterly |
| 200+ missing return types (lower priority) | T3.2 covers critical | Remaining are internal helpers; prevent regression via mypy in CI |
| Full `Any` type elimination | Many are legitimate | JWT claims and DB rows are genuinely dynamic |
| Next.js 15, ESLint 9, psycopg3 | Major version upgrades | Separate migration plan needed |
