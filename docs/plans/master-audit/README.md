# DataPulse Master Audit — Multi-Session Execution Plan

## Context

The Master Audit Prompt defines 15 phases covering security, infrastructure, API, frontend, testing, AI/forecasting, compliance, and business strategy. A quick scan across all phases identified **4 CRITICAL**, **8 HIGH**, **12 MEDIUM**, and **6 LOW** severity findings.

This plan breaks the audit into **8 focused sessions**, ordered by **business risk** (security/data first, polish/growth last). Each session is self-contained with clear scope, deliverables, and verification steps.

---

## Quick Scan Summary — Top Findings

### CRITICAL (Fix Before Production)

| # | Finding | Location | Risk |
|---|---------|----------|------|
| C1 | Dev mode auth bypass grants admin to all unauthenticated requests | `src/datapulse/api/auth.py:134-150` | Full data access if auth misconfigured |
| C2 | SQL injection risk in Explore/SQL Lab via catalog manipulation | `src/datapulse/api/routes/explore.py:95` | Code execution |
| C3 | PII leakage — customer/product names sent to OpenRouter AI | `src/datapulse/ai_light/service.py:67-75` | Privacy violation, compliance risk |
| C4 | Currency formatting uses `en-US` instead of `ar-EG` for EGP | `frontend/src/lib/formatters.ts:15` | Wrong display for entire Egyptian market |

### HIGH (Fix This Sprint)

| # | Finding | Location | Risk |
|---|---------|----------|------|
| H1 | Production image tag fallback to `latest` | `docker-compose.prod.yml` | Unpredictable deployments |
| H2 | Pipeline webhook auth defaults to disabled | `auth.py:55-65` | Unauthenticated pipeline execution |
| H3 | Memory OOM risk — 2.27M rows loaded at once | `bronze/loader.py:59-89` | Pipeline crash on large datasets |
| H4 | SSE stream missing tenant validation | `api/routes/pipeline.py:134-136` | Cross-tenant data access |
| H5 | mypy `continue-on-error: true` in CI | `.github/workflows/ci.yml` | Type errors silently ignored |
| H6 | No i18n infrastructure — hardcoded English strings everywhere | `frontend/src/` | Cannot support Arabic |
| H7 | Tenant-scoped RLS policies not yet implemented | `migrations/002_add_rls_and_roles.sql` | Multi-tenant data leakage |
| H8 | No frontend component unit tests | `frontend/src/__tests__/` | UI regressions undetected |

### MEDIUM (12 items)

| # | Finding | Location |
|---|---------|----------|
| M1 | Missing HSTS header in nginx and app | `nginx/default.conf` |
| M2 | CSP allows `unsafe-inline` for scripts in production | `frontend/src/middleware.ts` |
| M3 | Audit log missing user_id column | `migrations/008_create_audit_log.sql` |
| M4 | E2E tests not in CI pipeline | `.github/workflows/ci.yml` |
| M5 | AI response JSON not validated against schema | `ai_light/service.py:155-172` |
| M6 | No minimum series length check for forecasting | `forecasting/service.py:119-138` |
| M7 | Custom SQL check lacks execution timeout | `pipeline/quality_engine.py:252-297` |
| M8 | BETWEEN filter value format not validated | `api/filters.py:145-148` |
| M9 | prev_cursor not implemented (no backward pagination) | `api/pagination.py:77` |
| M10 | Accessibility gaps — 25 aria labels for 78 components | `frontend/src/components/` |
| M11 | Slicer panel 347 lines, should be split | `frontend/src/components/filters/slicer-panel.tsx` |
| M12 | Architecture documentation file missing | `docs/ARCHITECTURE.md` |

---

## Session Breakdown

### Session 1: Security Hardening (Phases 2 + 14)
**Priority**: CRITICAL — Must be first
**Estimated scope**: ~15 files, ~20 changes
**Covers audit phases**: 2.1-2.5, 14.1-14.5

#### Fixes

| Task | Severity | Files |
|------|----------|-------|
| Fix dev mode auth bypass — require auth in production | C1 | `src/datapulse/api/auth.py` |
| Fix SQL injection in explore route | C2 | `src/datapulse/api/routes/explore.py`, `src/datapulse/explore/sql_builder.py` |
| Add PII anonymization layer before AI calls | C3 | `src/datapulse/ai_light/service.py`, new `src/datapulse/ai_light/anonymizer.py` |
| Enforce pipeline webhook secret in production | H2 | `src/datapulse/api/auth.py` |
| Add tenant_id check to SSE stream | H4 | `src/datapulse/api/routes/pipeline.py` |
| Add HSTS header to nginx | M1 | `nginx/default.conf` |
| Remove CSP `unsafe-inline` in production | M2 | `frontend/src/middleware.ts` |
| Add user_id column to audit_log | M3 | new `migrations/014_add_audit_user_id.sql` |
| Validate AI response JSON with Pydantic | M5 | `src/datapulse/ai_light/service.py`, `src/datapulse/ai_light/models.py` |
| Add execution timeout to custom SQL checks | M7 | `src/datapulse/pipeline/quality_engine.py` |

#### Tests to Write

- Test: unauthenticated request without auth config in production mode -> 500/startup error
- Test: SQL injection attempt in explore query -> blocked
- Test: AI prompt payload contains zero PII (customer/staff names)
- Test: cross-tenant SSE stream access -> 403
- Test: expired JWT -> 401
- Test: rate limit exceeded -> 429

#### Verification
```bash
make test                    # All existing tests still pass
pytest tests/test_auth.py    # New security tests pass
pytest tests/test_explore.py # SQL injection tests pass
```

---

### Session 2: Data Pipeline Resilience (Phase 3)
**Priority**: HIGH — Data integrity at risk
**Estimated scope**: ~10 files, ~15 changes
**Covers audit phases**: 3.1-3.4

#### Fixes

| Task | Severity | Files |
|------|----------|-------|
| Implement chunked/streaming bronze loader (100K batch) | H3 | `src/datapulse/bronze/loader.py` |
| Add migration chain rollback on failure | M | `src/datapulse/bronze/loader.py` |
| Add path traversal validation in file discovery | M | `src/datapulse/bronze/loader.py` |
| Add unknown billing_type quality check | M | `src/datapulse/pipeline/quality.py` |
| Add fct_sales unknown dimension (-1) dbt test | M | `dbt/models/marts/facts/_facts__models.yml` |
| Validate BETWEEN filter values in API | M8 | `src/datapulse/api/filters.py` |
| Add forecasting minimum series length check | M6 | `src/datapulse/forecasting/service.py` |

#### Tests to Write

- Test: Upload 500K+ rows -> completes without OOM
- Test: Upload with missing columns -> clear error listing expected columns
- Test: Upload with bad dates/nulls -> quality gate catches
- Test: Pipeline fails at silver stage -> bronze data preserved
- Test: dbt `fct_sales` unknown dimension count < 5% of total
- Test: Forecast with < 30 days data -> graceful error message

#### Verification
```bash
make test
make dbt-test
# Manual: upload a large Excel file and monitor memory
```

---

### Session 3: Infrastructure & CI/CD (Phases 1 + 11)
**Priority**: HIGH — Production readiness
**Estimated scope**: ~8 files, ~12 changes
**Covers audit phases**: 1.1-1.5, 11.1-11.5

#### Fixes

| Task | Severity | Files |
|------|----------|-------|
| Pin production image tags (remove `latest` fallback) | H1 | `docker-compose.prod.yml` |
| Enforce mypy in CI (remove `continue-on-error`) | H5 | `.github/workflows/ci.yml` |
| Add E2E tests to CI pipeline | M4 | `.github/workflows/ci.yml` |
| Add Trivy image scanning to CI | M | new `.github/workflows/security.yml` update |
| Fix AUTH0 env vars to use `${VAR:?}` in prod | M | `docker-compose.prod.yml` |
| Add deep health check endpoint (`/health/deep`) | M | `src/datapulse/api/routes/health.py` |
| Add structured request logging with correlation ID | M | `src/datapulse/api/app.py` |
| Document all .env variables with examples | M | `.env.example` |

#### Tests to Write

- Test: Docker compose up -> all health checks pass within 60s
- Test: All required env vars missing -> fail-fast with clear message
- Test: Kill Redis -> API returns degraded (not 500)
- Test: Kill PostgreSQL -> `/health` returns 503 with details
- Test: Slow query (>5s) -> logged with query text and duration

#### Verification
```bash
docker compose up -d --build
# Wait for health checks
curl http://localhost:8000/health/deep
make test
```

---

### Session 4: Backend API Quality (Phase 4)
**Priority**: MEDIUM-HIGH — API consistency
**Estimated scope**: ~12 files, ~15 changes
**Covers audit phases**: 4.1-4.5

#### Fixes

| Task | Severity | Files |
|------|----------|-------|
| Implement backward pagination (prev_cursor) | M9 | `src/datapulse/api/pagination.py` |
| Add date range validation (reject future dates) | M | `src/datapulse/api/routes/analytics.py` |
| Add AI client timeout parameter | M | `src/datapulse/ai_light/client.py` |
| Improve error messages — actionable, not generic | M | Multiple route files |
| Add API versioning consistency check | L | `src/datapulse/api/app.py` |
| Document all endpoints in OpenAPI schema | L | Route files (response_model params) |

#### Tests to Write

- Test: Every endpoint returns correct status codes (200/201/400/401/404/422)
- Test: Pagination — page 1, last page, out of range, zero limit
- Test: Date filters — valid range, reversed dates, future dates
- Test: Export CSV format correctness, Excel opens correctly
- Test: AI insights with empty data, with OpenRouter timeout
- Test: Concurrent requests — 50 parallel to /dashboard -> no 500s

#### Verification
```bash
make test
# Manual: test pagination in frontend
```

---

### Session 5: Frontend UX & Accessibility (Phase 5)
**Priority**: MEDIUM-HIGH — User-facing quality
**Estimated scope**: ~15 files, ~20 changes
**Covers audit phases**: 5.1-5.5

#### Fixes

| Task | Severity | Files |
|------|----------|-------|
| Fix EGP currency formatting (`ar-EG` locale) | C4 | `frontend/src/lib/formatters.ts` |
| Add aria labels to all interactive components | M10 | Multiple components |
| Split `slicer-panel.tsx` into sub-components | M11 | `frontend/src/components/filters/slicer-panel.tsx` |
| Add loading skeletons to all data pages | M | Dashboard, products, customers pages |
| Add empty state guidance (not just "No data") | M | Multiple components |
| Add metric tooltips (`?` icon with explanations) | L | `frontend/src/components/dashboard/kpi-card.tsx` |
| Fix version display — import from package.json | L | `frontend/src/components/layout/sidebar.tsx` |

#### Tests to Write

- E2E: Dashboard loads in <3 seconds with full data
- E2E: Dark mode toggle -> no visual glitches
- E2E: Mobile viewport -> all pages usable
- E2E: Navigation -> visit every page, no 404s or blank screens
- Unit: formatCurrency("1234") -> "1,234 EGP" (not "$1,234")
- Accessibility: Run axe-core scan on all pages

#### Verification
```bash
cd frontend && npm run build    # No build errors
cd frontend && npx playwright test
```

---

### Session 6: Testing & Coverage (Phase 6)
**Priority**: MEDIUM — Quality assurance
**Estimated scope**: ~20 new test files
**Covers audit phases**: 6.1-6.4

#### Fixes

| Task | Severity | Files |
|------|----------|-------|
| Create frontend component unit tests (vitest) | H8 | `frontend/src/__tests__/components/` |
| Create SWR hook unit tests | H | `frontend/src/__tests__/hooks/` |
| Create formatter/utility unit tests | M | `frontend/src/__tests__/utils/` |
| Add cross-tenant isolation test | M | `tests/test_cross_tenant_isolation.py` |
| Add concurrent upload race condition test | M | `tests/test_concurrent_uploads.py` |
| Add large dataset performance test | L | `tests/test_large_dataset_performance.py` |
| Enable vitest in CI pipeline | M | `.github/workflows/ci.yml` |

#### New Test Files

```
# Frontend unit tests (NEW)
frontend/src/__tests__/components/kpi-card.test.tsx
frontend/src/__tests__/components/sidebar.test.tsx
frontend/src/__tests__/components/filter-bar.test.tsx
frontend/src/__tests__/components/chart-card.test.tsx
frontend/src/__tests__/hooks/use-dashboard.test.ts
frontend/src/__tests__/hooks/use-forecast.test.ts
frontend/src/__tests__/utils/formatters.test.ts
frontend/src/__tests__/utils/date-utils.test.ts

# Backend security tests (NEW)
tests/test_cross_tenant_isolation.py
tests/test_concurrent_uploads.py
tests/test_api_rate_limiting.py
```

#### Verification
```bash
make test                         # Python 95%+ coverage
cd frontend && npx vitest --run   # Frontend unit tests pass
cd frontend && npx playwright test # E2E tests pass
```

---

### Session 7: i18n, Landing Page & Growth (Phases 9 + 10)
**Priority**: MEDIUM — Market readiness
**Estimated scope**: ~15 files, ~25 changes
**Covers audit phases**: 9.1-9.3, 10.1-10.8

#### Fixes

| Task | Severity | Files |
|------|----------|-------|
| Set up next-intl for i18n | H6 | `frontend/package.json`, new `frontend/messages/` |
| Create Arabic + English translation files | H | `frontend/messages/ar.json`, `frontend/messages/en.json` |
| Add locale switcher to sidebar | M | `frontend/src/components/layout/sidebar.tsx` |
| Add RTL layout support | M | `frontend/src/app/layout.tsx`, `globals.css` |
| Format dates for Egyptian locale | M | `frontend/src/lib/date-utils.ts` |
| Improve landing page value proposition | M | `frontend/src/components/marketing/hero-section.tsx` |
| Add SEO structured data (JSON-LD) | L | `frontend/src/components/marketing/json-ld.tsx` |

#### Business Strategy Deliverables (Phase 10 — No Code)

- [ ] One-sentence pitch document
- [ ] Pricing model recommendation (EGP tiers)
- [ ] GTM strategy for Egyptian pharma market
- [ ] MLP (Minimum Lovable Product) feature list
- [ ] User journey audit (clicks from signup to first dashboard)
- [ ] Retention hooks recommendation

#### Verification
```bash
cd frontend && npm run build  # Builds with i18n
# Manual: switch to Arabic, verify RTL layout
# Manual: check landing page Lighthouse score
```

---

### Session 8: DR, Multi-Tenancy & DX (Phases 12 + 13 + 15)
**Priority**: LOWER — Future readiness
**Estimated scope**: ~10 files, ~15 changes
**Covers audit phases**: 12.1-12.5, 13.1-13.6, 15.1-15.6

#### Fixes

| Task | Severity | Files |
|------|----------|-------|
| Implement tenant-scoped RLS policies | H7 | new `migrations/015_tenant_rls.sql` |
| Create disaster recovery runbook | M | new `docs/disaster-recovery.md` |
| Create architecture documentation | M12 | new `docs/ARCHITECTURE.md` (update) |
| Add tenant provisioning script/API | M | new endpoint in `api/routes/` |
| Add per-tenant rate limiting | L | `src/datapulse/api/limiter.py` |
| Create developer onboarding guide | L | update `README.md` |
| Document ADRs (Architecture Decision Records) | L | new `docs/adr/` |
| Create incident runbook | L | new `docs/runbook.md` |

#### Tests to Write

- Test: Create 2 tenants -> verify complete data isolation
- Test: Tenant A queries -> zero results from Tenant B
- Test: Fresh `docker compose up` -> health check passes
- Test: All Makefile targets run without errors
- Test: Architecture fitness — no route imports repository directly

#### Verification
```bash
make test
docker compose up -d --build && curl http://localhost:8000/health
```

---

## Session Execution Order

```
Session 1: Security Hardening          [CRITICAL] ██████████ ~3-4 hours
Session 2: Data Pipeline Resilience    [HIGH]     ████████   ~2-3 hours
Session 3: Infrastructure & CI/CD      [HIGH]     ████████   ~2-3 hours
Session 4: Backend API Quality         [MEDIUM+]  ██████     ~2 hours
Session 5: Frontend UX & Accessibility [MEDIUM+]  ██████     ~2-3 hours
Session 6: Testing & Coverage          [MEDIUM]   ██████     ~2-3 hours
Session 7: i18n, Landing & Growth      [MEDIUM]   ████████   ~3 hours
Session 8: DR, Multi-Tenancy & DX      [LOWER]    ██████     ~2-3 hours
```

**Total estimated**: 8 sessions, ~18-25 hours of Claude Code work

## How to Start Each Session

Copy this prompt pattern to start each session:

```
Execute DataPulse Master Audit — Session [N]: [Title]

Scope from plan: [paste the session's Fixes table + Tests list]

Rules:
1. Read every file before changing it
2. Every fix must have a corresponding test
3. Group into atomic commits: `fix: [description]`
4. Run `make test` after each commit
5. Report findings in table format: Severity | File | Issue | Fix
```

## Step 0: Save This Plan to Repo

Before starting any session, commit this plan + the original audit prompt to:
- `docs/plans/master-audit/README.md` — this execution plan
- `docs/plans/master-audit/AUDIT_PROMPT.md` — the full 15-phase audit prompt

This ensures any future conversation can reference the plan via the repo.

---

## Files Referenced in This Plan

Key files to modify across all sessions:
- `src/datapulse/api/auth.py` — auth bypass fix
- `src/datapulse/api/routes/explore.py` — SQL injection fix
- `src/datapulse/ai_light/service.py` — PII anonymization
- `src/datapulse/bronze/loader.py` — memory/chunking fix
- `frontend/src/lib/formatters.ts` — currency locale fix
- `nginx/default.conf` — security headers
- `.github/workflows/ci.yml` — CI improvements
- `docker-compose.prod.yml` — image pinning
- `frontend/src/middleware.ts` — CSP fix
