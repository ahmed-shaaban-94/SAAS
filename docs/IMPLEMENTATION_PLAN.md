# DataPulse Implementation Plan (Graph-Validated)

> **Date:** 2026-04-10 | **Validated with:** DataPulse Graph MCP (`dp_impact`, `dp_context`, `dp_query`)
> **Companion report:** `docs/DEEP_ANALYSIS_REPORT.md`

---

## Phase A: Critical Fixes (Week 1-2)

### A1. Fix Migration 030 Duplicate Filenames
**Bug:** B1 (CRITICAL)
**Files:** `migrations/030_bronze_sales_unique_index.sql`, `030_fix_owner_user_id.sql`, `030_fix_rls_and_tenant_fks.sql`
**Graph check:** Not needed (file-level, no symbol impact)

**Steps:**
1. Read all three 030_*.sql files
2. Determine correct ordering (bronze index first, then owner fix, then RLS)
3. Rename to `030a_`, `030b_`, `030c_` preserving content
4. Verify `schema_migrations` table entries don't conflict
5. Test: `prestart.sh` dry-run

**Effort:** 1h | **Risk:** LOW (renaming only, idempotent migrations)

---

### A2. Fix Decimal Parsing (Scientific Notation)
**Bug:** B2 (HIGH)
**File:** `frontend/src/lib/api-client.ts:19`
**Graph check:** `dp_query("api-client", layer="frontend")` - Used by ALL SWR hooks (60+ hooks)

**Current regex:** `/^-?\d+(\.\d+)?$/` misses `1e-5`, `2.5E+3`

**Steps:**
1. Update regex to handle scientific notation: `/^-?\d+(\.\d+)?([eE][+-]?\d+)?$/`
2. OR replace with `Number.isFinite(Number(val))` check
3. Update test in `frontend/src/__tests__/lib/api-client.test.ts`
4. Verify: run `npx vitest run`

**Effort:** 1h | **Blast radius:** ALL frontend data parsing (60+ hooks rely on `fetchAPI`)

---

### A3. Fix LIKE Wildcard Injection
**Bug:** B4 (HIGH)
**File:** `src/datapulse/api/filters.py:173`
**Graph check:** `dp_impact("apply_filters")` = **160 affected symbols**

**Current code:**
```python
conditions.append(col.ilike(f"%{f.value}%"))
```

**Steps:**
1. Escape wildcards before LIKE:
   ```python
   escaped = f.value.replace("%", "\\%").replace("_", "\\_")
   conditions.append(col.ilike(f"%{escaped}%", escape="\\"))
   ```
2. Add test case with `%` and `_` in filter value
3. Run: `pytest tests/test_analytics_repository.py tests/test_api_endpoints.py -x`
4. `dp_detect_changes()` to verify blast radius

**Effort:** 30m | **Blast radius:** 160 symbols (but safe change - escaping only)

---

### A4. Increase DB Connection Pool
**Bug:** B5 (HIGH)
**File:** `src/datapulse/core/config.py:36-39`
**Graph check:** `dp_context("get_engine")` - singleton used by ALL DB operations

**Steps:**
1. Change defaults: `pool_size: int = 10`, `max_overflow: int = 20`
2. Add pool event logging:
   ```python
   from sqlalchemy import event
   @event.listens_for(engine, "checkout")
   def log_checkout(dbapi_conn, connection_record, connection_proxy): ...
   ```
3. Verify existing tests pass (pool config tested in `tests/test_config.py`)

**Effort:** 30m | **Risk:** LOW (backward-compatible, env vars override defaults)

---

### A5. Add Tenant ID Validation
**Bug:** B7 (MEDIUM)
**File:** `src/datapulse/api/auth.py:103-109`
**Graph check:** `dp_context("get_current_user")` - called by ALL authenticated routes

**Steps:**
1. After tenant_id extraction, add:
   ```python
   import re
   if tenant_id and not re.match(r'^\d{1,10}$', str(tenant_id)):
       logger.warning("invalid_tenant_id", raw=tenant_id)
       raise HTTPException(401, "Invalid tenant context")
   ```
2. Add test cases in `tests/test_auth.py`
3. Run: `pytest tests/test_auth.py -x`

**Effort:** 30m | **Blast radius:** All authenticated endpoints (safe - validation only)

---

### A6. Fix DB_READER_PASSWORD Mismatch
**Bug:** B6 (MEDIUM)
**Files:** `docker-compose.yml:26`, `scripts/prestart.sh:18`

**Steps:**
1. In `docker-compose.yml`, change:
   ```yaml
   DB_READER_PASSWORD: ${DB_READER_PASSWORD:-}
   ```
   to:
   ```yaml
   DB_READER_PASSWORD: ${DB_READER_PASSWORD:?DB_READER_PASSWORD must be set}
   ```
2. Update `.env.example` with clear instructions
3. Test: `docker compose config` to verify

**Effort:** 15m | **Risk:** LOW (breaks only if env var missing — intentional)

---

### A7. Secret Validation at Startup
**Fortification:** F7 (HIGH)
**File:** `src/datapulse/core/config.py` (add `@model_validator`)

**Steps:**
1. Add Pydantic model_validator to Settings:
   ```python
   @model_validator(mode="after")
   def warn_missing_secrets(self) -> "Settings":
       env = self.sentry_environment
       if env not in ("development", "test"):
           if not self.api_key:
               raise ValueError("API_KEY required in production")
           if not self.auth0_domain:
               raise ValueError("AUTH0_DOMAIN required in production")
       return self
   ```
2. Test: `pytest tests/test_config.py -x`

**Effort:** 1h | **Risk:** MEDIUM (could break dev if not careful with env check)

---

## Phase B: Fortification (Week 3-4)

### B1. RLS Audit Migration
**Fortification:** F1 (HIGH)
**File:** New migration `035_rls_audit.sql`
**Graph check:** `dp_query("rls", layer="gold")` - verifies which models have RLS

**Steps:**
1. Create migration that:
   ```sql
   DO $$ BEGIN
     IF EXISTS (
       SELECT 1 FROM pg_tables
       WHERE schemaname IN ('public_marts', 'public_staging', 'bronze')
       AND rowsecurity = false
     ) THEN
       RAISE WARNING 'Tables without RLS found!';
     END IF;
   END $$;
   ```
2. Add to CI integration test

**Effort:** 2h

---

### B2. Consolidate `_set_cache` Duplication
**Graph finding:** `_set_cache` duplicated in 7 route files
**Files:** analytics.py, anomalies.py, branding.py, forecasting.py, gamification.py, reseller.py, targets.py

**Steps:**
1. Extract to shared utility: `src/datapulse/api/cache_helpers.py`
2. Replace all 7 copies with import
3. `dp_detect_changes()` to verify no missed references
4. Run full test suite

**Effort:** 1h | **Blast radius:** 7 route files (safe - extract only)

---

### B3. SWR Global Config + Error Recovery
**Bugs:** B9, F12
**Files:** `frontend/src/components/providers.tsx`, `frontend/src/lib/swr-config.ts`

**Steps:**
1. Wrap app in `<SWRConfig value={swrConfig}>` in providers.tsx
2. Add global `onErrorRetry` with exponential backoff (max 3 retries)
3. Test: verify SWR deduplication still works

**Effort:** 1h

---

### B4. Business Exception Hierarchy
**Fortification:** F21
**File:** New `src/datapulse/core/exceptions.py`
**Graph check:** `dp_impact("global_exception_handler")` - catches all unhandled errors

**Steps:**
1. Create exception classes:
   ```python
   class DataPulseError(Exception): ...
   class ValidationError(DataPulseError): ...
   class QuotaExceeded(DataPulseError): ...
   class TenantError(DataPulseError): ...
   ```
2. Register handlers in `app.py` for each type
3. Gradually replace generic raises in service layer

**Effort:** 2h

---

### B5. JWKS Retry with Backoff
**Fortification:** F4
**File:** `src/datapulse/api/jwt.py:36-52`
**Graph check:** `dp_context("_fetch_jwks")` - used by `verify_jwt` -> ALL auth

**Steps:**
1. Add retry loop (3 attempts, 1s/2s/4s backoff)
2. Only retry on network errors, not on 4xx responses
3. Test: `pytest tests/test_auth.py -x`

**Effort:** 1h

---

### B6. Cache Hit Ratio Prometheus Metrics
**Fortification:** F22
**File:** `src/datapulse/cache.py`
**Graph check:** `dp_query("cache", layer="backend")` - 15 cache-related symbols

**Steps:**
1. Add counters: `cache_hits_total`, `cache_misses_total`
2. Expose via existing Prometheus instrumentator
3. Test: verify `/metrics` endpoint includes new counters

**Effort:** 1h

---

### B7. Web Vitals Tracking
**Fortification:** F27
**File:** `frontend/src/app/layout.tsx` or `frontend/src/components/providers.tsx`

**Steps:**
1. Add `web-vitals` package or use Sentry's built-in Web Vitals
2. Report LCP, FID, CLS to PostHog or Sentry
3. Verify in browser DevTools

**Effort:** 1h

---

## Phase C: Visual Enhancements (Week 5-6)

### C1. KPI Number Morphing Animation
**Enhancement:** E (2.2)
**File:** `frontend/src/components/dashboard/kpi-card.tsx`
**Graph check:** `dp_context("KPICard")` - used by KPIGrid on dashboard

**Steps:**
1. Replace `useCountUp` with digit-by-digit morphing animation
2. When SWR revalidates, only animate changed digits (slot-machine effect)
3. Use framer-motion `AnimatePresence` for digit transitions
4. Test: visual QA on dashboard page

**Effort:** 4h

---

### C2. Loading Skeleton-to-Content Morph
**Enhancement:** L (2.3)
**File:** `frontend/src/components/loading-card.tsx`
**Graph check:** Used by ALL lazy-loaded dashboard sections (9 dynamic imports)

**Steps:**
1. Wrap LoadingCard content in framer-motion `motion.div`
2. Use `layoutId` to morph skeleton shape into content shape
3. Add `AnimatePresence` in parent LazySection
4. Test: verify smooth transitions on slow network (DevTools throttle)

**Effort:** 4h

---

### C3. Marketing Mouse-Tracking Glow
**Enhancement:** A (2.1) - Inspired by Gemini file
**File:** `frontend/src/app/(marketing)/layout.tsx`, `frontend/src/app/globals.css`

**Steps:**
1. Add mouse position tracking (like Gemini's `mousePos` state)
2. Render radial gradient div following cursor (600px, accent color, 20% opacity)
3. Only on marketing pages (not dashboard — would be distracting)
4. Respect `prefers-reduced-motion`

**Effort:** 2h | **Zero bundle cost** (CSS + 30 lines JS)

---

### C4. Staggered Section Reveal
**Enhancement:** G (2.2)
**File:** `frontend/src/components/dashboard/lazy-section.tsx`

**Steps:**
1. Wire existing `stagger-1` through `stagger-7` CSS classes to LazySection children
2. When IntersectionObserver triggers, add `.is-visible` with stagger delays
3. Test: scroll through dashboard, verify smooth section reveals

**Effort:** 2h

---

### C5. Calendar Heatmap Click-to-Filter
**Enhancement:** H (2.2)
**File:** `frontend/src/components/dashboard/calendar-heatmap.tsx`
**Graph check:** `dp_query("heatmap", layer="frontend")` - connected to `use-heatmap` hook

**Steps:**
1. Add `onClick` handler to heatmap cells
2. On click, update FilterContext with selected date range (single day)
3. All dashboard sections react automatically (SWR keys change)
4. Add visual "selected" state (ring + tooltip)

**Effort:** 4h | **Blast radius:** Filter context shared by all dashboard components (intended)

---

## Phase D: Dependency Upgrades (Week 7-8)

### D1. Next.js 14 -> 15
**Graph check:** `dp_query("page", kind="page", layer="frontend")` - 22+ pages affected

**Steps:**
1. Update `next` to `^15.x` in package.json
2. Update `react` and `react-dom` to `^19.x`
3. Fix breaking changes: `cookies()` and `headers()` now async
4. Update `next-auth` to v5 (if needed for React 19 compat)
5. Update eslint-config-next
6. Run: `npx tsc --noEmit && npm run build && npx playwright test`

**Effort:** 8h | **Risk:** HIGH (major version, test thoroughly)

---

### D2. Tailwind 3 -> 4
**Steps:**
1. Install Tailwind v4 + update postcss config
2. Migrate `tailwind.config.ts` to CSS-first `@theme` syntax
3. Update `globals.css` to use new `@theme` directive
4. Verify dark mode, custom colors, animations
5. Run: `npm run build` + visual QA

**Effort:** 6h | **Risk:** MEDIUM (CSS changes, visual regression possible)

---

### D3. Incremental dbt Models
**Fortification:** F20 (HIGH)
**Graph check:** `dp_impact("fct_sales", max_depth=2)` - 8 aggs + 8 features depend on it

**Steps:**
1. Convert `fct_sales` to incremental (on `loaded_at` timestamp)
2. Convert `agg_sales_daily` and `agg_sales_monthly` to incremental
3. Add `--full-refresh` flag for manual rebuilds
4. Test: `dbt run --select fct_sales+ && dbt test`

**Effort:** 8h | **Blast radius:** 55 downstream symbols (but incremental is additive, not destructive)

---

## Phase E: Performance (Week 9-10)

### E1. Recharts Bundle Splitting
**File:** `frontend/next.config.mjs`

**Steps:**
1. Use Next.js `optimizePackageImports` (already includes recharts)
2. Verify recharts is tree-shaken per chart type
3. Consider `next/dynamic` for the chart registry if not already lazy

**Effort:** 2h

---

### E2. Redis Pipeline for Bulk Cache
**File:** `src/datapulse/cache.py`
**Graph check:** `dp_context("cache_get")` - called by analytics service

**Steps:**
1. Add `cache_get_many(keys: list[str])` using Redis PIPELINE
2. Use in dashboard endpoint (fetches KPIs + trends + rankings)
3. Benchmark: compare single-key vs pipeline latency

**Effort:** 2h

---

### E3. PostgreSQL Prepared Statements
**File:** `src/datapulse/core/db.py`
**Graph check:** `dp_context("get_engine")` - singleton for all DB ops

**Steps:**
1. Enable `use_insertmanyvalues=True` for batch inserts
2. Add `pool_pre_ping=True` (already done)
3. Consider `query_cache_size` for repeated queries

**Effort:** 2h

---

## Phase F: New Features (Week 11+)

### F1. Executive Briefing View
**Low effort, HIGH impact**
**Files:** New page `frontend/src/app/(app)/briefing/page.tsx`

**Steps:**
1. Create single-page C-suite view
2. Show 5 KPIs, AI narrative, top 3 action items
3. Auto-refresh every 10 minutes
4. Inspired by Gemini's "Command Center" section

**Effort:** 8h

---

### F2. Dashboard Builder (Drag & Drop)
**File:** `frontend/src/app/(app)/my-dashboard/page.tsx` (already exists!)
**Graph check:** `dp_context("MyDashboardPage")` + `dp_context("DashboardGrid")`

**Steps:**
1. `react-grid-layout` already installed
2. `DashboardGrid` component already exists
3. `useDashboardLayout` hook already exists
4. Wire up: layout persistence via API, widget catalog, add/remove

**Effort:** 16h (UI polish + widget catalog)

---

### F3. Live Demo Mode
**Inspired by Gemini's real-time simulation**

**Steps:**
1. Create `/demo` route with sample data (no auth required)
2. Simulate real-time updates with `setInterval` (like Gemini's `posEngine`)
3. Show KPI counters incrementing, trend chart scrolling
4. Marketing CTA: "See it live with your data"

**Effort:** 8h

---

## Validation Checklist (Per Phase)

Before merging ANY phase:
- [ ] `dp_detect_changes()` shows expected blast radius
- [ ] `pytest -m unit -x` passes
- [ ] `ruff check src/ tests/` clean
- [ ] `ruff format --check src/ tests/` clean
- [ ] `npx tsc --noEmit` (frontend type check)
- [ ] `npm run build` (frontend builds)
- [ ] `docker compose build` (containers build)
- [ ] Coverage >= 95% (`pytest --cov --cov-fail-under=95`)

---

*Plan generated with DataPulse Graph MCP validation - blast radius verified for all critical changes.*
