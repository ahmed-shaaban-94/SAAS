# DataPulse Master Audit — Full Execution Plan

## Context

A 15-phase comprehensive audit of DataPulse — a pharmaceutical sales analytics SaaS platform. This plan maps 15 audit phases into **8 focused sessions**, each with full checklists, creative improvements, tests, and tool recommendations.

**IMPORTANT — Verify-First Approach**: This plan was created from a point-in-time scan (2026-04-04). Some findings may already be fixed (e.g., by "The Great Fix" or subsequent PRs). For EVERY finding below:
1. **Read the current code first** — do NOT assume the issue still exists
2. **Verify** the issue is present in the current codebase
3. **Skip** anything already fixed — mark as "VERIFIED OK" and move on
4. **Fix** only confirmed issues
5. **Discover** new issues not in this list — the checklists are the real work, findings are just hints

**8 sessions, ordered by business risk.** Each session is self-contained — start any session in a new conversation.

---

## Potential Findings to Verify

These were flagged during a quick scan. **Some may already be fixed.** Read the code first.

### CRITICAL (Verify First)

| # | Check For | Where to Look | Risk if Present |
|---|-----------|---------------|-----------------|
| C1 | Dev mode auth bypass granting admin without auth configured | `src/datapulse/api/auth.py` — look for fallback when neither API_KEY nor AUTH0_DOMAIN set | Full data access |
| C2 | SQL injection in Explore/SQL Lab via identifier injection | `src/datapulse/api/routes/explore.py` + `src/datapulse/explore/sql_builder.py` | Code execution |
| C3 | PII (customer/product names) sent to external AI (OpenRouter) | `src/datapulse/ai_light/service.py` — trace what data goes into prompts | Privacy violation |
| C4 | Currency formatting using wrong locale (en-US instead of ar-EG) | `frontend/src/lib/formatters.ts` — check formatCurrency function | Wrong display for Egyptian market |

### HIGH (Verify First)

| # | Check For | Where to Look |
|---|-----------|---------------|
| H1 | Production Docker images using `latest` tag fallback | `docker-compose.prod.yml` — look for `${IMAGE_TAG:-latest}` |
| H2 | Pipeline webhook secret defaulting to empty/disabled | `src/datapulse/api/auth.py` — look for PIPELINE_WEBHOOK_SECRET handling |
| H3 | Bronze loader loading all rows at once (OOM risk) | `src/datapulse/bronze/loader.py` — check if chunked/batched |
| H4 | SSE stream endpoint not checking tenant_id ownership | `src/datapulse/api/routes/pipeline.py` — stream_run_progress function |
| H5 | mypy set to continue-on-error in CI | `.github/workflows/ci.yml` — search for `continue-on-error` |
| H6 | No i18n infrastructure (hardcoded English strings) | `frontend/src/` — check if next-intl or similar is set up |
| H7 | Tenant-scoped RLS policies not implemented | `migrations/` — check if tenant-level USING clauses exist |
| H8 | No frontend component unit tests | `frontend/src/__tests__/` — check for vitest component tests |

### MEDIUM (Verify First)

| # | Check For | Where to Look |
|---|-----------|---------------|
| M1 | Missing HSTS header | `nginx/default.conf` |
| M2 | CSP allows unsafe-inline in production | `frontend/src/middleware.ts` |
| M3 | Audit log table missing user_id column | Check audit_log table schema |
| M4 | E2E tests not in CI pipeline | `.github/workflows/ci.yml` |
| M5 | AI response JSON not validated against schema | `src/datapulse/ai_light/service.py` |
| M6 | Forecasting has no minimum series length check | `src/datapulse/forecasting/service.py` |
| M7 | Custom SQL quality check has no execution timeout | `src/datapulse/pipeline/quality_engine.py` |
| M8 | BETWEEN filter values not type-validated | `src/datapulse/api/filters.py` |
| M9 | No backward pagination (prev_cursor) | `src/datapulse/api/pagination.py` |
| M10 | Low ARIA label coverage across frontend components | `frontend/src/components/` |
| M11 | Large component files (>300 lines) needing split | `frontend/src/components/filters/slicer-panel.tsx` |
| M12 | Architecture documentation missing or outdated | `docs/ARCHITECTURE.md` |

---

## Session 1: Security Hardening

**Priority**: CRITICAL | **Covers**: Phases 2 + 14 | **~3-4 hours**

### Scope

```
src/datapulse/api/auth.py, jwt.py
src/datapulse/core/security.py
src/datapulse/ai_light/ (all files — PII trace)
src/datapulse/api/routes/ (all 13 route files — auth decorators)
src/datapulse/explore/sql_builder.py
src/datapulse/pipeline/quality_engine.py
frontend/src/lib/auth.ts
frontend/src/middleware.ts
frontend/src/app/api/auth/[...nextauth]/route.ts
migrations/ (RLS policies)
nginx/default.conf
docker-compose*.yml (secrets scan)
frontend/src/app/(marketing)/terms/page.tsx
frontend/src/app/(marketing)/privacy/page.tsx
structlog configuration
Redis cache contents
```

### Audit Checklist

#### 2.1 Authentication
- [ ] Read all auth files (jwt.py, auth.py, NextAuth config)
- [ ] JWT validation: audience/issuer verified? Token expiry checked?
- [ ] **FIX C1**: Endpoints WITHOUT auth that should have it?
- [ ] API key auth: keys stored? Hashed? Rotatable?
- [ ] Rate limiting on login/auth endpoints?
- [ ] Session management: timeout, refresh, revocation

#### 2.2 Authorization (RLS)
- [ ] Read ALL PostgreSQL RLS policies
- [ ] **FIX H7**: tenant_id enforced on EVERY query? Any bypass?
- [ ] Can a user access another tenant's data via any endpoint?
- [ ] Admin endpoints properly gated?
- [ ] Write cross-tenant access test

#### 2.3 Input Validation
- [ ] Every Pydantic model: fields validated (min/max, regex, enums)?
- [ ] **FIX C2**: SQL injection — all queries parameterized? Any raw f-strings?
- [ ] File upload: type/size validated? Malicious file blocked?
- [ ] SQL Lab: query sandboxing? Can users DROP tables?
- [ ] Export endpoints: path traversal protection?

#### 2.4 Secrets and Exposure
- [ ] Scan entire codebase for hardcoded secrets (grep patterns)
- [ ] Error responses leaking internals (stack traces, DB info)?
- [ ] API docs (Swagger/ReDoc) exposed in production?
- [ ] Debug endpoints accessible in prod mode?

#### 2.5 Frontend Security
- [ ] XSS protection: user content sanitized before rendering?
- [ ] CSRF protection on state-changing requests?
- [ ] Auth0 client secret exposed to browser?
- [ ] API keys stored in localStorage? (should use httpOnly cookies)

#### 14.1 Egyptian Data Protection Law (PDPL 2020)
- [ ] Read Terms of Service and Privacy Policy — real or placeholder?
- [ ] Explicit consent before processing user data?
- [ ] Data controller + data processor designation?
- [ ] Users can request data copy (portability)?
- [ ] Users can request permanent deletion (not soft-delete)?
- [ ] Data breach notification process documented?
- [ ] Data stored in Egypt or leaving to foreign servers?

#### 14.2 AI and Third-Party Data Leakage
- [ ] **FIX C3**: Trace EXACTLY what data goes to OpenRouter
- [ ] Customer names sent to OpenRouter? (must not)
- [ ] Staff names sent? (must not)
- [ ] Drug names + quantities sent? (commercially sensitive)
- [ ] Data anonymization layer before AI calls?
- [ ] OpenRouter data retention policy?
- [ ] User toggle to disable AI entirely?
- [ ] AI responses cached to avoid duplicate calls?

#### 14.3 Pharma Data Sensitivity
- [ ] Classify ALL data fields: Public / Internal / Confidential / Restricted
- [ ] Can sales rep see other reps' performance via API?
- [ ] Can branch manager see other branches' data?
- [ ] Export of customer lists restricted by role?

#### 14.4 Audit Trail
- [ ] **FIX M3**: EVERY data access logged (who, what, when, from where)?
- [ ] Logins logged (successful + failed, with IP)?
- [ ] Exports logged?
- [ ] AI queries logged (what asked, what returned)?
- [ ] Pipeline runs logged with who triggered?
- [ ] Audit log immutable (nobody can delete entries)?

#### 14.5 PII in Logs and Cache
- [ ] Grep structlog output for PII patterns: emails, phones, names
- [ ] Redis cache stores customer/staff names?
- [ ] Error logs sanitized (no PII in stack traces)?
- [ ] API request logs safe (no sensitive query params)?
- [ ] Sentry captures PII in error reports?

### Verify and Fix (read code first — skip if already fixed)

| Verify | If Present, Fix | Where to Look |
|--------|----------------|---------------|
| C1: Auth bypass in dev mode? | Require at least one auth method in production | `src/datapulse/api/auth.py` |
| C2: SQL injection in explore? | Add identifier validation before text() parsing | `src/datapulse/api/routes/explore.py`, `explore/sql_builder.py` |
| C3: PII in AI prompts? | Add anonymization layer (replace names with codes) | `src/datapulse/ai_light/service.py` |
| H2: Webhook secret optional? | Make required in production | `src/datapulse/api/auth.py` |
| H4: SSE stream no tenant check? | Add tenant_id ownership verification | `src/datapulse/api/routes/pipeline.py` |
| M1: No HSTS header? | Add Strict-Transport-Security | `nginx/default.conf` |
| M2: CSP unsafe-inline in prod? | Remove for production builds | `frontend/src/middleware.ts` |
| M3: Audit log no user_id? | Add user_id column via migration | Check audit_log schema |
| M5: AI response unvalidated? | Add Pydantic model for AI response | `src/datapulse/ai_light/service.py` |
| M7: Custom SQL no timeout? | Add execution timeout (5s default) | `src/datapulse/pipeline/quality_engine.py` |

### Creative Improvements

1. Security score dashboard for tenant admins
2. Audit log viewer — searchable, exportable in admin panel
3. Session management UI — see active sessions + revoke
4. 2FA support (TOTP for admin accounts)
5. AI anonymization toggle — "AI Privacy Mode: ON"
6. Data classification badges on every page/export
7. Privacy dashboard for admins — data stored, AI usage, export log
8. Consent re-confirmation after 12 months (Egyptian law)
9. "Who accessed my data?" page for tenant admins
10. Compliance export pack — one-click policy/DPA/audit/inventory download

### Tests to Write

```
test_unauthenticated_request_every_protected_endpoint -> 401
test_cross_tenant_access_attempt -> 403
test_sql_injection_attempts_sql_lab -> blocked
test_malicious_file_upload -> rejected_with_clear_error
test_expired_jwt -> 401_with_token_expired_message
test_rate_limit_exceeded -> 429_with_retry_after_header
test_dev_mode_bypass_disabled_in_production -> startup_error
test_ai_insight_request_http_payload -> zero_PII
test_structlog_output_100_requests -> grep_PII_zero_matches
test_redis_cache_dump -> grep_customer_staff_names_zero
test_sentry_error_payload -> no_PII_in_context
test_delete_tenant -> ALL_data_gone_from_postgres_redis_files
test_role_based_export -> sales_rep_cannot_export_others_data
test_audit_log_immutable -> DELETE_on_audit_table_blocked
test_privacy_page -> exists_real_content_mentions_egyptian_law
```

### Tools: Presidio (PII), CookieYes (privacy), Vault (secrets)

---

## Session 2: Data Pipeline Resilience

**Priority**: HIGH | **Covers**: Phase 3 | **~2-3 hours**

### Scope

```
src/datapulse/bronze/ (loader.py, column_map.py)
src/datapulse/pipeline/ (executor, quality, quality_engine, quality_service, rollback, retry, checkpoint)
dbt/ (all models, schemas, tests)
migrations/ (all files)
src/datapulse/analytics/ (repository layer — SQL queries)
```

### Audit Checklist

#### 3.1 Bronze Layer (Ingestion)
- [ ] Read `bronze/loader.py` completely
- [ ] **FIX H3**: Memory usage — 2.27M rows at once or chunked?
- [ ] Error handling — malformed Excel?
- [ ] Duplicate detection — re-uploads?
- [ ] Data types: dates, currencies, nulls?
- [ ] Rollback if ingestion fails midway?

#### 3.2 dbt Models (Silver to Gold)
- [ ] Read ALL dbt models (staging, marts, aggregations)
- [ ] `stg_sales.sql`: deduplication correct? Edge cases?
- [ ] Dimension tables: surrogate keys consistent?
- [ ] Fact table joins: COALESCE(-1) defaults correct?
- [ ] Aggregation models: incremental or full refresh?
- [ ] dbt tests: uniqueness, not_null, referential integrity, accepted_values?

#### 3.3 Query Performance
- [ ] Analytics repository SQL queries — efficient?
- [ ] Proper indexes on date, tenant_id, product_key?
- [ ] CTEs vs subqueries?
- [ ] Redis cache TTL strategy?
- [ ] N+1 query patterns?
- [ ] EXPLAIN ANALYZE top 5 queries

#### 3.4 Data Quality
- [ ] Quality gates: what do they check?
- [ ] Quality fails: pipeline stops? Notifies?
- [ ] Data freshness checks?

### Verify and Fix (read code first — skip if already fixed)

| Verify | If Present, Fix | Where to Look |
|--------|----------------|---------------|
| H3: All rows loaded at once? | Implement chunked read-write (100K batches) | `src/datapulse/bronze/loader.py` |
| Migration rollback on failure? | Add chain rollback mechanism | `src/datapulse/bronze/loader.py` |
| File discovery path traversal? | Add depth limit and path validation | `src/datapulse/bronze/loader.py` |
| Unknown billing_type silently ignored? | Add quality check for unmapped values | `src/datapulse/pipeline/quality.py` |
| fct_sales unknown dim (-1) untested? | Add dbt test: count < 5% of total | `dbt/models/marts/facts/` schema YAML |
| M8: BETWEEN filter unvalidated? | Add type coercion and validation | `src/datapulse/api/filters.py` |
| M6: Forecast no min length? | Add check for minimum series length | `src/datapulse/forecasting/service.py` |

### Creative Improvements

1. **Upload wizard**: Select file -> preview rows -> confirm columns -> progress bar -> success CTA
2. **Data quality score**: "Your data is 94% clean, 3 issues found"
3. **Smart duplicate detection**: On re-upload diff: "243 new, 12 updated, 0 duplicates"
4. **Pipeline timeline**: Visual Bronze -> Silver -> Gold with duration + row counts

### Tests to Write

```
test_upload_valid_excel -> all_stages_complete
test_upload_missing_columns -> clear_error_listing_expected
test_upload_bad_dates_nulls -> quality_gate_catches
test_upload_duplicate_file -> no_duplicate_rows
test_pipeline_fails_silver -> bronze_preserved_clear_error
test_dbt_output_row_counts_match
test_aggregation_totals_match_fact  # reconciliation
test_query_1M_rows_under_2_seconds
test_upload_500K_rows -> no_OOM
```

### Tools: Great Expectations / dbt-expectations

---

## Session 3: Infrastructure and CI/CD

**Priority**: HIGH | **Covers**: Phases 1 + 11 | **~2-3 hours**

### Scope

```
docker-compose*.yml, nginx/, .github/workflows/, .env.example
scripts/, Makefile, pyproject.toml, Dockerfile
src/datapulse/core/ (logging), structlog, n8n workflows
```

### Audit Checklist

#### 1.1 Docker Compose Health
- [ ] All services: health checks, restart policies, memory limits, depends_on
- [ ] No hardcoded secrets
- [ ] Volumes persistent? Named vs bind?
- [ ] Network isolation
- [ ] **FIX H1**: Image pinning (not `latest`)

#### 1.2 Nginx Configuration
- [ ] SSL/TLS, rate limiting, CORS, security headers (HSTS, CSP)
- [ ] Gzip, static caching, proxy timeouts
- [ ] WebSocket/SSE support
- [ ] 502/503 error page

#### 1.3 CI/CD Pipeline
- [ ] **FIX M4**: E2E tests in CI?
- [ ] **FIX H5**: mypy enforced?
- [ ] Frontend tests in CI?
- [ ] Docker build caching?
- [ ] Deployment stages?
- [ ] Dependency scanning?

#### 1.4 Database Migrations
- [ ] Reversible (downgrade)?
- [ ] Gaps or conflicts?
- [ ] RLS migration?

#### 1.5 Environment
- [ ] .env.example documented?
- [ ] Separate dev/staging/prod configs?
- [ ] Pydantic defaults safe?

#### 11.1-11.5 Observability
- [ ] Structured JSON logging in production
- [ ] Request logging: request_id, user_id, tenant_id, duration
- [ ] Sensitive fields redacted
- [ ] Sentry configured (not optional)
- [ ] `/health` checks ALL services
- [ ] Slow queries logged (>1s)
- [ ] Business metrics tracked (tenants, uploads, errors)

### Verify and Fix (read code first — skip if already fixed)

| Verify | If Present, Fix | Where to Look |
|--------|----------------|---------------|
| H1: Prod images use `latest`? | Pin to semver, remove fallback | `docker-compose.prod.yml` |
| H5: mypy continue-on-error? | Set to false | `.github/workflows/ci.yml` |
| M4: E2E tests in CI? | Add Playwright step | `.github/workflows/ci.yml` |
| Trivy scanning in CI? | Add image scan step | `.github/workflows/security.yml` |
| AUTH0 vars default empty? | Use `${VAR:?}` in prod | `docker-compose.prod.yml` |
| `/health/deep` exists? | Add deep check endpoint | `src/datapulse/api/routes/health.py` |
| Request correlation ID? | Add to structured logging | `src/datapulse/api/app.py` |
| .env.example complete? | Document all vars | `.env.example` |

### Creative Improvements

1. One-command setup (`make setup` zero to working <2 min)
2. `/status` health dashboard page
3. Docker auto-recovery with restart policies
4. Ops dashboard (internal admin — uptime, users, pipeline, errors)
5. Tenant health score (green/yellow/red)
6. Self-metrics anomaly detection
7. Incident playbook runbook

### Tests to Write

```
test_smoke_all_docker_services -> health_pass
test_env_vars_missing -> fail_fast_clear_message
test_migration_upgrade_downgrade_cycle
test_kill_redis -> degraded_not_500
test_kill_postgres -> health_503
test_500_error -> sentry_within_30s
test_slow_query_5s -> logged
```

### Tools: Sentry, Renovate, Trivy, Lighthouse CI, Grafana+Prometheus, Loki, pgBackRest, Better Uptime

---

## Session 4: Backend API Quality

**Priority**: MEDIUM-HIGH | **Covers**: Phases 4 + 7 | **~3 hours**

### Scope

```
src/datapulse/api/ (all 13 route files, 84 endpoints)
src/datapulse/analytics/, forecasting/, ai_light/, explore/
src/datapulse/targets/, reports/, export/, embed/
```

### Audit Checklist

#### 4.1 API Design
- [ ] Read ALL 13 route files
- [ ] Consistent error response format
- [ ] Proper HTTP status codes
- [ ] Query params validated
- [ ] Pagination consistent
- [ ] Response schemas documented
- [ ] API versioning consistent

#### 4.2 Error Handling
- [ ] Service calls in try/except
- [ ] Useful error messages
- [ ] DB errors translated
- [ ] External failures (OpenRouter, n8n) graceful
- [ ] Global exception handler

#### 4.3 Performance
- [ ] Slow endpoints cached
- [ ] Redis invalidation strategy
- [ ] Blocking calls that should be async
- [ ] Rate limiting per-user or per-IP
- [ ] Large responses streamed

#### 4.4-4.5 + 7.1-7.3 Forecasting, AI, SQL Lab
- [ ] Holt-Winters tuned or defaults
- [ ] Insufficient data handling
- [ ] Forecast accuracy (MAPE/MAE)
- [ ] Auto-select best model
- [ ] Prompt injection protection
- [ ] AI cached, token limits, fallback
- [ ] SQL Lab: DROP/DELETE blocked, timeout, tenant scoping

### Verify and Fix (read code first — skip if already fixed)

| Verify | If Present, Fix | Where to Look |
|--------|----------------|---------------|
| M9: No backward pagination? | Implement prev_cursor | `src/datapulse/api/pagination.py` |
| Date range accepts future? | Add validation, reject future dates | `src/datapulse/api/routes/analytics.py` |
| AI client no timeout? | Add timeout parameter | `src/datapulse/ai_light/client.py` |
| Generic error messages? | Make actionable (WHAT/WHERE/HOW) | Multiple route files |
| M6: Forecast no min length? | Add series length check | `src/datapulse/forecasting/service.py` |
| M5: AI response unvalidated? | Add Pydantic response model | `src/datapulse/ai_light/service.py` |
| M8: BETWEEN unvalidated? | Add type coercion | `src/datapulse/api/filters.py` |

### Creative Improvements

1. API playground in dashboard
2. Caching indicators ("Updated 5 min ago" + refresh)
3. Forecast confidence bands on charts
4. AI chat: "Ask DataPulse: Why did sales drop?"
5. Webhook notifications for alerts
6. Forecast explainer: "Sales +15% because Ramadan starts soon"
7. What-if scenarios
8. Natural language queries -> auto SQL
9. Saved insights library

### Tests to Write

```
test_every_endpoint_status_codes  # 200/201/400/401/404/422
test_pagination_all_edge_cases
test_date_filters_valid_reversed_future
test_export_csv_excel_large
test_rate_limiting_429
test_concurrent_50_dashboard -> no_500
test_forecast_36m_6m_1m_data
test_ai_valid_empty_timeout
test_sql_lab_SELECT_ok_DROP_blocked_timeout
```

---

## Session 5: Frontend UX and Accessibility

**Priority**: MEDIUM-HIGH | **Covers**: Phase 5 | **~3 hours**

### Scope

```
frontend/src/app/ (26 pages)
frontend/src/components/ (78 components)
frontend/src/hooks/ (40 SWR hooks)
frontend/src/contexts/, lib/, globals.css, tailwind.config.ts
```

### Audit Checklist

#### 5.1 Component Quality
- [ ] Read ALL 78 components: loading, error, empty states, responsive
- [ ] Components >300 lines -> split
- [ ] Consistent TypeScript interfaces
- [ ] Unused components/imports

#### 5.2 UX for Non-Technical Users (CRITICAL)
- [ ] Navigation <3 clicks to dashboard
- [ ] Charts labeled (Arabic + English)
- [ ] **FIX C4**: EGP formatting correct
- [ ] Tooltips explaining metrics
- [ ] Onboarding flow for first-time
- [ ] Plain language errors
- [ ] Guided upload flow

#### 5.3 Visual Design
- [ ] Theme tokens everywhere
- [ ] Typography hierarchy
- [ ] 8px spacing grid
- [ ] Dark mode all pages, contrast
- [ ] Colorblind-friendly charts
- [ ] Landing page compelling

#### 5.4 Performance
- [ ] Bundle size (`next build`)
- [ ] Images optimized (next/image)
- [ ] Code splitting / lazy loading
- [ ] SWR revalidation intervals
- [ ] CLS on dashboard load

#### 5.5 Accessibility
- [ ] **FIX M10**: Keyboard navigation
- [ ] ARIA labels
- [ ] WCAG AA contrast
- [ ] Focus indicators
- [ ] RTL support

### Verify and Fix (read code first — skip if already fixed)

| Verify | If Present, Fix | Where to Look |
|--------|----------------|---------------|
| C4: Currency uses en-US? | Change to ar-EG locale for EGP | `frontend/src/lib/formatters.ts` |
| M10: Low aria label coverage? | Add to all interactive elements | `frontend/src/components/` |
| M11: slicer-panel >300 lines? | Split into sub-components | `frontend/src/components/filters/slicer-panel.tsx` |
| Pages missing loading skeletons? | Add skeleton states | Dashboard, products, customers pages |
| Empty states say "No data"? | Add helpful guidance | Multiple components |
| Metrics have no tooltips? | Add `?` icon with explanation | `frontend/src/components/dashboard/kpi-card.tsx` |

### Creative Improvements (UX Gems)

1. Welcome dashboard with 4 KPI cards + sparklines
2. "What happened today?" AI summary
3. Guided upload wizard (5 steps)
4. Contextual help `?` bubbles on every metric
5. Quick actions FAB: Upload, Export, Ask AI, Set Alert
6. Smart date presets: "Ramadan 2025", "Summer 2025"
7. Mobile-first push-style alerts
8. Celebration confetti on target hit
9. Comparison mode: "This Month vs Last Month"
10. One-click PDF report with logo + charts + AI summary

### Tests to Write

```
E2E: dashboard_loads_under_3s
E2E: upload_flow -> data_in_dashboard
E2E: date_filter -> charts_update
E2E: dark_mode -> no_glitches
E2E: mobile -> all_usable
E2E: navigation -> no_404s
Visual: screenshot_comparison
A11y: axe_core_scan
Unit: SWR_hooks_data_shape
Unit: formatCurrency("1234") -> "1,234 EGP"
```

### Tools: axe-core, Storybook, Chromatic, react-pdf

---

## Session 6: Testing and Coverage

**Priority**: MEDIUM | **Covers**: Phase 6 | **~2-3 hours**

### Scope

```
tests/ (80 files), frontend/e2e/ (11 specs)
conftest.py, pytest/vitest config, CI jobs
```

### Audit Checklist

#### 6.1 Backend Coverage
- [ ] `pytest --cov` report
- [ ] Modules <90%
- [ ] Edge cases (empty, huge, malformed)
- [ ] Error paths (not just happy)
- [ ] Realistic fixtures
- [ ] Transaction rollback

#### 6.2 Frontend Tests
- [ ] **FIX H8**: Create vitest component tests
- [ ] SWR hook tests
- [ ] Filter context tests
- [ ] Formatter/validator tests

#### 6.3 E2E Tests
- [ ] All 11 specs — critical journeys covered?
- [ ] Enable in CI
- [ ] Flaky tests? Proper waits?

#### 6.4 Infrastructure
- [ ] Test DB isolated
- [ ] Fixtures auto-cleaned
- [ ] Test data factory
- [ ] Parallel safety

### New Test Files to Create

```
# Frontend (vitest)
frontend/src/__tests__/components/kpi-card.test.tsx
frontend/src/__tests__/components/sidebar.test.tsx
frontend/src/__tests__/components/filter-bar.test.tsx
frontend/src/__tests__/hooks/use-dashboard.test.ts
frontend/src/__tests__/hooks/use-forecast.test.ts
frontend/src/__tests__/utils/formatters.test.ts

# Backend (pytest)
tests/test_cross_tenant_isolation.py
tests/test_pipeline_failure_recovery.py
tests/test_concurrent_uploads.py
tests/test_large_dataset_performance.py
tests/test_api_rate_limiting.py
tests/test_export_large_file.py
tests/test_forecasting_edge_cases.py
tests/test_ai_insights_fallback.py
```

### Creative Improvements

1. CI badge + test report link
2. Mutation testing (mutmut)
3. Contract testing (Pact)
4. Performance tests (k6/Locust)
5. Chaos testing (kill service during E2E)

### Tools: k6/Locust, Pact, mutmut

---

## Session 7: i18n, Landing and Business Strategy

**Priority**: MEDIUM | **Covers**: Phases 9 + 10 | **~3 hours**

### Scope

```
frontend/src/app/(marketing)/, frontend/public/
All UI strings, SEO metadata
Business analysis (strategic, no code)
```

### Audit Checklist

#### i18n (Phase 9)
- [ ] **FIX H6**: Hardcoded strings -> translation files
- [ ] RTL layout for Arabic
- [ ] Dates for Egyptian locale
- [ ] EGP formatting
- [ ] next-intl setup
- [ ] Locale switcher
- [ ] Chart labels bilingual
- [ ] PDF exports in Arabic
- [ ] AI output language configurable

#### Business (Phase 10)
- [ ] Landing page: answers "What? Who? Why?" in 5 seconds
- [ ] One-sentence pitch
- [ ] Competitive moat
- [ ] Pricing model (Freemium / Per-seat / Tiered)
- [ ] User journey: clicks from signup to dashboard
- [ ] Empty states guide users
- [ ] Sample data for exploration
- [ ] Time-to-value < 5 minutes
- [ ] Retention hooks (daily digest, weekly PDF, alerts, targets)
- [ ] Engagement tracking
- [ ] Competitive landscape map
- [ ] GTM: WhatsApp, conferences, LinkedIn, free tier, distributors
- [ ] Roadmap re-prioritized by revenue impact
- [ ] MLP for paid launch
- [ ] Unit economics (cost per tenant at 10/100/1000)

### Verify and Fix (read code first — skip if already implemented)

| Verify | If Missing, Implement | Where to Look |
|--------|----------------------|---------------|
| H6: i18n library installed? | Set up next-intl | `frontend/package.json` |
| Translation files exist? | Create ar.json + en.json | `frontend/messages/` or `frontend/locales/` |
| Locale switcher in UI? | Add to sidebar | `frontend/src/components/layout/sidebar.tsx` |
| RTL layout support? | Add dir="rtl" + CSS | `frontend/src/app/layout.tsx`, `globals.css` |
| Dates use Egyptian locale? | Update date formatting | `frontend/src/lib/date-utils.ts` |
| Landing page compelling? | Improve value proposition | `frontend/src/components/marketing/hero-section.tsx` |
| SEO structured data? | Add JSON-LD | `frontend/src/components/marketing/json-ld.tsx` |

### Creative Improvements

1. Arabic-first default with English toggle
2. Animated landing: Upload -> Clean -> Analyze -> Insight
3. Interactive demo on landing (read-only dashboard, sample data)
4. WhatsApp bot: `/daily` summary, `/alert low-stock`
5. "Before vs After DataPulse" split-screen
6. Pharmacy templates: "Sales Team", "Branch Comparison", "Seasonal"
7. Referral program
8. ROI calculator on landing
9. Success stories section

### Business Deliverables (No Code)

- [ ] One-sentence pitch
- [ ] 3-tier pricing model (EGP)
- [ ] 5-channel GTM strategy
- [ ] MLP feature list
- [ ] User journey click audit
- [ ] Retention hooks plan
- [ ] Competitive landscape map
- [ ] Unit economics estimate

### Tools: next-intl, PostHog, Novu, Resend, Cal.com

---

## Session 8: DR, Multi-Tenancy and DX

**Priority**: LOWER | **Covers**: Phases 12 + 13 + 15 | **~3 hours**

### Scope

```
docker-compose*.yml (volumes), PostgreSQL backup
All tenant-related code, RLS policies
README.md, CLAUDE.md, CONTRIBUTING.md, docs/
Makefile, scripts/, .claude/ (agents)
Code comments, error messages quality
```

### Audit Checklist

#### DR (Phase 12)
- [ ] Automated backup (pg_dump, WAL, cloud)?
- [ ] Frequency, storage location, tested restore
- [ ] PITR capability
- [ ] Tenant data recovery (accidental delete)
- [ ] Soft vs hard delete
- [ ] Pipeline rollback
- [ ] RTO/RPO defined
- [ ] IaC (Docker Compose = partial)
- [ ] Privacy policy compliance (Egyptian PDPL)
- [ ] Data encrypted at rest/transit
- [ ] Per-tenant backup/restore

#### Multi-Tenancy (Phase 13)
- [ ] **FIX H7**: tenant_id at EVERY layer
- [ ] Shared resources isolation (Redis keys, uploads)
- [ ] Per-tenant rate limits
- [ ] Celery tenant-aware
- [ ] n8n tenant-scoped
- [ ] Tenant onboarding (manual vs self-serve)
- [ ] Provisioning script/API (<1 min)
- [ ] Tenant config (logo, colors, language)
- [ ] Feature flags per plan
- [ ] Resource limits (rows, storage, AI)
- [ ] Usage tracking (API calls, rows, AI)
- [ ] Billing readiness (Stripe/Paymob)
- [ ] Admin panel (tenant list, impersonate, suspend)

#### DX (Phase 15)
- [ ] README: zero to working <10 min
- [ ] Prerequisites listed
- [ ] Seed data scripts
- [ ] CLAUDE.md matches codebase
- [ ] ADRs documented
- [ ] API auto-documented (OpenAPI)
- [ ] dbt lineage graph
- [ ] n8n workflows documented
- [ ] Complex functions have docstrings
- [ ] Error messages: WHAT, WHERE, HOW to fix
- [ ] Makefile targets complete
- [ ] Pre-commit hooks
- [ ] PR template
- [ ] Bus factor matrix
- [ ] Incident runbook
- [ ] Break Glass document

### Verify and Fix (read code first — skip if already implemented)

| Verify | If Missing, Implement | Where to Look |
|--------|----------------------|---------------|
| H7: Tenant RLS policies exist? | Add tenant-scoped USING clauses | `migrations/` — check all RLS policies |
| DR runbook exists? | Create step-by-step procedures | `docs/ops/disaster-recovery.md` |
| M12: Architecture docs current? | Update or create | `docs/ARCHITECTURE.md` |
| Tenant provisioning API? | Add self-serve endpoint | `src/datapulse/api/routes/` |
| Per-tenant rate limiting? | Implement tier-based limits | `src/datapulse/api/limiter.py` |
| Onboarding guide for devs? | Add "zero to working" guide | `README.md` |
| ADRs documented? | Create key decision records | `docs/adr/` |
| Incident runbook? | Create common incident procedures | `docs/runbook.md` |

### Creative Improvements

1. "Download all my data" button
2. Backup status in admin panel
3. Tenant health dashboard (traffic light)
4. Usage-based upsell ("80% quota -> upgrade")
5. White-label option
6. Team management (invite, roles)
7. Onboarding checklist gamification
8. Interactive architecture diagram
9. Video walkthroughs (Loom)
10. Architecture fitness functions (automated rules)
11. Incident journal
12. Dependency graph visualization

### Tests to Write

```
test_2_tenants -> complete_isolation
test_tenant_A -> zero_from_B
test_new_tenant -> provisioned_30s
test_usage_quota -> error_upgrade_prompt
test_suspend_tenant -> all_403
test_delete_tenant -> all_removed
test_db_restore -> data_integrity
test_rls_bypass -> blocked
test_pipeline_rollback -> gold_reverts
test_git_clone_compose_up -> health_passes
test_makefile_targets -> no_errors
test_architecture_no_route_imports_repo
test_all_dbt_have_schema
test_all_endpoints_have_auth
test_error_messages_actionable
```

### Tools: Paymob, Stripe, LaunchDarkly, Docusaurus, Linear, ArchUnit, Crisp, Loops, Hotjar, Loom

---

## Full Tools Matrix

### CRITICAL (Add Now)

| Tool | Purpose |
|------|---------|
| Sentry | Error tracking (mandatory) |
| Renovate / Dependabot | Auto dependency updates |
| Trivy | Docker image vulnerability scan |
| Presidio | PII detection and anonymization |
| Grafana + Prometheus | Infrastructure monitoring |
| pgBackRest | PostgreSQL backup and PITR |

### HIGH (Add Soon)

| Tool | Purpose |
|------|---------|
| axe-core | Accessibility testing |
| Lighthouse CI | Performance budgets |
| k6 / Locust | Load testing |
| Storybook + Chromatic | Component library + visual regression |
| Great Expectations | Data validation |
| PostHog / Mixpanel | Product analytics |
| next-intl | i18n framework |
| react-pdf | PDF generation |
| Loki | Log aggregation |
| Better Uptime | External monitoring |
| LaunchDarkly | Feature flags |
| Paymob / Fawry | Egyptian payments |
| Vault | Secrets management |
| CookieYes | Privacy compliance |

### MEDIUM (Future)

| Tool | Purpose |
|------|---------|
| Pact | Contract testing |
| mutmut | Mutation testing |
| OpenTelemetry | Distributed tracing |
| Novu | Notifications |
| Crisp / Intercom | In-app chat |
| Hotjar | Heatmaps |

---

## Session Execution Order

```
Session 1: Security Hardening          [CRITICAL] ██████████ ~3-4h  (Phases 2+14)
Session 2: Data Pipeline Resilience    [HIGH]     ████████   ~2-3h  (Phase 3)
Session 3: Infrastructure & CI/CD      [HIGH]     ████████   ~2-3h  (Phases 1+11)
Session 4: Backend API Quality         [MEDIUM+]  ████████   ~3h    (Phases 4+7)
Session 5: Frontend UX & Accessibility [MEDIUM+]  ████████   ~3h    (Phase 5)
Session 6: Testing & Coverage          [MEDIUM]   ██████     ~2-3h  (Phase 6)
Session 7: i18n, Landing & Growth      [MEDIUM]   ████████   ~3h    (Phases 9+10)
Session 8: DR, Multi-Tenancy & DX      [LOWER]    ████████   ~3h    (Phases 12+13+15)
```

**Total: 8 sessions, ~22-28 hours**

---

## How to Start Each Session

**IMPORTANT**: This plan was created from a point-in-time scan. Some findings may already be fixed. Always verify before fixing.

### Approach per Session
1. Read the session's **Scope** files in the current codebase
2. Work through the **Audit Checklist** item by item — these are the primary work
3. For each item in **Verify and Fix** table:
   - Read the current code at the location specified
   - If the issue is ALREADY FIXED: mark as "VERIFIED OK" and move on
   - If the issue STILL EXISTS: fix it and write a test
   - If you find NEW issues not in the table: report and fix them too
4. Group changes into atomic commits
5. Run `make test` after each group
6. Attempt creative improvements from the list where feasible
7. Report findings in table format
