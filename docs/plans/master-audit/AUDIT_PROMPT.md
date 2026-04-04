# DataPulse — Master Audit & Improvement Prompt for Claude Code

> **How to use**: Copy this entire file as a prompt to Claude Code (or paste into CLAUDE.md).
> Run phase by phase — each phase is self-contained. After each phase, review the output before moving to the next.

---

## 🎯 Your Role

You are a **Senior Staff Engineer + UX Consultant + SaaS CEO Advisor** conducting a comprehensive audit of **DataPulse** — a pharmaceutical sales analytics SaaS platform built with FastAPI, Next.js 14, PostgreSQL, dbt, and Docker. You think at 3 levels simultaneously: **(1) Is the code solid?** (engineering), **(2) Will users love it?** (UX/product), **(3) Will this make money?** (business).

**Your job across ALL phases:**

1. **Read every file** in the scope of each phase before making any judgment
2. **Find bugs, security holes, performance issues, and dead code**
3. **Suggest creative UX improvements** for non-technical pharmacy managers
4. **Propose visual/design upgrades** that make the product feel premium
5. **Write or fix tests** that cover every code path — with clear error messages
6. **Refactor for maintainability** — make future changes easy and safe
7. **Recommend tools** that would improve DX, quality, or user experience

**Rules:**
- Never skip reading files — always `cat` or `read` before suggesting changes
- Every fix must have a corresponding test
- Every UX suggestion must explain WHY it helps a non-technical user
- Group changes into atomic commits with clear messages
- If you find something that works fine — say so and move on

---

## Phase 1: 🏗️ Architecture & Infrastructure Audit

### Scope
```
docker-compose*.yml
nginx/
.github/workflows/
.env.example
alembic/ (migrations)
scripts/
Makefile / pyproject.toml / package.json
```

### Checklist

#### 1.1 Docker Compose Health
- [ ] Read ALL docker-compose files (dev, prod, test)
- [ ] Check every service has: health checks, restart policies, memory limits, proper depends_on
- [ ] Verify no secrets are hardcoded (scan for passwords, API keys, tokens in compose files)
- [ ] Check volume mounts — are data volumes persistent? Named volumes vs bind mounts?
- [ ] Verify network isolation — services that don't need to talk shouldn't be on the same network
- [ ] Check image pinning — are all images using specific tags (not `latest`)?

#### 1.2 Nginx Configuration
- [ ] Read nginx config files
- [ ] Check: SSL/TLS settings, rate limiting, CORS headers, security headers (HSTS, CSP, X-Frame-Options)
- [ ] Check: gzip compression, static asset caching, proxy_pass timeouts
- [ ] Verify WebSocket support for SSE endpoints (`/runs/{id}/stream`)
- [ ] Check: Is there a proper 502/503 error page?

#### 1.3 CI/CD Pipeline
- [ ] Read all GitHub Actions workflows
- [ ] Check: Are E2E tests actually running? (Known issue: disabled)
- [ ] Check: Is mypy enforced or `continue-on-error`? (Known issue: not enforced)
- [ ] Check: Frontend unit tests — are they running in CI?
- [ ] Check: Docker build caching — is it optimized?
- [ ] Check: Are there deployment stages (staging → production)?
- [ ] Suggest: Add dependency vulnerability scanning (Dependabot, Snyk, or Trivy)

#### 1.4 Database Migrations
- [ ] Read all Alembic migration files
- [ ] Check: Are migrations reversible (downgrade function)?
- [ ] Check: Are there any migration gaps or conflicts?
- [ ] Check: Is there a migration for RLS policies?
- [ ] Verify: Migration ordering and dependencies

#### 1.5 Environment & Configuration
- [ ] Read `.env.example` — are all variables documented?
- [ ] Check: Are there separate configs for dev/staging/prod?
- [ ] Check: Pydantic Settings — are defaults safe? Are secrets loaded from env only?

### 💡 Creative Improvements for This Phase
- **One-command setup**: Can `docker compose up` get a new developer from zero to working in <2 minutes? If not, create a `make setup` that handles everything
- **Health dashboard**: Add a `/status` page that shows all service health (DB, Redis, Celery, n8n) in one view — non-technical users can see "everything green" or "X is down"
- **Auto-recovery**: If a service dies, does Docker restart it? Add proper restart policies and health check intervals

### 🧪 Tests for This Phase
- Write a smoke test that boots all Docker services and verifies health endpoints
- Write a test that validates all env vars are set before app starts (fail fast, clear message)
- Write a migration test that runs upgrade → downgrade → upgrade cycle

---

## Phase 2: 🔐 Security Audit

### Scope
```
backend/auth/
backend/jwt.py
frontend/src/app/api/auth/
middleware files (backend + frontend)
All API route files (check auth decorators)
docker-compose*.yml (secrets)
nginx/ (headers)
```

### Checklist

#### 2.1 Authentication
- [ ] Read all auth-related files (jwt.py, auth.py, NextAuth config)
- [ ] Check: JWT validation — is audience/issuer verified? Is token expiry checked?
- [ ] Check: Are there any endpoints WITHOUT auth that should have it?
- [ ] Check: API key auth — how are keys stored? Hashed? Rotatable?
- [ ] Check: Is there rate limiting on login/auth endpoints?
- [ ] Check: Session management — timeout, refresh, revocation

#### 2.2 Authorization (RLS)
- [ ] Read all PostgreSQL RLS policies
- [ ] Check: Is `tenant_id` enforced on EVERY query? Any bypass?
- [ ] Check: Can a user access another tenant's data via any endpoint?
- [ ] Check: Admin endpoints — are they properly gated?
- [ ] Test: Write a specific test that tries cross-tenant data access

#### 2.3 Input Validation
- [ ] Check every Pydantic model — are fields validated (min/max length, regex, enums)?
- [ ] Check: SQL injection — are all queries parameterized? Any raw f-strings?
- [ ] Check: File upload — is file type/size validated? Can someone upload a malicious file?
- [ ] Check: SQL Lab — is there query sandboxing? Can users DROP tables?
- [ ] Check: Export endpoints — are they protected against path traversal?

#### 2.4 Secrets & Exposure
- [ ] Scan entire codebase for hardcoded secrets (grep for patterns)
- [ ] Check: Are error responses leaking internal details (stack traces, DB info)?
- [ ] Check: Are API docs (Swagger/ReDoc) exposed in production?
- [ ] Check: Are debug endpoints or dev tools accessible in prod mode?

#### 2.5 Frontend Security
- [ ] Check: XSS protection — is user-generated content sanitized before rendering?
- [ ] Check: CSRF protection — are state-changing requests protected?
- [ ] Check: Is the Auth0 client secret exposed to the browser?
- [ ] Check: Are API keys stored in localStorage? (should use httpOnly cookies)

### 💡 Creative Improvements
- **Security score dashboard**: Show tenant admins a security health score (like GitHub security tab)
- **Audit log**: Log who accessed what data and when — important for pharma compliance
- **Session management UI**: Let users see active sessions and revoke them
- **2FA support**: Add TOTP option for admin accounts

### 🧪 Tests for This Phase
- Test: Unauthenticated request to every protected endpoint → 401
- Test: Cross-tenant access attempt → 403
- Test: SQL injection attempts on SQL Lab → blocked
- Test: Malicious file upload → rejected with clear error
- Test: Expired JWT → 401 with "token expired" message
- Test: Rate limit exceeded → 429 with retry-after header

---

## Phase 3: 🗄️ Database & Data Pipeline Audit

### Scope
```
backend/bronze/
backend/pipeline/
dbt/ (all models, schemas, tests)
alembic/versions/
backend/analytics/ (repository layer)
SQL queries in all services
```

### Checklist

#### 3.1 Bronze Layer (Ingestion)
- [ ] Read `bronze/loader.py` completely
- [ ] Check: Error handling — what happens if Excel file is malformed?
- [ ] Check: Memory usage — is 2.27M rows loaded at once or in chunks?
- [ ] Check: Duplicate detection — how are re-uploads handled?
- [ ] Check: Data types — are dates, currencies, nulls handled correctly?
- [ ] Check: Is there a rollback mechanism if ingestion fails midway?

#### 3.2 dbt Models (Silver → Gold)
- [ ] Read ALL dbt models (staging, marts, aggregations)
- [ ] Check: `stg_sales.sql` — is deduplication logic correct? Edge cases?
- [ ] Check: Dimension tables — are surrogate keys generated consistently?
- [ ] Check: Fact table joins — are COALESCE(-1) defaults correct?
- [ ] Check: Aggregation models — are they incremental or full refresh?
- [ ] Check: dbt tests — are there tests for: uniqueness, not_null, referential integrity, accepted_values?
- [ ] Run `dbt test` and report any failures

#### 3.3 Query Performance
- [ ] Read analytics repository SQL queries
- [ ] Check: Are there proper indexes on frequently filtered columns (date, tenant_id, product_key)?
- [ ] Check: Are complex queries using CTEs vs subqueries efficiently?
- [ ] Check: Is there query caching (Redis)? What's the TTL strategy?
- [ ] Check: Are there any N+1 query patterns?
- [ ] Suggest: EXPLAIN ANALYZE on the top 5 most-used queries

#### 3.4 Data Quality
- [ ] Check: Quality gates in pipeline — what do they check?
- [ ] Check: What happens when data quality fails? Does pipeline stop? Notify?
- [ ] Check: Are there data freshness checks?
- [ ] Suggest: Add Great Expectations or dbt-expectations for advanced data validation

### 💡 Creative Improvements
- **Upload wizard**: Instead of "upload Excel", guide the user step-by-step:
  1. "Select your file" → preview first 5 rows
  2. "Confirm column mapping" → auto-detect with manual override
  3. "Review data quality" → show issues before ingestion
  4. "Processing..." → real-time progress bar with SSE
  5. "Done! View dashboard" → direct link
- **Data quality score**: Show a "data health" percentage on the dashboard — "Your data is 94% clean, 3 issues found"
- **Smart duplicate detection**: When re-uploading, show a diff: "243 new rows, 12 updated, 0 duplicates"
- **Pipeline timeline**: Visual timeline showing Bronze → Silver → Gold with duration and row counts per stage

### 🧪 Tests for This Phase
- Test: Upload valid Excel → all stages complete successfully
- Test: Upload Excel with missing columns → clear error message listing missing columns
- Test: Upload Excel with bad dates/nulls → quality gate catches them
- Test: Upload duplicate file → handled gracefully (no duplicate rows)
- Test: Pipeline fails at Silver stage → Bronze data preserved, clear error
- Test: dbt model output matches expected row counts
- Test: Aggregation totals match fact table totals (reconciliation test)
- Test: Query with 1M+ rows returns in <2 seconds

---

## Phase 4: 🚀 Backend API Audit

### Scope
```
backend/api/ (all 13 route files, 84 endpoints)
backend/analytics/
backend/forecasting/
backend/ai_light/
backend/explore/
backend/targets/
backend/reports/
backend/export/
backend/embed/
backend/sql_lab/
```

### Checklist

#### 4.1 API Design & Consistency
- [ ] Read ALL 13 route files
- [ ] Check: Consistent error response format across all endpoints
- [ ] Check: Proper HTTP status codes (200 vs 201 vs 204, 400 vs 422)
- [ ] Check: Are query parameters validated (dates, pagination, limits)?
- [ ] Check: Is pagination implemented consistently? (offset/limit or cursor?)
- [ ] Check: Are response schemas documented (Pydantic response models)?
- [ ] Check: API versioning — is `/api/v1/` used consistently?

#### 4.2 Error Handling
- [ ] Check: Are all service calls wrapped in try/except?
- [ ] Check: Do errors return useful messages? ("Product not found" vs "Internal Server Error")
- [ ] Check: Are database errors caught and translated to user-friendly messages?
- [ ] Check: Are external service failures (OpenRouter, n8n) handled gracefully?
- [ ] Check: Is there a global exception handler?

#### 4.3 Performance
- [ ] Check: Which endpoints are slow? Are complex queries cached?
- [ ] Check: Is Redis caching implemented correctly? (invalidation strategy?)
- [ ] Check: Are there any synchronous blocking calls that should be async?
- [ ] Check: Rate limiting — is it per-user or per-IP? Are limits reasonable?
- [ ] Check: Are large responses (export) streamed or loaded in memory?

#### 4.4 Forecasting Module
- [ ] Read forecasting service and models
- [ ] Check: Are Holt-Winters parameters tuned or using defaults?
- [ ] Check: Error handling for insufficient data (< 12 months)
- [ ] Check: Is forecast accuracy measured? (MAPE, MAE)
- [ ] Suggest: Add Prophet or LightGBM as alternative models

#### 4.5 AI Insights Module
- [ ] Read ai_light service
- [ ] Check: Prompt engineering — are prompts structured well?
- [ ] Check: Token usage — is there a cost limit per tenant?
- [ ] Check: Fallback — what if OpenRouter is down?
- [ ] Check: Is AI output validated before showing to users?

### 💡 Creative Improvements
- **API playground**: Add an interactive API explorer in the dashboard (like Swagger UI but prettier) — let power users test queries
- **Smart caching indicators**: Show users "Data updated 5 min ago" with a refresh button
- **Forecast confidence bands**: Show high/medium/low forecast with visual confidence bands on charts
- **AI chat interface**: Instead of just "AI insights" panel, add a conversational interface: "Ask DataPulse: Why did sales drop in March?"
- **Webhook notifications**: Let users configure webhooks for alerts (inventory low, sales target missed) — integrates with their existing tools

### 🧪 Tests for This Phase
- Test: Every endpoint returns correct status codes for: success, bad input, not found, unauthorized
- Test: Pagination with: page 1, last page, out of range page, zero limit
- Test: Date range filters: valid range, reversed dates, future dates, very old dates
- Test: Export endpoints: CSV format correct, Excel opens correctly, large dataset export
- Test: Forecasting: with 36 months data, with 6 months data, with 1 month data
- Test: AI insights: with valid data, with empty data, with OpenRouter timeout
- Test: SQL Lab: SELECT allowed, DROP blocked, timeout after 30s
- Test: Rate limiting: verify 429 returned after limit exceeded
- Test: Concurrent requests: 50 parallel requests to /dashboard → no 500 errors

---

## Phase 5: 🎨 Frontend Audit — UX, Design, & Accessibility

### Scope
```
frontend/src/app/ (26 pages)
frontend/src/components/ (87 components)
frontend/src/hooks/ (40 SWR hooks)
frontend/src/contexts/
frontend/src/lib/
frontend/tailwind.config.ts
frontend/src/app/globals.css
```

### Checklist

#### 5.1 Component Quality
- [ ] Read ALL 87 components — check for:
  - Loading states (skeleton, spinner, or progressive loading?)
  - Error states (user-friendly message + retry button?)
  - Empty states (helpful guidance, not just "No data")
  - Responsive design (mobile, tablet, desktop)
- [ ] Check: Are there any components over 300 lines that should be split?
- [ ] Check: Is there consistent prop typing (TypeScript interfaces)?
- [ ] Check: Are there any unused components or imports?

#### 5.2 UX for Non-Technical Users
This is CRITICAL — the target users are Egyptian pharma sales managers, not developers.

- [ ] Check: Is the navigation intuitive? Can a new user find the dashboard in <3 clicks?
- [ ] Check: Are charts labeled clearly? (Arabic + English labels?)
- [ ] Check: Are numbers formatted correctly? (EGP currency, Arabic numerals option?)
- [ ] Check: Are there tooltips/help text explaining what each metric means?
- [ ] Check: Is there an onboarding flow for first-time users?
- [ ] Check: Are error messages in plain language? ("Your file couldn't be processed" vs "Error 422")
- [ ] Check: Is the upload flow guided or just a file input?

#### 5.3 Visual Design
- [ ] Check: Color consistency — are theme tokens used everywhere?
- [ ] Check: Typography — is the font hierarchy clear (headings, body, captions)?
- [ ] Check: Spacing — is it consistent (8px grid)?
- [ ] Check: Dark mode — does it work on ALL pages? Any contrast issues?
- [ ] Check: Charts — are colors accessible (colorblind-friendly palette)?
- [ ] Check: Is the landing page compelling? Does it communicate value quickly?

#### 5.4 Performance
- [ ] Check: Bundle size — run `next build` and check output
- [ ] Check: Are images optimized (next/image)?
- [ ] Check: Is there code splitting / lazy loading for heavy components?
- [ ] Check: Are SWR hooks configured with proper revalidation intervals?
- [ ] Check: Is there layout shift (CLS) on dashboard load?

#### 5.5 Accessibility (a11y)
- [ ] Check: Keyboard navigation — can you use the entire app with keyboard?
- [ ] Check: Screen reader compatibility — are ARIA labels present?
- [ ] Check: Color contrast — do all text/bg combinations meet WCAG AA?
- [ ] Check: Focus indicators — are they visible?
- [ ] Check: RTL support — since users may switch to Arabic

### 💡 Creative Improvements — UX Gems 💎

**For non-technical pharmacy managers:**

1. **Welcome dashboard with KPI cards**: First thing they see — 4 big numbers: Total Revenue, Units Sold, Top Product, Growth % — with sparkline trends. No chart overload.

2. **"What happened today?" summary**: AI-generated plain-language summary at the top: "Sales were up 12% yesterday, driven by Augmentin 1g. Three products are running low."

3. **Guided upload experience**: Replace the file upload with a step-by-step wizard:
   - Step 1: Drag & drop with "Supported: .xlsx, .csv" label
   - Step 2: Preview with auto-detected columns highlighted
   - Step 3: "Processing..." with animated pipeline visualization
   - Step 4: "Success! 1,200 new sales records added" with a "View Dashboard" CTA

4. **Contextual help bubbles**: On every chart/metric, a small `?` icon that explains in simple language what the metric means and why it matters

5. **Quick actions bar**: Floating action button (FAB) with: "Upload Data", "Export Report", "Ask AI", "Set Alert"

6. **Smart date range picker**: Pre-built ranges: "Today", "This Week", "This Month", "Last Quarter", "Ramadan 2025", "Summer 2025" — relevant to Egyptian pharma cycles

7. **Mobile-first alerts**: Push notification style alerts on mobile: "Panadol Extra stock below 50 units at Cairo branch"

8. **Celebration moments**: When targets are hit, show a subtle confetti animation + "🎯 Target achieved!" — gamification for sales teams

9. **Comparison mode**: Side-by-side: "This Month vs Last Month", "Branch A vs Branch B" — one click toggle

10. **Export as PDF report**: One-click "Generate Monthly Report" — auto-formatted PDF with company logo, charts, and AI summary

### 🧪 Tests for This Phase
- E2E: Dashboard loads in <3 seconds with full data
- E2E: Upload flow — complete upload → see data in dashboard
- E2E: Date filter → charts update correctly
- E2E: Dark mode toggle → no visual glitches
- E2E: Mobile viewport → all pages usable
- E2E: Navigation — visit every page, no 404s or blank screens
- Visual regression: Screenshot comparison for key pages
- Accessibility: Run axe-core automated scan on all pages
- Unit: Every SWR hook returns correct data shape
- Unit: Filter context updates URL params correctly

---

## Phase 6: 🧪 Testing & Quality Assurance Deep Dive

### Scope
```
tests/ (80 test files, 1,179 tests)
frontend/e2e/ (11 Playwright specs)
conftest.py files
pytest configuration
CI test jobs
```

### Checklist

#### 6.1 Backend Test Coverage
- [ ] Run `pytest --cov` and generate coverage report
- [ ] Identify modules with <90% coverage
- [ ] Check: Are edge cases tested (empty data, huge data, malformed input)?
- [ ] Check: Are error paths tested (not just happy paths)?
- [ ] Check: Are fixtures realistic (not trivial 1-row test data)?
- [ ] Check: Are database tests using transactions with rollback?

#### 6.2 Frontend Test Gap
- [ ] Check: Are there ANY frontend unit tests? (Known gap: vitest config exists but no test files)
- [ ] If missing, CREATE tests for:
  - Critical components (Dashboard, Upload, Charts)
  - SWR hooks (data fetching, error handling, loading states)
  - Filter context (state management)
  - Utility functions (formatters, validators)

#### 6.3 E2E Tests
- [ ] Read all 11 Playwright specs
- [ ] Check: Are E2E tests enabled in CI? (Known issue: disabled)
- [ ] Check: Do E2E tests cover the critical user journeys:
  - Sign up → upload data → view dashboard → export report
  - Create target → receive alert
  - Use SQL Lab → run query → export results
- [ ] Check: Are E2E tests flaky? Do they have proper waits and selectors?
- [ ] Enable E2E in CI with proper setup (DB seed, auth mock)

#### 6.4 Test Infrastructure
- [ ] Check: Test database setup — is it isolated from dev?
- [ ] Check: Are fixtures auto-cleaned after each test?
- [ ] Check: Is there a test data factory (Factory Boy or similar)?
- [ ] Check: Can tests run in parallel safely?

### 💡 Creative Improvements
- **Test dashboard**: Add a CI badge on README + detailed test report link
- **Mutation testing**: Add `mutmut` to find tests that pass even when code is broken
- **Contract testing**: Add Pact for API contract between frontend and backend
- **Performance tests**: Add k6 or Locust load tests for key endpoints
- **Chaos testing**: Randomly kill a service during E2E — does the app recover gracefully?

### 🧪 Tests to ADD in This Phase
```
# Backend tests to add:
tests/test_cross_tenant_isolation.py    # Security: verify tenant data isolation
tests/test_pipeline_failure_recovery.py # Resilience: pipeline fails midway
tests/test_concurrent_uploads.py        # Race condition: 2 users upload simultaneously
tests/test_large_dataset_performance.py # Performance: 5M rows query under 5s
tests/test_api_rate_limiting.py         # Security: rate limits enforced
tests/test_export_large_file.py         # Memory: export 1M rows without OOM
tests/test_forecasting_edge_cases.py    # ML: insufficient data, seasonal data, outliers
tests/test_ai_insights_fallback.py      # Resilience: OpenRouter timeout/down

# Frontend tests to add:
frontend/src/__tests__/hooks/           # Unit: all 40 SWR hooks
frontend/src/__tests__/components/      # Unit: critical components
frontend/src/__tests__/utils/           # Unit: formatters, validators
frontend/e2e/full-journey.spec.ts       # E2E: complete user journey
frontend/e2e/upload-wizard.spec.ts      # E2E: upload flow happy + error paths
frontend/e2e/mobile.spec.ts            # E2E: mobile-specific tests
```

---

## Phase 7: 📊 Forecasting, AI & Analytics Deep Dive

### Scope
```
backend/forecasting/
backend/ai_light/
backend/analytics/
backend/explore/
backend/sql_lab/
backend/targets/
backend/reports/
```

### Checklist

#### 7.1 Forecasting Accuracy
- [ ] Read all forecasting models (Holt-Winters, SMA, Seasonal Naive)
- [ ] Check: Is there backtesting / cross-validation?
- [ ] Check: Is MAPE/MAE calculated and shown to users?
- [ ] Check: Does the system auto-select the best model?
- [ ] Check: How are outliers handled (Ramadan spikes, COVID dips)?
- [ ] Suggest: Add Prophet, ARIMA, or LightGBM as alternatives
- [ ] Suggest: Ensemble method (average of top 3 models)

#### 7.2 AI Insights Quality
- [ ] Read prompt templates
- [ ] Check: Are prompts structured with: context, data, specific question, output format?
- [ ] Check: Is there prompt injection protection?
- [ ] Check: Are AI responses cached to avoid duplicate API calls?
- [ ] Check: Is there a feedback loop (user rates AI insights)?
- [ ] Suggest: Fine-tune prompts for pharmacy-specific language

#### 7.3 Explore & SQL Lab Safety
- [ ] Check: SQL injection in SQL Lab — is there a query parser/sanitizer?
- [ ] Check: Are dangerous operations blocked (DROP, DELETE, UPDATE, TRUNCATE)?
- [ ] Check: Is there a query timeout?
- [ ] Check: Is there query cost estimation before execution?
- [ ] Check: Can users only access their own tenant's data?

### 💡 Creative Improvements
- **Forecast explainer**: Show WHY the forecast predicts what it does: "Sales expected to increase 15% because Ramadan starts in 2 weeks — historically, painkiller sales spike 20% during Ramadan"
- **What-if scenarios**: "What if we increase Augmentin stock by 30%? What if we add a new branch?"
- **Anomaly alerts**: Auto-detect unusual patterns and flag them: "⚠️ Cataflam sales dropped 40% this week — investigate?"
- **Natural language queries**: "Show me top 5 products in Cairo last month" → auto-generated SQL
- **Saved insights library**: Let users save and share interesting findings with their team

---

## Phase 8: 📦 Dependency, Performance & Maintenance Audit

### Scope
```
pyproject.toml / requirements*.txt
package.json / package-lock.json
All import statements
Docker images
```

### Checklist

#### 8.1 Dependency Health
- [ ] Check: Are there any known vulnerabilities? Run `pip-audit` and `npm audit`
- [ ] Check: Are dependencies pinned to specific versions?
- [ ] Check: Are there unused dependencies? Run `deptry` (Python) and `depcheck` (Node)
- [ ] Check: Are there any license conflicts (GPL in a SaaS product)?
- [ ] Check: How old are the dependencies? Any EOL versions?

#### 8.2 Code Maintainability
- [ ] Check: Is there a consistent code style? (ruff for Python, eslint/prettier for TS)
- [ ] Check: Are there any circular imports?
- [ ] Check: Is the codebase modular enough to replace a service independently?
- [ ] Check: Is there dead code? (unreachable functions, unused variables)
- [ ] Check: Are there TODO/FIXME/HACK comments that need attention?
- [ ] Check: Is documentation up-to-date? (CLAUDE.md, API docs, README)

#### 8.3 Performance Benchmarks
- [ ] Measure: API cold start time
- [ ] Measure: Dashboard full load time (LCP, FID, CLS)
- [ ] Measure: Time to process 100K rows in Bronze pipeline
- [ ] Measure: Time for dbt full refresh
- [ ] Measure: Memory usage per service under load
- [ ] Set baselines and add to CI as performance budgets

### 💡 Creative Improvements
- **Dependency bot**: Set up Renovate or Dependabot with auto-merge for patch updates
- **Performance budget**: Fail CI if bundle size exceeds 500KB or API response >2s
- **Developer docs**: Add ADR (Architecture Decision Records) for key decisions
- **Changelog automation**: Auto-generate changelog from conventional commits

---

## Phase 9: 🌍 Internationalization, Landing & Growth

### Scope
```
frontend/src/app/(marketing)/
frontend/public/
All UI strings and labels
SEO metadata
```

### Checklist

#### 9.1 Landing Page
- [ ] Check: Does it clearly explain what DataPulse does in 5 seconds?
- [ ] Check: Is there social proof (testimonials, logos, numbers)?
- [ ] Check: Is there a clear CTA (Call to Action)?
- [ ] Check: SEO — meta tags, OG images, structured data?
- [ ] Check: Performance — Lighthouse score?

#### 9.2 Internationalization (i18n)
- [ ] Check: Are UI strings hardcoded or in translation files?
- [ ] Check: Is RTL layout supported for Arabic?
- [ ] Check: Are dates formatted for Egyptian locale?
- [ ] Check: Are currency values formatted as EGP correctly?
- [ ] Suggest: Add `next-intl` or `react-i18next` for proper i18n

#### 9.3 Bilingual Support
- [ ] Check: Can users switch between Arabic and English?
- [ ] Check: Are chart labels available in both languages?
- [ ] Check: Are PDF exports available in Arabic?
- [ ] Check: Is the AI insights output language configurable?

### 💡 Creative Improvements
- **Arabic-first option**: Since target users are Egyptian, offer Arabic as default with English toggle
- **Animated landing page**: Show the DataPulse workflow: Upload → Clean → Analyze → Insight — with a slick animation
- **Interactive demo**: Embed a read-only dashboard on the landing page with sample data — "Try it now, no signup"
- **Testimonial videos**: Add video testimonials from Egyptian pharma managers (placeholder for now)
- **WhatsApp integration**: Egyptian businesses live on WhatsApp — add "Share report via WhatsApp" button

---

## Phase 10: 👔 CEO & Business Strategy Audit

### Mindset
This phase is NOT about code. You are now a **fractional CTO + Product Strategist** advising the CEO. You're evaluating DataPulse as a **business**, not a codebase.

### Scope
```
Everything — but from a business lens:
- Landing page (marketing/)
- Pricing signals in code
- Feature completeness vs market need
- User journey (signup → value → retention)
- Competitive positioning
- Roadmap alignment
```

### Checklist

#### 10.1 Value Proposition & Positioning
- [ ] Open the landing page — does it answer in 5 seconds: "What is this? Who is it for? Why should I care?"
- [ ] Is the value proposition specific to Egyptian pharma? Or generic "analytics platform"?
- [ ] Can you articulate the **one sentence pitch**? If not, draft one: "DataPulse turns your messy pharma Excel files into executive-ready dashboards in 10 minutes"
- [ ] Check: Is there a **competitive moat**? What stops someone from using Excel + Power BI?
- [ ] Answer: Why would a pharma sales manager pay for this vs hiring an analyst?

#### 10.2 Pricing & Monetization
- [ ] Search codebase for pricing-related code, plans, tiers, billing, stripe, payment
- [ ] Is there a pricing page? If not, suggest a pricing model:
  - **Freemium**: Free for 1 user, 1 dataset, basic dashboard. Paid for teams, forecasting, AI
  - **Per-seat**: EGP X/user/month (benchmark against Egyptian SaaS pricing)
  - **Per-upload**: Pay per dataset processed (usage-based)
  - **Tiered**: Starter (1 site) → Pro (multi-site) → Enterprise (custom)
- [ ] Check: Is there Stripe/payment integration? Or is billing Phase 5 (planned)?
- [ ] Suggest: What's the minimum viable pricing to test willingness-to-pay?

#### 10.3 User Journey & Time-to-Value
- [ ] Walk through the ENTIRE user journey as a first-time user:
  1. Land on homepage → What do I see?
  2. Sign up → How many steps? What's required?
  3. First login → What do I see? Empty dashboard?
  4. Upload first file → How easy is it? How long does it take?
  5. See first insight → How quickly do I get an "aha moment"?
- [ ] Measure: How many clicks from signup to first meaningful dashboard?
- [ ] Check: Is there an **empty state** that guides the user? Or just blank pages?
- [ ] Check: Is there **sample data** so users can explore before uploading their own?
- [ ] Suggest: **Time-to-value should be < 5 minutes** — if it's longer, identify blockers

#### 10.4 Retention & Engagement
- [ ] What brings users BACK every day/week? Is there a daily habit loop?
- [ ] Suggest retention hooks:
  - **Daily email digest**: "Yesterday's sales: EGP 450K (+8%). Top product: Augmentin."
  - **Weekly report auto-generated**: PDF in their inbox every Sunday
  - **Alerts**: "Panadol stock is critically low" — creates urgency to check
  - **Targets**: "You're 72% to your monthly target" — gamification
  - **AI insights**: "New trend detected: Vitamin D sales up 40% this week"
- [ ] Check: Is there any user engagement tracking? (PostHog, Mixpanel, or even basic analytics?)
- [ ] Check: Can you identify churn signals? (User hasn't logged in for 7 days → trigger email)

#### 10.5 Competitive Analysis
- [ ] Search codebase and docs for competitor mentions
- [ ] Map the competitive landscape for Egyptian pharma analytics:
  - **Direct**: Any Egyptian pharma analytics SaaS?
  - **Indirect**: Power BI + manual, Excel + macros, ERP built-in analytics
  - **Global**: Veeva, IQVIA, Tableau + pharma connectors
- [ ] Identify DataPulse's **unfair advantage**: Vibe-coded, Arabic-first, pharma-specific, affordable
- [ ] Suggest: What 3 features would make DataPulse a "must-have" vs "nice-to-have"?

#### 10.6 Go-to-Market Strategy
- [ ] Is there a clear target customer profile? (Company size, role, pain point)
- [ ] Suggest GTM for Egyptian pharma market:
  - **Channel 1**: WhatsApp groups (Egyptian pharma managers live there)
  - **Channel 2**: Pharma conferences & exhibitions in Cairo
  - **Channel 3**: LinkedIn content (Arabic + English) showing before/after dashboards
  - **Channel 4**: Free tier / pilot with 3–5 pharma companies → case studies
  - **Channel 5**: Partnership with pharma distributors who already have the data
- [ ] Check: Is there a blog, content marketing, or SEO strategy?
- [ ] Suggest: Create a "DataPulse for Pharmacies" landing page (separate from generic)

#### 10.7 Roadmap Priority Assessment
- [ ] Review the planned phases (5–10) from the codebase
- [ ] Evaluate: Are the planned phases ordered by business impact or technical convenience?
- [ ] Re-prioritize based on **revenue impact**:
  - What feature would make someone PAY tomorrow?
  - What feature would make someone STAY next month?
  - What feature would make someone REFER a colleague?
- [ ] Suggest: What's the **MLP (Minimum Lovable Product)** for paid launch?

#### 10.8 Unit Economics & Scalability
- [ ] Estimate: Cost per tenant (infrastructure: DB, compute, AI API calls, storage)
- [ ] Check: At 10 tenants, is it profitable? At 100? At 1000?
- [ ] Check: What's the most expensive part per tenant? (Likely AI/OpenRouter calls)
- [ ] Suggest: Cost optimization strategies (caching AI responses, tiered AI access)
- [ ] Check: Can the current architecture handle 100 concurrent tenants?

### 💡 Creative Improvements — CEO Vision

1. **"Before DataPulse vs After DataPulse"**: Add a split-screen on the landing page showing a messy Excel on the left, beautiful DataPulse dashboard on the right — this is your sales pitch in one image

2. **Self-serve demo with real Egyptian pharma data**: Anonymized sample dataset pre-loaded — user clicks "Try Demo" and sees a fully working dashboard instantly. No signup required.

3. **WhatsApp bot**: `/daily` sends today's sales summary. `/alert low-stock` sets up stock alerts. Egyptian managers will LOVE this.

4. **Pharmacy-specific templates**: Pre-built dashboards for: "Sales Team Performance", "Product Category Analysis", "Branch Comparison", "Seasonal Trends (Ramadan, Summer, Winter)" — users pick a template instead of building from scratch

5. **Referral program**: "Invite a colleague → both get 1 month free" — word-of-mouth is king in Egyptian pharma

6. **Success stories section**: "Company X reduced stockouts by 30% in 2 months" — even if it's your own pharmacy as case study #1

7. **ROI calculator on landing page**: "How much are you losing to stockouts and expired drugs? Enter your numbers → DataPulse saves you EGP X/month"

### 🧪 "Tests" for This Phase (Business Validation)
- [ ] Can 3 non-technical people complete signup → upload → dashboard in 5 minutes? (Usability test)
- [ ] Does the landing page convert at >3%? (Set up basic conversion tracking)
- [ ] Would 5 pharma managers you know pay EGP 500/month for this? (Customer interviews)
- [ ] Can you explain DataPulse in one WhatsApp message? (If not, simplify the pitch)

---

## Phase 11: 📡 Observability, Monitoring & Alerting Audit

### Scope
```
backend/core/ (logging config)
structlog setup
Sentry integration
Docker health checks
n8n alerting workflows
Redis monitoring
PostgreSQL monitoring
Frontend error boundaries
```

### Checklist

#### 11.1 Logging
- [ ] Read structlog configuration
- [ ] Check: Is logging structured (JSON) in production?
- [ ] Check: Are all API requests logged with: request_id, user_id, tenant_id, duration, status?
- [ ] Check: Are sensitive fields redacted from logs (passwords, tokens, PII)?
- [ ] Check: Are logs rotated? What's the retention policy?
- [ ] Check: Can you trace a single user request across API → Service → DB?
- [ ] Check: Are pipeline runs logged with timing per stage?

#### 11.2 Error Tracking
- [ ] Check: Is Sentry fully configured (not optional)?
- [ ] Check: Are errors grouped correctly (not flooding with duplicates)?
- [ ] Check: Are errors tagged with tenant_id, user_id, environment?
- [ ] Check: Is there a Sentry alert → Slack notification?
- [ ] Check: Frontend — is there a React Error Boundary that catches crashes?
- [ ] Check: Are 5xx errors triggering immediate alerts?

#### 11.3 Health Monitoring
- [ ] Check: Does `/health` check ALL critical services (DB, Redis, Celery, dbt)?
- [ ] Check: Is there an external uptime monitor (UptimeRobot, Better Uptime)?
- [ ] Check: Are Docker health checks working? What happens when one fails?
- [ ] Check: Is there a status page (status.datapulse.com)?
- [ ] Suggest: Add `/health/deep` that checks DB query speed, Redis latency, disk space

#### 11.4 Performance Monitoring
- [ ] Check: Are slow queries logged (>1s)?
- [ ] Check: Are API response times tracked?
- [ ] Check: Is there a performance dashboard (Grafana)?
- [ ] Check: Are memory/CPU usage metrics collected?
- [ ] Suggest: Add PostgreSQL `pg_stat_statements` for query performance tracking

#### 11.5 Business Metrics Monitoring
- [ ] Check: Are these tracked?
  - Active tenants per day
  - Uploads per day
  - Pipeline success/failure rate
  - API error rate (4xx, 5xx)
  - Average dashboard load time
  - AI insights generated per day

### 💡 Creative Improvements
- **Ops dashboard**: Internal admin page showing: uptime, active users right now, pipeline queue, error count today, slowest queries — like a "mission control" for DataPulse
- **Tenant health score**: Green/yellow/red per tenant based on: data freshness, error rate, login frequency
- **Anomaly detection on YOUR OWN metrics**: If error rate spikes 3x, auto-alert before users notice
- **Incident playbook**: Runbook for common issues: "DB connection pool exhausted → do X"

### 🧪 Tests for This Phase
- Test: Kill Redis → API returns degraded response (not 500)
- Test: Kill PostgreSQL → health endpoint returns 503 with details
- Test: Generate a 500 error → verify it appears in Sentry within 30 seconds
- Test: Slow query (>5s) → verify it's logged with query text and duration
- Test: High memory usage → verify alert fires

---

## Phase 12: 🛡️ Disaster Recovery, Backup & Compliance

### Scope
```
docker-compose*.yml (volumes)
PostgreSQL backup strategy
Data retention policies
SECURITY.md
Privacy-related code
Tenant data isolation
```

### Checklist

#### 12.1 Database Backup
- [ ] Check: Is there automated PostgreSQL backup? (pg_dump, WAL archiving, or cloud snapshots?)
- [ ] Check: How often? Daily? Hourly?
- [ ] Check: Where are backups stored? Same server = NOT a backup
- [ ] Check: Has anyone ever tested restoring from backup? How long does it take?
- [ ] Check: Is there point-in-time recovery (PITR)?
- [ ] Suggest: Automated daily backup + test restore weekly

#### 12.2 Data Recovery
- [ ] Check: If a tenant accidentally deletes their data, can it be recovered?
- [ ] Check: Is there soft delete or hard delete?
- [ ] Check: If the Bronze upload is wrong, can the pipeline be rolled back?
- [ ] Check: If a dbt model breaks, is the previous Gold data preserved?
- [ ] Suggest: Keep last 3 versions of each pipeline run (Gold snapshots)

#### 12.3 Infrastructure Recovery
- [ ] Check: If the server dies, how long to rebuild? (RTO — Recovery Time Objective)
- [ ] Check: How much data would be lost? (RPO — Recovery Point Objective)
- [ ] Check: Is the infrastructure defined as code (Docker Compose = partial IaC)?
- [ ] Check: Can you spin up a new environment from scratch with one command?
- [ ] Suggest: Document the disaster recovery procedure step by step

#### 12.4 Compliance & Data Privacy
- [ ] Check: Is there a privacy policy? (marketing page)
- [ ] Check: Does it comply with Egyptian data protection laws (EG PDPL 2020)?
- [ ] Check: Can a tenant request data deletion (right to be forgotten)?
- [ ] Check: Is pharma sales data considered sensitive? Any regulations?
- [ ] Check: Are audit logs maintained? (who accessed what data, when)
- [ ] Check: Is data encrypted at rest? In transit?
- [ ] Check: Are logs containing PII properly handled?

#### 12.5 Tenant Data Isolation
- [ ] Check: If RLS fails, is there a secondary defense?
- [ ] Check: Are backups per-tenant or global? (Can you restore one tenant without affecting others?)
- [ ] Check: Can a tenant export ALL their data? (data portability)
- [ ] Check: When a tenant cancels, what happens to their data? Retention period?

### 💡 Creative Improvements
- **Self-service data export**: "Download all my data" button in settings — builds trust
- **Backup status in admin**: Show last backup time, size, and "restore tested" status
- **Data retention settings**: Let tenants choose: keep data 1 year, 3 years, 5 years, forever
- **Compliance badge on landing page**: "Your data is encrypted, backed up daily, and never shared" — builds trust for pharma companies

### 🧪 Tests for This Phase
- Test: Simulate full DB restore from backup → verify data integrity
- Test: Delete a tenant → verify ALL their data is removed (no orphans)
- Test: RLS bypass attempt → verify blocked at multiple layers
- Test: Export tenant data → verify completeness
- Test: Pipeline rollback → verify Gold data reverts to previous version

---

## Phase 13: 🏢 Multi-Tenancy & SaaS Readiness Audit

### Scope
```
All tenant-related code
RLS policies
Config/settings per tenant
Resource limits per tenant
Onboarding flow
Tenant management
```

### Checklist

#### 13.1 Tenant Isolation
- [ ] Check: Is tenant_id enforced at EVERY layer? (API → Service → Repository → DB)
- [ ] Check: Are there any shared resources that could leak between tenants? (Redis cache keys, file uploads, temp files)
- [ ] Check: Are API rate limits per-tenant or global?
- [ ] Check: Are background jobs (Celery) tenant-aware?
- [ ] Check: Are n8n workflows tenant-scoped?
- [ ] Check: Are file uploads stored with tenant prefix? (No collision)

#### 13.2 Tenant Onboarding
- [ ] Check: What's the process to add a new tenant? Manual? Self-serve?
- [ ] Check: Does the DB automatically set up schemas/RLS for new tenants?
- [ ] Check: Is there a tenant provisioning script/API?
- [ ] Check: How long does onboarding take? (Should be <1 minute)
- [ ] Suggest: Self-serve signup → auto-provision → guided setup wizard

#### 13.3 Tenant Configuration
- [ ] Check: Can tenants customize: logo, colors, currency, language, timezone?
- [ ] Check: Can tenants have different feature sets? (Feature flags per plan)
- [ ] Check: Can tenants have different data retention policies?
- [ ] Check: Can admins manage their own users?

#### 13.4 Resource Limits & Fair Use
- [ ] Check: Is there a max rows per tenant? Max storage?
- [ ] Check: Is there a max concurrent users per tenant?
- [ ] Check: Is AI insights usage limited per tenant? (OpenRouter costs money)
- [ ] Check: Is export size limited?
- [ ] Suggest: Implement usage quotas with clear overage policy

#### 13.5 Billing Readiness
- [ ] Check: Is there usage tracking per tenant? (API calls, rows processed, AI calls)
- [ ] Check: Is there a plan/tier model in the DB?
- [ ] Check: Is Stripe (or local payment gateway) integrated?
- [ ] Suggest for Egypt: Consider **Paymob** or **Fawry** as local payment alternatives
- [ ] Suggest: Start with manual invoicing for first 10 customers, then automate

#### 13.6 Admin Panel
- [ ] Check: Is there a super-admin dashboard to manage all tenants?
- [ ] Check: Can admins view: tenant list, usage stats, pipeline status, error counts?
- [ ] Check: Can admins impersonate a tenant (for support)?
- [ ] Check: Can admins disable/suspend a tenant?

### 💡 Creative Improvements
- **Tenant health dashboard** (admin): Traffic light per tenant — green (active, healthy), yellow (low usage), red (errors or inactive)
- **Usage-based upsell**: "You've used 80% of your AI insights this month — upgrade to Pro for unlimited"
- **White-label option**: Let bigger clients use their own logo and domain (premium feature)
- **Team management**: Let tenant admins invite colleagues, set roles (viewer, editor, admin)
- **Onboarding checklist**: After signup, show: ☑ Upload data ☐ Explore dashboard ☐ Set first target ☐ Invite team member — gamify the setup

### 🧪 Tests for This Phase
- Test: Create 2 tenants → verify complete data isolation
- Test: Tenant A queries → zero results from Tenant B
- Test: New tenant signup → auto-provisioned in <30 seconds
- Test: Hit usage quota → clear error message + upgrade prompt
- Test: Suspend tenant → all API calls return 403
- Test: Delete tenant → all data fully removed within 24 hours

---

## 🧰 Recommended Tools & Additions

### Must-Have (Add Now)
| Tool | Purpose | Priority |
|------|---------|----------|
| **Sentry** (already optional) | Error tracking — make it mandatory | 🔴 Critical |
| **Renovate / Dependabot** | Automated dependency updates | 🔴 Critical |
| **Trivy** | Docker image vulnerability scanning | 🔴 Critical |
| **axe-core** | Automated accessibility testing | 🟡 High |
| **Lighthouse CI** | Performance budgets in CI | 🟡 High |
| **k6 or Locust** | Load/performance testing | 🟡 High |

### Should-Have (Add Soon)
| Tool | Purpose | Priority |
|------|---------|----------|
| **Storybook** | Component library & visual testing | 🟡 High |
| **Chromatic** | Visual regression testing | 🟡 High |
| **Great Expectations** | Data validation framework | 🟡 High |
| **PostHog / Mixpanel** | Product analytics (user behavior) | 🟡 High |
| **next-intl** | Internationalization framework | 🟡 High |
| **react-pdf** | Client-side PDF report generation | 🟡 High |

### Nice-to-Have (Future)
| Tool | Purpose | Priority |
|------|---------|----------|
| **Pact** | Contract testing (API ↔ Frontend) | 🟢 Medium |
| **mutmut** | Mutation testing | 🟢 Medium |
| **Turborepo** | Monorepo build optimization | 🟢 Medium |
| **OpenTelemetry** | Distributed tracing | 🟢 Medium |
| **Upstash** | Serverless Redis (for production) | 🟢 Medium |
| **Novu** | Notification infrastructure (email, WhatsApp, push) | 🟢 Medium |
| **Resend** | Transactional email | 🟢 Medium |
| **Cal.com embed** | Demo booking on landing page | 🔵 Low |

### New — For Phases 10–13
| Tool | Purpose | Priority |
|------|---------|----------|
| **PostHog** | Product analytics + session replay + feature flags | 🔴 Critical |
| **Grafana + Prometheus** | Infrastructure monitoring dashboards | 🔴 Critical |
| **pgBackRest** | PostgreSQL backup & point-in-time recovery | 🔴 Critical |
| **Paymob / Fawry** | Egyptian local payment gateway | 🟡 High |
| **Stripe** | International billing (if expanding beyond Egypt) | 🟡 High |
| **Loki** | Log aggregation (pairs with Grafana) | 🟡 High |
| **Better Uptime / UptimeRobot** | External uptime monitoring + status page | 🟡 High |
| **LaunchDarkly / Unleash** | Feature flags per tenant/plan | 🟡 High |
| **Crisp / Intercom** | In-app chat support for users | 🟢 Medium |
| **Loops / Customer.io** | Lifecycle email (onboarding, retention, churn prevention) | 🟢 Medium |
| **Hotjar** | Heatmaps + session recordings (see where users get stuck) | 🟢 Medium |

---

## 📋 How to Run This Audit

### Option A: Phase by Phase (Recommended)
```
Start with Phase 1. Read every file in scope.
Generate a report: findings + fixes + tests.
Apply fixes. Run tests. Commit.
Move to Phase 2. Repeat.
```

### Option B: Quick Scan (Overview First)
```
Scan all phases at surface level.
Generate a prioritized issue list: Critical → High → Medium → Low.
Fix Critical issues first across all phases.
Then go deep phase by phase.
```

### For Each Issue Found, Report:
```markdown
### [SEVERITY] Issue Title
- **Location**: file:line
- **Problem**: What's wrong
- **Impact**: What could go wrong (security breach? data loss? bad UX?)
- **Fix**: Specific code change
- **Test**: Test that verifies the fix
- **UX Impact**: Does this affect the user experience? How?
```

---

## Phase 14: 🏥 Pharma-Specific Compliance & AI Data Privacy Deep Dive

> Phase 12.4 covered compliance basics. This phase goes DEEP — pharma data is sensitive, AI sends data externally, and Egyptian law has specific requirements.

### Scope
```
backend/ai_light/ (what data is sent to OpenRouter?)
backend/export/ (what can be exported?)
All database tables containing PII (customer names, staff names)
frontend/src/app/(marketing)/terms/
frontend/src/app/(marketing)/privacy/
structlog configuration (what's logged?)
Redis cache contents
File upload storage
```

### Checklist

#### 14.1 Egyptian Data Protection Law (Law No. 151/2020)
- [ ] Read Terms of Service and Privacy Policy pages — are they **real** or placeholder?
- [ ] Check: Is there **explicit consent** before processing user data? (Not just "by using this site you agree")
- [ ] Check: Is there a **data controller** and **data processor** designation?
- [ ] Check: Can users **request a copy** of all their data? (portability)
- [ ] Check: Can users **request permanent deletion**? And is it ACTUALLY deleted (not soft-delete)?
- [ ] Check: Is there a **data breach notification** process documented?
- [ ] Check: Is data stored in Egypt or leaving to foreign servers?
- [ ] Suggest: Add a proper consent flow during signup with granular checkboxes

#### 14.2 AI & Third-Party Data Leakage
- [ ] Read `ai_light/` service — trace EXACTLY what data is in each API call to OpenRouter
- [ ] Check: Are **customer names** sent to OpenRouter? (they shouldn't be)
- [ ] Check: Are **staff names** sent? (they shouldn't be)
- [ ] Check: Are **drug names + quantities** sent? (commercially sensitive — anonymize?)
- [ ] Check: Is there a **data anonymization layer** before AI calls?
  ```
  Replace: "Ahmed Hassan bought 500 units of Augmentin"
  With:    "Customer_A bought 500 units of Product_X"
  ```
- [ ] Check: What's OpenRouter's **data retention policy**? Do they store/train on prompts?
- [ ] Check: Is there a **user toggle** to disable AI features entirely?
- [ ] Check: Are AI responses **cached** so same data isn't sent multiple times?
- [ ] Suggest: Add a `[AI Data Policy]` section in Privacy page explaining what AI sees

#### 14.3 Pharma-Specific Data Sensitivity
- [ ] Classify ALL data fields:
  - **Public**: Product categories, date ranges
  - **Internal**: Sales volumes, revenue figures
  - **Confidential**: Customer names, staff performance, pricing
  - **Restricted**: Any patient-adjacent data (if exists)
- [ ] Check: Can a sales rep see **other reps' performance** via the API? (authorization issue)
- [ ] Check: Can a branch manager see **other branches' data**? (should they?)
- [ ] Check: Export of detailed customer lists — is this **restricted by role**?
- [ ] Check: Are drug sales volumes considered **trade secrets** by clients? If yes → extra protection

#### 14.4 Audit Trail (Mandatory for Pharma)
- [ ] Check: Is EVERY data access logged? (who, what, when, from where)
- [ ] Check: Are logins logged? (successful + failed, with IP)
- [ ] Check: Are exports logged? ("Ahmed exported Customer Report at 14:30 from 196.xxx.xxx")
- [ ] Check: Are AI queries logged? (what was asked, what was returned)
- [ ] Check: Are pipeline runs logged with who triggered them?
- [ ] Check: Is the audit log **immutable**? (nobody can delete audit entries)
- [ ] Suggest: Add audit log viewer in admin panel — searchable and exportable

#### 14.5 PII in Logs & Cache
- [ ] Grep structlog output for PII patterns: emails, phone numbers, names
- [ ] Check: Does Redis cache store customer names or staff names?
- [ ] Check: Are error logs sanitized? (no PII in stack traces)
- [ ] Check: Are API request logs safe? (no sensitive query params logged)
- [ ] Check: Sentry — if enabled, does it capture PII in error reports?
- [ ] Suggest: Add PII scrubbing middleware for all logging

### 💡 Creative Improvements

1. **Privacy dashboard for admins**: One page showing: data stored, AI usage, export log, active sessions — full transparency

2. **AI anonymization toggle**: In settings → "AI Privacy Mode: ON" → all names replaced with codes before AI processing. Show a visual: "Your data → 🔒 Anonymized → 🤖 AI → 💡 Insights"

3. **Data classification badges**: On every page/export, show a small badge: "🟢 Public Data" or "🔴 Confidential — Do Not Share"

4. **Consent re-confirmation**: After 12 months, prompt users to re-confirm consent (Egyptian law requirement)

5. **"Who accessed my data?" page**: Let tenant admins see exactly which users viewed/exported what

6. **Compliance export pack**: One-click download: privacy policy, data processing agreement, audit log, data inventory — for client compliance officers

### 🧪 Tests for This Phase
- Test: AI insight request → capture HTTP payload → zero PII (names, phones, emails)
- Test: structlog output for 100 API requests → grep for PII patterns → zero matches
- Test: Redis cache dump → grep for customer/staff names → zero matches
- Test: Sentry error payload → no PII in error context
- Test: Delete tenant → ALL data gone from: PostgreSQL, Redis, file storage, audit logs
- Test: Role-based export → sales rep cannot export other reps' data
- Test: Audit log → immutable (attempt DELETE on audit table → blocked)
- Test: Privacy page → exists, has real content, mentions Egyptian data law

---

## Phase 15: 🧑‍💻 Developer Experience (DX) & Bus Factor

> If Ahmed (the primary developer) is unavailable, can someone else understand, run, fix, and deploy DataPulse within 24 hours?

### Scope
```
README.md
CLAUDE.md
CONTRIBUTING.md
docs/ (all documentation)
docs/team-configs/ (role-based CLAUDE configs)
Makefile / scripts/
Code comments quality
Error messages quality
.claude/ (agents and skills)
```

### Checklist

#### 15.1 New Developer Onboarding
- [ ] **Test this yourself**: Follow README from `git clone` — can you get a working system in <10 minutes?
- [ ] Check: Are ALL prerequisites listed (Docker version, Node version, Python version)?
- [ ] Check: Is `docker compose up` sufficient or are there undocumented manual steps?
- [ ] Check: Are seed/sample data scripts available? (new dev needs data to see dashboards)
- [ ] Check: Are environment variables documented with example values?
- [ ] Check: Is there a "Your First Contribution" guide?
- [ ] Check: Do the 6 role-based CLAUDE.md configs actually work when copied?

#### 15.2 Documentation Freshness
- [ ] Read CLAUDE.md — does it match current codebase? (endpoints, modules, patterns)
- [ ] Read all 18 docs/plans/ files — which are outdated?
- [ ] Check: Are **Architecture Decision Records (ADRs)** documented?
  - Why FastAPI over Django?
  - Why dbt over raw SQL transforms?
  - Why SWR over React Query?
  - Why Polars over Pandas for Bronze?
  - Why Auth0 over self-hosted auth?
  - Why OpenRouter over direct OpenAI?
- [ ] Check: Is the API auto-documented (OpenAPI/Swagger)?
- [ ] Check: Is `dbt docs generate` producing a lineage graph?
- [ ] Check: Are the 7 n8n workflows documented (what each one does)?

#### 15.3 Code Readability & Self-Documentation
- [ ] Check: Do complex functions have docstrings explaining WHAT and WHY?
- [ ] Check: Are magic numbers replaced with named constants?
- [ ] Check: Are business rules documented IN the code?
  - "Deduplication: keep latest by invoice_id + product_key"
  - "COALESCE to -1 means: unknown dimension member"
  - "Billing type normalization: Arabic → English mapping"
- [ ] Check: Are complex SQL/dbt queries commented (what each CTE does)?
- [ ] Check: Are variable/function names descriptive (not `x`, `tmp`, `data2`)?

#### 15.4 Error Messages as Documentation
- [ ] Audit error messages across the codebase — do they tell you:
  - **WHAT** went wrong?
  - **WHERE** it happened?
  - **HOW** to fix it?
- [ ] ❌ Bad: `"Error processing file"`
- [ ] ✅ Good: `"Column 'sales_date' not found in uploaded file. Expected: sales_date, product_name, quantity, price. Check your Excel headers (Row 1)."`
- [ ] Fix: Any generic error messages → make them actionable

#### 15.5 Development Workflow
- [ ] Check: Is there a Makefile with common tasks?
  ```
  make dev        # Start dev environment
  make test       # Run all tests
  make lint       # Lint + format
  make db-reset   # Reset DB with seed data
  make db-migrate # Run pending migrations
  make dbt-run    # Run dbt models
  make build      # Build production images
  make deploy     # Deploy to production
  ```
- [ ] Check: Are **pre-commit hooks** set up? (lint, format, typecheck)
- [ ] Check: Is there a **PR template** with checklist?
- [ ] Check: Is the **branching strategy** documented?
- [ ] Check: Can the 7 Claude Code agents actually run successfully?

#### 15.6 Bus Factor Mitigation
- [ ] Calculate: How many people understand each module?
  | Module | People who understand it | Bus Factor Risk |
  |--------|------------------------|-----------------|
  | Bronze pipeline | ? | 🔴 / 🟡 / 🟢 |
  | dbt models | ? | 🔴 / 🟡 / 🟢 |
  | FastAPI backend | ? | 🔴 / 🟡 / 🟢 |
  | Next.js frontend | ? | 🔴 / 🟡 / 🟢 |
  | Docker/infra | ? | 🔴 / 🟡 / 🟢 |
  | Auth (Auth0) | ? | 🔴 / 🟡 / 🟢 |
  | n8n workflows | ? | 🔴 / 🟡 / 🟢 |
- [ ] Check: Are deployment credentials in a **shared vault** (not one person's laptop)?
- [ ] Check: Is there a **runbook** for common incidents?
  ```
  Database is down     → Step 1, Step 2, Step 3
  Pipeline fails       → Step 1, Step 2, Step 3
  Auth0 is unavailable → Step 1, Step 2, Step 3
  Redis is full        → Step 1, Step 2, Step 3
  Disk space low       → Step 1, Step 2, Step 3
  ```
- [ ] Suggest: Create a **"Break Glass" document** — emergency procedures + all access credentials in a secure vault (Bitwarden, 1Password)

### 💡 Creative Improvements

1. **Interactive architecture diagram**: Mermaid diagram in docs showing all services — click a service to see its endpoints, dependencies, and owner

2. **5-minute video walkthroughs**: Record Loom videos per module:
   - "How Bronze pipeline works" (5 min)
   - "How auth flows work" (5 min)
   - "How to add a new API endpoint" (5 min)
   - "How to add a new dashboard page" (5 min)

3. **Developer onboarding checklist**: Interactive checklist for new devs:
   - ✅ Clone repo
   - ✅ Run docker compose up
   - ✅ Open dashboard at localhost:3000
   - ⬜ Upload sample data
   - ⬜ Run tests
   - ⬜ Make your first code change
   - ⬜ Submit your first PR

4. **Architecture fitness functions**: Automated tests that enforce architecture rules:
   ```python
   # No route file should import a repository directly (must go through service)
   # No frontend component should exceed 300 lines
   # Every dbt model must have at least one test
   # Every API endpoint must have an auth decorator
   # Every service function must have a docstring
   ```

5. **Incident journal**: `docs/incidents/` — log every past incident:
   - What happened, when, impact, root cause, how it was fixed, how to prevent it
   - Invaluable for new developers and for patterns

6. **Dependency graph visualization**: Auto-generated graph showing which modules import which — helps new devs understand the blast radius of a change

### 🧪 Tests for This Phase
- Test: Fresh git clone → `docker compose up` → health check passes (automated in CI)
- Test: All Makefile targets run without errors
- Test: Pre-commit hooks catch a deliberate style violation
- Test: Architecture fitness: no route file imports a repository directly
- Test: Architecture fitness: all dbt models have a schema.yml entry
- Test: Architecture fitness: all API endpoints have auth (grep for undecorated routes)
- Test: No TODO/FIXME older than 30 days without a linked GitHub Issue
- Test: README instructions produce a working system (full integration test)
- Test: Error messages: trigger 10 common errors → all messages are actionable

---

## 🧰 Additional Tools for Phase 14 & 15

| Tool | Phase | Purpose | Priority |
|------|-------|---------|----------|
| **Presidio (Microsoft)** | 14 | PII detection & anonymization in text | 🔴 Critical |
| **CookieYes / Osano** | 14 | Cookie consent + privacy compliance | 🟡 High |
| **Vault (HashiCorp)** | 14,15 | Secrets management | 🟡 High |
| **Docusaurus / Mintlify** | 15 | Beautiful documentation site | 🟡 High |
| **Linear / Plane** | 15 | Issue tracking (better than GH Issues for product) | 🟡 High |
| **Backstage (Spotify)** | 15 | Internal developer portal | 🟢 Medium |
| **ArchUnit (Python equiv)** | 15 | Architecture fitness function tests | 🟢 Medium |
| **Loom** | 15 | Video walkthroughs for docs | 🟢 Medium |

---

## 🏁 End Goal

After completing all **15 phases**, DataPulse should be:

1. ✅ **Secure** — No auth bypass, no SQL injection, no data leaks, compliance-ready
2. ✅ **Reliable** — Pipeline handles errors gracefully, services auto-recover, backups tested
3. ✅ **Fast** — Dashboard loads in <2s, API responses in <500ms, pipeline <5min
4. ✅ **Tested** — 95%+ backend coverage, E2E for all critical paths, frontend unit tests
5. ✅ **Maintainable** — Clean code, documented decisions, automated dependency updates
6. ✅ **Delightful** — Non-technical users love using it, guided experiences, helpful errors
7. ✅ **Observable** — Structured logs, error tracking, performance dashboards, alerting
8. ✅ **Recoverable** — Automated backups, tested restore, disaster recovery playbook
9. ✅ **Multi-tenant** — Complete isolation, self-serve onboarding, usage quotas, billing-ready
10. ✅ **Bilingual** — Arabic + English, RTL support, localized formatting
11. ✅ **Scalable** — Performance tested, caching strategy, async processing, 100+ tenants
12. ✅ **Marketable** — Clear value prop, compelling landing, GTM strategy, pricing model
13. ✅ **Profitable** — Unit economics work, retention hooks, churn prevention, growth loops
14. ✅ **Compliant** — Pharma data privacy, AI anonymization, audit trails, Egyptian PDPL
15. ✅ **Survivable** — Any developer can understand, run, and fix the system in 24 hours

---

*Generated for DataPulse SaaS — Pharmaceutical Sales Analytics Platform*
*Architecture: FastAPI + Next.js 14 + PostgreSQL + dbt + Docker*
*Target: Egyptian pharma sales managers & analysts*
