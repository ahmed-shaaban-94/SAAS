# DataPulse -- Opus Full Project Review

> **Date**: 2026-03-30
> **Reviewer**: Claude Opus 4.6
> **Scope**: Security + Architecture + UI/UX
> **Files Analyzed**: ~189 source files (45 Python, 127 TypeScript, 17 SQL)

---

## Executive Summary

| Category | CRITICAL | HIGH | MEDIUM | LOW | Total |
|----------|----------|------|--------|-----|-------|
| Security | 3 | 5 | 9 | 13 | 30 |
| Architecture | 0 | 6 | 13 | 12 | 31 |
| UI/UX | 0 | 0 | 10 | 8 | 18 |
| **Total** | **3** | **11** | **32** | **33** | **79** |

**Overall Verdict**: The project is well-engineered for its stage -- clean medallion architecture, consistent code patterns, and a polished dark-themed dashboard. However, **authentication is fundamentally broken** (auth disabled by default, Keycloak not integrated, tenant_id hardcoded), making it unsuitable for production deployment without remediation. The frontend and dbt layers are solid with mostly cosmetic/accessibility issues.

---

# Part 1: Security Audit

## CRITICAL Findings

### SEC-01: Auth guards are no-ops when API_KEY is empty (default)
- **File**: `src/datapulse/api/auth.py:27-28`, `config.py:49`
- **Impact**: Entire API is unauthenticated by default
- Both `require_api_key` and `require_pipeline_token` silently skip auth when config values are empty strings (the default). No warning is logged. Nothing forces these to be set in production.
- **Fix**: Remove empty-string defaults. Add startup validation that refuses to boot without `API_KEY` in production.

### SEC-02: Pipeline GET endpoints have NO auth at all
- **File**: `src/datapulse/api/routes/pipeline.py:50-96, 219-234`
- **Impact**: Pipeline run data (error messages, row counts, durations) publicly accessible
- The pipeline router lacks router-level `dependencies=[Depends(require_api_key)]` unlike analytics and ai-light routers. Four GET endpoints are always unauthenticated even when API_KEY is configured.
- **Fix**: Add `dependencies=[Depends(require_api_key)]` to the pipeline router.

### SEC-03: No real user authentication -- Keycloak not integrated
- **File**: `docker-compose.yml:247-277`
- **Impact**: No OAuth2/OIDC flows, no JWT verification, no session management
- Keycloak is deployed in `start-dev` mode but has zero integration with the API or frontend. The static API key is the sole auth mechanism, shared across all clients.
- **Fix**: Implement OAuth2/OIDC with JWT verification middleware; derive tenant_id from JWT claims.

## HIGH Findings

### SEC-04: Tenant_id hardcoded to "1"
- **File**: `src/datapulse/api/deps.py:56-57`
- `SET LOCAL app.tenant_id = :tid` always uses `"1"`. RLS is configured but functionally useless.

### SEC-05: RLS uses owner role -- policies grant unrestricted access
- **Files**: `migrations/005_create_pipeline_runs.sql:51-55`, `migrations/003_add_tenant_id.sql:72-75`
- API connects as `datapulse` owner. Owner policy is `USING (true)` -- full access regardless of tenant. The `datapulse_reader` role (which enforces scoping) is never used.

### SEC-06: SET LOCAL without explicit transaction -- scope leak risk
- **File**: `src/datapulse/api/deps.py:53-63`
- `SET LOCAL` scoped to current transaction, but if transaction commits mid-request (pipeline CRUD), subsequent queries lose tenant context.

### SEC-07: Keycloak running in dev mode
- **File**: `docker-compose.yml:251`
- `start-dev` disables HTTPS and enables insecure features. No prod override exists.

### SEC-08: All services share one DB with owner credentials
- **File**: `docker-compose.yml` (multiple lines)
- App, API, n8n, Metabase, and Keycloak all use the same `datapulse` owner credentials. Compromise of any one service = full DB access.

## MEDIUM Findings

| ID | Finding | File |
|----|---------|------|
| SEC-09 | CORS `allow_credentials=True` with configurable origins | `api/app.py:36-42` |
| SEC-10 | No CSRF protection on POST/PATCH endpoints | `api/routes/pipeline.py:99-177` |
| SEC-11 | Error sanitization incomplete in executor | `pipeline/executor.py:28-38` |
| SEC-12 | Metabase uses `latest` tag (unpinned) | `docker-compose.yml:219` |
| SEC-13 | Metabase uses same DB owner credentials | `docker-compose.yml:227-229` |
| SEC-14 | Source code mounted as volumes in compose | `docker-compose.yml:21-27` |
| SEC-15 | Frontend sends NO auth headers | `frontend/src/lib/api-client.ts:50-90` |
| SEC-16 | `psycopg2-binary` not recommended for production | `pyproject.toml:19` |
| SEC-17 | No magic-byte validation on file uploads | `import_pipeline/validator.py` |

## Positive Security Findings (LOW/Info)

- All ports bound to `127.0.0.1` -- good
- Non-root Docker users (`appuser`, `nextjs`)
- SQL column whitelists prevent injection
- Path traversal properly defended (`validate_source_dir`)
- CSP headers properly configured in frontend middleware
- Global exception handler hides internal errors
- Rate limiting in place (60/min global)
- Sensitive log fields masked by structlog processor
- `.env` properly gitignored, no secrets committed
- `parseDecimals` has `MAX_SAFE_INTEGER` guard

---

# Part 2: Architecture Review

## HIGH Findings

### ARCH-01: Missing `api_base_url` in Settings -- runtime crash
- **File**: `src/datapulse/watcher/service.py:29`
- References `self._settings.api_base_url` which doesn't exist in `config.py`. Will raise `AttributeError` at runtime.

### ARCH-02: Watcher sends wrong auth header
- **File**: `src/datapulse/watcher/service.py:38`
- Sends `X-Webhook-Secret` but API expects `X-Pipeline-Token`. Pipeline trigger will fail auth.

### ARCH-03: Frontend `postAPI` has no auth headers
- **File**: `frontend/src/lib/api-client.ts:75`
- Neither `fetchAPI` nor `postAPI` send `X-API-Key`. Pipeline trigger button fails when auth is enabled.

### ARCH-04: No integration tests against real database
- All repository/service tests mock SQLAlchemy session. Zero tests verify SQL against PostgreSQL. RLS enforcement, query correctness, and migration idempotency are untested.

### ARCH-05: Auth disabled by default in config
- **File**: `src/datapulse/config.py:49`
- `api_key: str = ""` and `pipeline_webhook_secret: str = ""` silently disable all authentication.

### ARCH-06: `get_db_session` never commits on happy path
- **File**: `src/datapulse/api/deps.py:53-63`
- Session catches exceptions and rolls back but never commits. Write operations rely on repositories calling `commit()` explicitly -- fragile pattern.

## MEDIUM Findings

| ID | Finding | File |
|----|---------|------|
| ARCH-07 | Duplicate `JsonDecimal` type alias | `ai_light/models.py:11` vs `types.py` |
| ARCH-08 | Duplicate duration calculation in PipelineService | `pipeline/service.py:55-65, 83-93` |
| ARCH-09 | `metrics_summary` correlated subquery (slow) | `dbt/models/marts/aggs/metrics_summary.sql:29-33` |
| ARCH-10 | No pagination on analytics endpoints | `api/routes/analytics.py` |
| ARCH-11 | Inconsistent AI-Light auth behavior (503 vs silent fallback) | `api/routes/ai_light.py` |
| ARCH-12 | No `useMemo`/`useCallback` on chart components | Frontend chart components |
| ARCH-13 | Keycloak in `start-dev` mode | `docker-compose.yml:249` |
| ARCH-14 | Metabase shares application database | `docker-compose.yml:227-229` |
| ARCH-15 | Raw SQL everywhere instead of SQLAlchemy Core expressions | `analytics/repository.py` |
| ARCH-16 | Global mutable state for engine/session factory | `api/deps.py:26-27` |
| ARCH-17 | `dim_site.sql` massive DRY violation (150 lines x2) | `dbt/models/marts/dims/dim_site.sql:55-208` |
| ARCH-18 | No incremental materialization in dbt | All dbt models |
| ARCH-19 | `fct_sales` ROW_NUMBER() for surrogate key (non-deterministic) | `dbt/models/marts/facts/fct_sales.sql:51` |

## LOW Findings

| ID | Finding | File |
|----|---------|------|
| ARCH-20 | `analytics/repository.py` at 607 lines (exceeds 400-line convention) | `analytics/repository.py` |
| ARCH-21 | Migration numbering gap (006 missing) | `migrations/` |
| ARCH-22 | Audit module is dead code (never started) | `api/audit.py` |
| ARCH-23 | Unused `summaryParams` variable | `frontend/src/hooks/use-summary.ts:10-12` |
| ARCH-24 | No indexes on aggregation tables | `dbt/models/marts/aggs/` |
| ARCH-25 | `agg_sales_daily` grain includes `billing_way` but queries aggregate it away | `agg_sales_daily.sql` |
| ARCH-26 | `stg_sales` is a view -- queried by all downstream models | `dbt/models/staging/stg_sales.sql` |
| ARCH-27 | Triplicate status validation (model + service + route) | `pipeline/` |
| ARCH-28 | `fetchAPI`/`postAPI` share duplicated timeout/error logic | `frontend/src/lib/api-client.ts` |
| ARCH-29 | SWR keys use `JSON.stringify` (property order sensitive) | `frontend/src/hooks/` |
| ARCH-30 | Watcher `_is_safe_path` uses vulnerable `str.startswith()` | `watcher/handler.py:47` |
| ARCH-31 | `openpyxl`/`xlrd` and `react-grid-layout` appear unused | `pyproject.toml`, `package.json` |

---

# Part 3: UI/UX Review

## MEDIUM Findings

### UI-01: `text-text-accent` class does not exist
- **File**: `frontend/src/components/shared/quick-rankings.tsx:42, 62, 66`
- This Tailwind class maps to no defined color. Elements render with browser default/inherited color -- potentially invisible on dark background.
- **Fix**: Replace with `text-text-primary` or `text-accent`.

### UI-02: Active filter chips show IDs instead of names
- **File**: `frontend/src/components/filters/active-filter-chips.tsx:38-46`
- Shows `Site ID: 1` or `Staff ID: 42` instead of human-readable names.
- **Fix**: Look up label from `useFilterOptions` hook.

### UI-03: Inconsistent error state patterns
- Four different error patterns exist across pages:
  - `ErrorRetry` component (best, used by detail pages)
  - `EmptyState` as error (wrong icon -- Inbox instead of error)
  - Inline red `<div>` (charts)
  - Custom inline card (returns)
- **Fix**: Standardize all error states to use `ErrorRetry`.

### UI-04: KPI grid 7-col on `lg` is cramped
- **File**: `frontend/src/components/dashboard/kpi-grid.tsx:26`
- 7 cards at `lg:grid-cols-7` = ~137px per card on 1024px viewport. Currency text overflows.
- **Fix**: Use `lg:grid-cols-4 xl:grid-cols-7`.

### UI-05: Mobile `pt-18` creates excessive top padding
- **File**: `frontend/src/app/(app)/layout.tsx:16`
- 72px top padding vs ~52px hamburger area creates a visible gap.
- **Fix**: Reduce to `pt-16`.

### UI-06: Date inputs not programmatically associated with labels
- **File**: `frontend/src/components/filters/filter-bar.tsx:117-141`
- Labels lack `htmlFor`/`id` pairing with inputs. Screen readers can't associate them.
- **Fix**: Add `id` to inputs and `htmlFor` to labels.

### UI-07: Missing `role="img"` and `aria-label` on 3 chart containers
- **Files**: `ranking-chart.tsx:33`, `returns-chart.tsx:35`, `site-comparison-cards.tsx:84`
- Other charts correctly have these attributes. Inconsistent.

### UI-08: Chart colors not colorblind-safe
- **File**: `frontend/src/lib/constants.ts:1-4`
- Teal-green (`#00BFA5`) and lime (`#8BC34A`) appear similar with deuteranopia. Pink and purple also confusable.
- **Fix**: Adopt a colorblind-safe palette (e.g., Tableau 10).

### UI-09: Tables lack `aria-label` or `<caption>`
- **Files**: `ranking-table.tsx`, `returns-table.tsx`, `run-history-table.tsx`
- Screen readers can't identify table purpose.

### UI-10: `growth-green`/`growth-red` fail WCAG AA contrast
- **File**: `tailwind.config.ts:22-23`
- `#2E7D32` on `#161B22` = ~3.2:1 (needs 4.5:1). `#C62828` = ~3.5:1.
- **Fix**: Lighten to `#4CAF50` and `#EF5350`.

## LOW Findings

| ID | Finding | File |
|----|---------|------|
| UI-11 | Monthly bar chart hardcodes `#2196F3` instead of theme | `monthly-trend-chart.tsx:79` |
| UI-12 | Distribution chart tooltip missing currency format | `distribution-chart.tsx:39` |
| UI-13 | Dashboard loading skeleton missing QuickRankings | `dashboard/loading.tsx` |
| UI-14 | Anomaly AlertTriangle uses accent color instead of warning | `anomaly-list.tsx:44` |
| UI-15 | Suspense boundary has no fallback | `providers.tsx:12` |
| UI-16 | No table sorting support | All table components |
| UI-17 | Overview pages could share a generic component | `*-overview.tsx` (3 files) |
| UI-18 | No light mode / system preference detection | `layout.tsx:31` |

---

# Priority Remediation Plan

## Phase 1: Critical Security (Must Fix Before Any Deployment)

| # | Action | Effort | Findings Addressed |
|---|--------|--------|--------------------|
| 1 | **Require API_KEY at startup** -- Remove empty defaults, add startup validation, log warning if unset | S | SEC-01, ARCH-05 |
| 2 | **Add auth to pipeline router** -- Add `dependencies=[Depends(require_api_key)]` | XS | SEC-02 |
| 3 | **Frontend auth headers** -- Add `X-API-Key` header to `fetchAPI`/`postAPI` from env var | S | SEC-15, ARCH-03 |
| 4 | **Fix watcher header** -- Change `X-Webhook-Secret` to `X-Pipeline-Token` | XS | ARCH-02 |
| 5 | **Add `api_base_url` to Settings** | XS | ARCH-01 |

## Phase 2: High Security & Data Integrity

| # | Action | Effort | Findings Addressed |
|---|--------|--------|--------------------|
| 6 | **Integrate Keycloak OIDC** -- JWT verification middleware, derive tenant_id from claims | L | SEC-03, SEC-04, SEC-07 |
| 7 | **Create least-privilege DB role for API** -- Use `datapulse_reader` for read endpoints | M | SEC-05, SEC-08 |
| 8 | **Fix SET LOCAL transaction scope** -- Wrap in explicit `session.begin()` | S | SEC-06 |
| 9 | **Separate DB credentials per service** -- Unique roles for n8n, Metabase, Keycloak | M | SEC-08, SEC-13, ARCH-14 |

## Phase 3: Architecture Improvements

| # | Action | Effort | Findings Addressed |
|---|--------|--------|--------------------|
| 10 | **Add integration tests** -- testcontainers or docker compose test target | L | ARCH-04 |
| 11 | **dbt incremental models** -- `fct_sales` and `agg_*` tables | M | ARCH-18 |
| 12 | **Fix fct_sales surrogate key** -- Use `dbt_utils.generate_surrogate_key()` | S | ARCH-19 |
| 13 | **Refactor dim_site governorate mapping** -- Extract to dbt macro or seed | S | ARCH-17 |
| 14 | **Materialize stg_sales as table** | XS | ARCH-26 |
| 15 | **Add indexes to agg tables** | S | ARCH-24 |

## Phase 4: UI/UX Polish

| # | Action | Effort | Findings Addressed |
|---|--------|--------|--------------------|
| 16 | **Fix `text-text-accent`** -- Replace with valid class | XS | UI-01 |
| 17 | **Standardize error states** -- Use `ErrorRetry` everywhere | S | UI-03 |
| 18 | **Fix filter chips** -- Show names instead of IDs | S | UI-02 |
| 19 | **Fix KPI grid breakpoints** -- `lg:grid-cols-4 xl:grid-cols-7` | XS | UI-04 |
| 20 | **Accessibility pass** -- labels, ARIA, contrast, colorblind palette | M | UI-06 through UI-10 |

---

# Appendix: Files Reviewed

<details>
<summary>Python (45 files)</summary>

- `src/datapulse/config.py`
- `src/datapulse/types.py`
- `src/datapulse/logging.py`
- `src/datapulse/api/app.py`
- `src/datapulse/api/auth.py`
- `src/datapulse/api/deps.py`
- `src/datapulse/api/audit.py`
- `src/datapulse/api/limiter.py`
- `src/datapulse/api/routes/health.py`
- `src/datapulse/api/routes/analytics.py`
- `src/datapulse/api/routes/pipeline.py`
- `src/datapulse/api/routes/ai_light.py`
- `src/datapulse/analytics/repository.py`
- `src/datapulse/analytics/service.py`
- `src/datapulse/analytics/models.py`
- `src/datapulse/pipeline/models.py`
- `src/datapulse/pipeline/repository.py`
- `src/datapulse/pipeline/service.py`
- `src/datapulse/pipeline/executor.py`
- `src/datapulse/pipeline/quality.py`
- `src/datapulse/pipeline/quality_repository.py`
- `src/datapulse/pipeline/quality_service.py`
- `src/datapulse/bronze/loader.py`
- `src/datapulse/bronze/column_map.py`
- `src/datapulse/import_pipeline/reader.py`
- `src/datapulse/import_pipeline/validator.py`
- `src/datapulse/import_pipeline/type_detector.py`
- `src/datapulse/import_pipeline/models.py`
- `src/datapulse/watcher/service.py`
- `src/datapulse/watcher/handler.py`
- `src/datapulse/ai_light/models.py`
- All test files (23 files)

</details>

<details>
<summary>Frontend TypeScript (127 files)</summary>

- `frontend/src/app/layout.tsx`
- `frontend/src/app/(app)/layout.tsx`
- `frontend/src/app/(app)/dashboard/page.tsx`
- `frontend/src/app/(app)/products/page.tsx`
- `frontend/src/app/(app)/customers/page.tsx`
- `frontend/src/app/(app)/staff/page.tsx`
- `frontend/src/app/(app)/sites/page.tsx`
- `frontend/src/app/(app)/returns/page.tsx`
- `frontend/src/app/(app)/pipeline/page.tsx`
- All component files (`components/`)
- All hook files (`hooks/`)
- All lib files (`lib/`)
- All type files (`types/`)
- `frontend/src/middleware.ts`
- `frontend/tailwind.config.ts`
- `frontend/e2e/*.spec.ts` (6 files)

</details>

<details>
<summary>SQL/dbt (17 files)</summary>

- `dbt/models/bronze/bronze_sales.sql`
- `dbt/models/staging/stg_sales.sql`
- `dbt/models/marts/dims/dim_*.sql` (6 files)
- `dbt/models/marts/facts/fct_sales.sql`
- `dbt/models/marts/aggs/*.sql` (8 files)
- `migrations/*.sql` (7 files)

</details>

<details>
<summary>Infrastructure</summary>

- `docker-compose.yml`
- `Dockerfile`
- `frontend/Dockerfile`
- `pyproject.toml`
- `frontend/package.json`
- `.gitignore`

</details>
