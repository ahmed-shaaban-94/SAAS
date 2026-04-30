# DataPulse Hardening Sprint — Zero New Features, Fix the Core

> **Date**: 2026-04-09
> **Status**: PROPOSED — awaiting approval
> **Goal**: Make DataPulse production-ready by fixing all CRITICAL/HIGH issues found across 5 deep audits
> **Principle**: No new features. Only fixes, security patches, and correctness improvements.

---

## Audit Summary

| Layer | CRITICAL | HIGH | MEDIUM | LOW | Total |
|-------|----------|------|--------|-----|-------|
| Backend Python | 2 | 8 | 7 | 5 | 22 |
| Frontend Next.js | 0 | 7 | 5 | 6 | 18 |
| dbt/SQL Models | 3 | 7 | 9 | 7 | 26 |
| Docker/CI/CD | 3 | 8 | 8 | 5 | 24 |
| Test Suite | 2 | 5 | 5 | 2 | 14 |
| **Total** | **10** | **35** | **34** | **25** | **104** |

---

## Phase H1: CRITICAL Security Fixes (Block Production)

> **Priority**: IMMEDIATE — must fix before any production deploy
> **Estimated items**: 10 CRITICAL findings

### H1.1 — Upload Service Path Traversal
- **Finding**: `file_id` in `upload/service.py:43,90` passed to `glob()` without UUID validation
- **Fix**: Validate `file_id` as UUID format before any filesystem operation
- **Files**: `src/datapulse/upload/service.py`

### H1.2 — Hardcoded Owner/Admin Email Addresses
- **Finding**: `config.py:76-77` has real emails as default owner/admin — auto-elevates anyone with those emails
- **Fix**: Move to required env vars with empty defaults; also fix `migrations/029_seed_initial_members.sql`
- **Files**: `src/datapulse/core/config.py`, `migrations/029_seed_initial_members.sql`

### H1.3 — Production Deploy Gate Bypass
- **Finding**: `deploy-prod.yml:49` uses `if: always()` — build-push runs even when staging gate fails
- **Fix**: Replace with `if: needs.gate.result == 'success'`
- **Files**: `.github/workflows/deploy-prod.yml`

### H1.4 — Secrets in SSH Shell History
- **Finding**: `deploy-staging.yml:86-88`, `deploy-prod.yml:128-130` expand secrets inline in SSH scripts
- **Fix**: Use appleboy/ssh-action `envs:` parameter instead of inline `${{ secrets.X }}`
- **Files**: `.github/workflows/deploy-staging.yml`, `.github/workflows/deploy-prod.yml`

### H1.5 — Nginx Missing TLS Protocol Restrictions
- **Finding**: No `ssl_protocols` or `ssl_ciphers` directives — allows TLS 1.0/1.1
- **Fix**: Add `ssl_protocols TLSv1.2 TLSv1.3;` + modern cipher suite
- **Files**: `nginx/default.conf`

### H1.6 — dim_billing Missing RLS
- **Finding**: `dim_billing` has no RLS post_hooks — tenant isolation gap
- **Fix**: Add RLS enable + force + grant to `datapulse_reader`
- **Files**: `dbt/models/marts/dims/dim_billing.sql`

### H1.7 — dim_date Missing Reader Grants
- **Finding**: `dim_date` never granted to `datapulse_reader` — joins will fail
- **Fix**: Add explicit GRANT or RLS post_hook with `USING (true)`
- **Files**: `dbt/models/marts/dims/dim_date.sql`, new migration

### H1.8 — 4 Tables Using Wrong RLS Cast Pattern
- **Finding**: `saved_views`, `notifications`, `dashboard_layouts`, `annotations` use `tenant_id::text =` instead of `NULLIF(...)::INT`
- **Fix**: Standardize to `NULLIF(current_setting('app.tenant_id', true), '')::INT` pattern
- **Files**: `migrations/019-022` (new migration to ALTER policies)

### H1.9 — 4 Tables Missing FK to bronze.tenants
- **Finding**: Same 4 tables have `tenant_id INT NOT NULL` without `REFERENCES`
- **Fix**: Add FK constraints via new migration
- **Files**: New migration `030_fix_tenant_fks.sql`

### H1.10 — RLS Never Tested at DB Level
- **Finding**: All tenant isolation tests mock the session — no real DB enforcement test
- **Fix**: Add integration test with real PostgreSQL (docker) verifying cross-tenant queries return 0 rows
- **Files**: New `tests/test_rls_integration.py`

---

## Phase H2: HIGH Security & Auth Fixes

> **Priority**: Before next release
> **Estimated items**: 15 findings (security-relevant HIGHs)

### H2.1 — Reseller Cross-Tenant Authorization
- **Finding**: Any authenticated user can query any reseller's dashboard/commissions/payouts
- **Fix**: Add ownership check — verify caller's tenant is associated with requested reseller_id
- **Files**: `src/datapulse/api/routes/reseller.py`

### H2.2 — `get_optional_user` Swallows 503
- **Finding**: Auth0 outage silently grants anonymous access instead of returning 503
- **Fix**: Only catch `401`/`403` HTTPExceptions; re-raise `503`
- **Files**: `src/datapulse/api/auth.py:174-177`

### H2.3 — Health Endpoint Leaks DB Errors
- **Finding**: Any request with non-empty `Authorization` header (even invalid) gets full component details
- **Fix**: Use `get_optional_user` (real verification) instead of header presence check
- **Files**: `src/datapulse/api/routes/health.py`

### H2.4 — Billing checkout URL Not Validated
- **Finding**: `success_url` and `cancel_url` passed to Stripe without domain validation
- **Fix**: Validate URLs start with `billing_base_url` domain
- **Files**: `src/datapulse/api/routes/billing.py`, `src/datapulse/billing/service.py`

### H2.5 — RBAC Session Leak
- **Finding**: `get_rbac_service` returns unclosed session
- **Fix**: Make `get_rbac_service` a generator with `finally: session.close()`
- **Files**: `src/datapulse/rbac/dependencies.py`

### H2.6 — Frontend Token Refresh Not Handled
- **Finding**: `RefreshAccessTokenError` set in session but never consumed — users see broken dashboard
- **Fix**: Add error check in `SessionProvider` wrapper or layout — redirect to sign-in
- **Files**: `frontend/src/app/(app)/layout.tsx` or new `SessionGuard` component

### H2.7 — Frontend Open Redirect in Login
- **Finding**: `callbackUrl` from search params passed to `signIn()` without validation
- **Fix**: Validate `callbackUrl` is relative path
- **Files**: `frontend/src/app/login/page.tsx`

### H2.8 — Embed Route Blocked by Middleware
- **Finding**: `/embed/[token]` not in `PUBLIC_PATHS` — unauthenticated embed users redirected to login
- **Fix**: Add `"/embed"` to `PUBLIC_PATHS`
- **Files**: `frontend/src/middleware.ts`

### H2.9 — Mutations Missing Auth Headers
- **Finding**: `updateMember`, `removeMember`, `removeSector` use raw `fetch()` without auth
- **Fix**: Use shared `_request` wrapper or `getAuthHeaders()`
- **Files**: `frontend/src/hooks/use-members.ts`

### H2.10 — Notifications Wrong API Path
- **Finding**: `useNotifications` uses `/notifications` instead of `/api/v1/notifications`
- **Fix**: Add `/api/v1/` prefix
- **Files**: `frontend/src/hooks/use-notifications.ts`

### H2.11 — Entrypoint Swallows Migration Failures
- **Finding**: API starts even when prestart.sh fails — serves against broken schema
- **Fix**: Let migration failures propagate (remove `if ! ... ; then warn; fi`)
- **Files**: `scripts/entrypoint.sh`

### H2.12 — DB Reader Password Regenerated on Restart
- **Finding**: `DB_READER_PASSWORD` generates time-based value when unset — breaks on restart
- **Fix**: Use `:?` syntax to require the env var
- **Files**: `scripts/prestart.sh`

### H2.13 — E2E Tests Never Block Deploy
- **Finding**: `continue-on-error: true` on Playwright job — broken user flows can ship
- **Fix**: Remove `continue-on-error: true` (or gate deploy on it)
- **Files**: `.github/workflows/ci.yml`

### H2.14 — CI Coverage Threshold Mismatch
- **Finding**: CI uses `--cov-fail-under=80` but docs say 95%
- **Fix**: Align to 95% in CI; add `--cov=datapulse` source target
- **Files**: `.github/workflows/ci.yml`

### H2.15 — No Secret Scanner in Security Workflow
- **Finding**: No Gitleaks/Trufflehog/Bandit in security.yml
- **Fix**: Add `gitleaks/gitleaks-action` + `PyCQA/bandit`
- **Files**: `.github/workflows/security.yml`

---

## Phase H3: Data Integrity & Semantic Fixes

> **Priority**: Critical for analytics trustworthiness
> **Estimated items**: 12 findings

### H3.1 — dim_billing ROW_NUMBER → MD5 Surrogate
- **Finding**: Alphabetical ROW_NUMBER means key values shift on data changes
- **Fix**: Replace with MD5-based hash consistent with other dims
- **Files**: `dbt/models/marts/dims/dim_billing.sql`

### H3.2 — Unknown Dimension Rows Hardcoded to tenant_id=1
- **Finding**: `dim_product`, `dim_customer`, `dim_site`, `dim_staff` Unknown rows only for tenant 1
- **Fix**: CROSS JOIN with `SELECT DISTINCT tenant_id FROM stg_sales`
- **Files**: 4 dim SQL files

### H3.3 — agg_sales_by_customer Missing total_net_amount
- **Finding**: Column computed in CTE but dropped from final SELECT; schema.yml expects it
- **Fix**: Add `cm.total_net_amount` to final SELECT
- **Files**: `dbt/models/marts/aggs/agg_sales_by_customer.sql`

### H3.4 — Gross vs Net Inconsistency Across Aggs
- **Finding**: `avg_basket_size` uses gross in 3 aggs but net in `agg_sales_daily`
- **Fix**: Standardize all to `SUM(f.net_amount)` for basket size
- **Files**: `agg_sales_by_product.sql`, `agg_sales_monthly.sql`, `agg_sales_by_customer.sql`

### H3.5 — Staff avg_transaction_value Uses COUNT(*) Not Distinct Invoices
- **Finding**: Counts line items, not baskets — misleading vs other agg tables
- **Fix**: Replace `COUNT(*)` with `COUNT(DISTINCT f.invoice_id)`
- **Files**: `dbt/models/marts/aggs/agg_sales_by_staff.sql`

### H3.6 — feat_customer_segments Monetary Uses Gross
- **Finding**: RFM monetary = gross, description says net
- **Fix**: Change to `SUM(f.net_amount)`
- **Files**: `dbt/models/marts/features/feat_customer_segments.sql`, `feat_customer_health.sql`

### H3.7 — feat_customer_health Wrong Schema
- **Finding**: `schema='public_marts'` instead of `schema='marts'`
- **Fix**: Correct schema + add RLS post_hooks
- **Files**: `dbt/models/marts/features/feat_customer_health.sql`

### H3.8 — metrics_summary Incremental Overwrites Entire Year
- **Finding**: WHERE predicate reprocesses all current-year data on every run
- **Fix**: Change to rolling 7-day window
- **Files**: `dbt/models/marts/aggs/metrics_summary.sql`

### H3.9 — Gamification Tables Missing tenant FK
- **Finding**: 8 gamification tables have no `REFERENCES bronze.tenants`
- **Fix**: New migration adding FK constraints
- **Files**: New migration

### H3.10 — stg_sales Dedup Key Includes Quantity
- **Finding**: Amendments/corrections with different quantity survive as duplicates
- **Fix**: Remove `quantity` from PARTITION BY
- **Files**: `dbt/models/staging/stg_sales.sql`

### H3.11 — dbt Unique Tests Break Multi-Tenant
- **Finding**: `dim_customer.customer_id` and `dim_site.site_code` uniqueness tests fail with 2+ tenants
- **Fix**: Replace with `unique_combination_of_columns` on `(tenant_id, column)`
- **Files**: `dbt/models/marts/dims/_dims__models.yml`

### H3.12 — Missing Migration 006
- **Finding**: Gap in migration sequence (005 → 007)
- **Fix**: Add placeholder `006_placeholder.sql` with comment explaining skip
- **Files**: New `migrations/006_placeholder.sql`

---

## Phase H4: Frontend UX & Reliability

> **Priority**: User-facing quality
> **Estimated items**: 8 findings

### H4.1 — CalendarHeatmap Dark Mode Hydration Mismatch
- Replace `document.documentElement` check with `useChartTheme()` hook

### H4.2 — EgyptMap No Error State
- Add `if (error) return <ErrorRetry />` pattern

### H4.3 — CalendarHeatmap No Error State
- Add error handling for both `useHeatmap` calls

### H4.4 — Token Cache Stale After Sign-Out
- Clear `_cachedToken` on session change; remove dead localStorage fallback

### H4.5 — useDashboard Inconsistent SWR Key Pattern
- Refactor to use standard `path` + `params` separation

### H4.6 — Nginx HTTP→HTTPS Redirect Missing
- Split into two server blocks; port 80 returns 301

### H4.7 — Nginx client_max_body_size Conflicts With App Limit
- Align `client_max_body_size` with `MAX_FILE_SIZE_MB` (500M)

### H4.8 — ForecastCard/TargetProgress ErrorRetry Missing onRetry
- Pass `onRetry={() => mutate()}` to enable retry button

---

## Phase H5: Test Coverage Gaps

> **Priority**: Safety net for all above fixes
> **Estimated items**: 8 areas

### H5.1 — Upload Service Tests (NEW)
- Path traversal, extension spoofing, size limits, concurrent confirm

### H5.2 — Billing/Stripe Webhook Tests (NEW)
- `handle_webhook_event`, checkout completed, subscription deleted, payment failed

### H5.3 — RLS DB Integration Tests (NEW)
- Real PostgreSQL container, verify cross-tenant queries blocked

### H5.4 — E2E Auth Flow Tests (NEW)
- Login redirect, token refresh, sign-out, protected routes

### H5.5 — E2E Broken Dashboard Sections
- Remove `if (await element.isVisible())` guards — assert elements exist

### H5.6 — Concurrent Pipeline Execution Test
- Verify two simultaneous pipeline triggers don't corrupt records

### H5.7 — Token Refresh Flow Test
- Verify expired token triggers refresh, failed refresh redirects to login

### H5.8 — Reseller Authorization Tests
- Verify cross-tenant access denied

---

## Execution Order

```
H1 (CRITICAL security)     ──── Must be first, blocks production
  │
  v
H5.1-H5.3 (Tests for H1)  ──── Write tests for critical fixes
  │
  v
H2 (HIGH security/auth)    ──── Fix auth gaps, deploy safety
  │
  v
H3 (Data integrity)        ──── Fix analytics trustworthiness
  │
  v
H4 (Frontend UX)           ──── Fix broken UI components
  │
  v
H5.4-H5.8 (Remaining tests) ── Safety net for all fixes
  │
  v
Production deploy v0.8.0   ──── Tag release after all phases pass
```

---

## Success Criteria

- [ ] 0 CRITICAL findings remain
- [ ] 0 HIGH security findings remain
- [ ] All agg tables use consistent net_amount for basket_size
- [ ] RLS enforced and tested at DB level for all tables
- [ ] E2E auth flow tested
- [ ] Upload service has path traversal protection + tests
- [ ] CI coverage threshold aligned at 95%
- [ ] Deploy pipeline cannot bypass staging gate
- [ ] TLS 1.2+ enforced
- [ ] No secrets in SSH shell history

---

## Out of Scope

- Phase 5 (Multi-tenancy self-service onboarding)
- Phase 6-10 (all expansion features)
- New dashboard features
- New API endpoints
- Mobile app features

**This sprint is about making what exists trustworthy, not adding more.**
