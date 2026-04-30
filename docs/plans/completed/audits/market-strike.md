# Market Strike — Competitive Features Plan

**Date:** 2026-04-09 | **Codebase:** DataPulse SaaS
**Scope:** 6 Tiers, ~70 hours | **Goal:** Transform from internal tool to market-ready SaaS competitor
**Execution order:** After Iron Curtain (hardening) + Unlock the Vault (activation)

---

## Context

A competitor analysis of 7 platforms (Zoho Analytics, Metabase, Holistics, Mode, Looker, Sisense, Power BI) + graph analysis of DataPulse's orphaned infrastructure revealed:

**DataPulse has 70% of the backend for SaaS monetization already built but not wired:**
- `BillingService` — ZERO callers (graph: orphaned)
- `OnboardingService` — ZERO callers (graph: orphaned)
- `ResellerService` — ZERO callers (graph: orphaned)
- `RBACService` — ZERO callers (graph: orphaned)
- Stripe integration — checkout, portal, webhooks all coded but no plan enforcement
- Plans defined (Starter/Pro/Enterprise) but limits never checked

**DataPulse has one nuclear competitive advantage no competitor exploits:**
- **Arabic/RTL** — Power BI Desktop excludes Arabic. Metabase has an open RTL issue since 2023. Zoho, Holistics, Looker, Sisense, Mode — none support Arabic dashboards. The MENA retail/pharmacy market has ZERO proper analytics tools.

**The #1 feature every competitor has that DataPulse doesn't:**
- Natural language "ask a question" (Zoho Zia, Power BI Copilot, Metabase Metabot, Looker Conversational)

---

## Graph Evidence: Revenue Infrastructure (All Orphaned)

```
dp_context("BillingService")    → callers: 0, imports: 0, tests: 0
dp_context("OnboardingService") → callers: 0, imports: 0, tests: 0
dp_context("ResellerService")   → callers: 0, imports: 0, tests: 0
dp_context("RBACService")       → callers: 0, imports: 0, tests: 0
dp_context("StripeClient")      → callers: 0, tests: 0
```

All have database tables, models, repositories, services, and API routes.
None are wired into the application lifecycle.

---

## T1: Revenue Engine (Make Users Pay)
**Priority:** P0 — Can't be a business without revenue | **Est:** ~12 hours
**Dependencies:** Iron Curtain T1 (auth hardening)

### T1.1 Self-service signup flow
**What exists:** Auth0 OIDC. `bronze.tenants` table. RBAC auto-registers users on first login. Marketing landing page with pricing cards.

**What's missing:** No public signup → tenant creation flow.

**Backend (new):**
- `src/datapulse/api/routes/auth.py` or extend `onboarding`:
  - `POST /api/v1/auth/signup` — creates tenant + sets user as owner
  - Steps: validate email → create tenant in `bronze.tenants` → set plan=starter → create RBAC entry as owner
  - Returns: JWT redirect to onboarding wizard
- Wire `OnboardingService` into the flow (it's already built with 3 steps: connect_data, first_report, first_goal)

**Frontend (new):**
- `frontend/src/app/(marketing)/signup/page.tsx` — signup form: name, email, company name, password
- After signup → redirect to `/dashboard` with onboarding wizard overlay
- Wire the existing onboarding components (directory exists at `frontend/src/components/onboarding/`)

**Frontend (modify):**
- Pricing cards CTA "Get Started" → links to `/signup?plan=starter` or `/signup?plan=pro`
- Pro plan CTA → `/signup?plan=pro` → after signup, redirect to Stripe checkout

**Risk:** MEDIUM — new auth flow
**Est:** 5h

### T1.2 Wire plan limit enforcement
**What exists:** `get_tenant_plan_limits()` at `deps.py:198`. `PLAN_LIMITS` dict in `billing/plans.py` with limits per tier (data_sources, max_rows, features). Usage tracking table `usage_metrics`. Billing page shows usage vs limits.

**What's missing:** No endpoint checks limits before operations.

**Backend (new):**
- `src/datapulse/billing/enforcement.py` — new middleware/dependency:
  ```python
  def require_feature(feature_name: str):
      """FastAPI dependency that checks tenant plan allows this feature"""
      def _check(limits = Depends(get_tenant_plan_limits)):
          if not limits.features.get(feature_name, False):
              raise HTTPException(402, f"Upgrade to access {feature_name}")
      return _check

  def require_row_limit():
      """Check tenant hasn't exceeded max_rows"""
      ...
  ```
- Apply to routes:
  - `POST /pipeline/trigger` → `require_feature("pipeline_automation")` + `require_row_limit()`
  - `GET /ai-light/*` → `require_feature("ai_insights")`
  - `POST /explore/query` → `require_feature("custom_queries")`
  - `POST /report-schedules` → `require_feature("scheduled_reports")`

**Frontend (modify):**
- Show upgrade prompts when 402 is returned: "This feature requires Pro. Upgrade now →"
- `frontend/src/components/shared/upgrade-gate.tsx` — wrapper component that checks plan and shows upgrade CTA

**Risk:** MEDIUM — may break existing demo/dev flows if plan is "starter"
**Est:** 3h

### T1.3 Wire usage tracking
**What exists:** `usage_metrics` table with `data_sources_count`, `total_rows`. `BillingRepository.upsert_usage()` method.

**Backend (modify):**
- `src/datapulse/pipeline/executor.py` — after successful bronze load:
  ```python
  billing_repo.upsert_usage(tenant_id, data_sources_count=1, total_rows=row_count)
  ```
- `src/datapulse/upload/service.py` — after confirm:
  ```python
  billing_repo.increment_data_sources(tenant_id)
  ```

**Risk:** LOW
**Est:** 2h

### T1.4 Wire subscription cancellation
**What exists:** `StripeClient.create_portal_session()` handles Stripe-side management. Webhook handles `customer.subscription.deleted`.

**What's missing:** No explicit cancel endpoint. Users must go through Stripe portal.

**Backend (new):**
- `POST /api/v1/billing/cancel` — calls `stripe.Subscription.cancel(subscription_id)` then updates local DB
- Send confirmation email (using email service from Unlock the Vault T3)

**Frontend (modify):**
- Add "Cancel Subscription" button on billing page with `ConfirmDialog` (already exists from T6.3 UX)

**Risk:** LOW
**Est:** 2h

### T1 Verification
```bash
# Signup flow
curl -X POST localhost:8000/api/v1/auth/signup -d '{"email":"test@example.com","name":"Test"}'
# Plan enforcement
curl localhost:8000/api/v1/ai-light/summary  # 402 on starter plan
# Usage tracking
# Trigger pipeline → verify usage_metrics incremented
# Cancel
curl -X POST localhost:8000/api/v1/billing/cancel
```

---

## T2: Arabic/RTL — The Nuclear Differentiator
**Priority:** P0 — No competitor does this. Owns the MENA market. | **Est:** ~14 hours
**Dependencies:** None

### Why This Is The #1 Competitive Move

| Competitor | Arabic Support | RTL Dashboard | Verdict |
|------------|---------------|---------------|---------|
| Power BI Desktop | Excludes Arabic | No RTL in reports | Broken |
| Metabase | Open issue #34318 since 2023 | No | Missing |
| Zoho Analytics | Locale settings only | No RTL UI | Partial |
| Holistics | None | None | Missing |
| Looker | Not in supported languages | No | Missing |
| Sisense | None | None | Missing |
| Mode | None | None | Missing |
| **DataPulse** | Comments in Arabic | **Not yet** | **Opportunity** |

**There are ~450M Arabic speakers. The MENA retail/pharmacy market is growing 15%+ YoY. Nobody serves them.**

### T2.1 RTL layout infrastructure
**Frontend (modify):**
- `frontend/src/app/layout.tsx` — add `dir` attribute based on locale:
  ```tsx
  <html lang={locale} dir={locale === 'ar' ? 'rtl' : 'ltr'}>
  ```
- `frontend/src/globals.css` — add RTL variants:
  ```css
  [dir="rtl"] .sidebar { right: 0; left: auto; }
  [dir="rtl"] .chart-label { text-anchor: end; }
  ```
- Use Tailwind CSS RTL plugin (`tailwindcss-rtl`) or logical properties (`ps-4` instead of `pl-4`, `me-2` instead of `mr-2`)

**Risk:** MEDIUM — affects entire layout
**Est:** 4h

### T2.2 Arabic translation file
**Frontend (new):**
- `frontend/src/locales/ar.json` — Arabic translations for:
  - Navigation: Dashboard (لوحة المعلومات), Products (المنتجات), Customers (العملاء), Staff (الموظفين), etc.
  - KPI labels: Revenue (الإيرادات), Transactions (المعاملات), Growth (النمو), etc.
  - Buttons: Save (حفظ), Export (تصدير), Filter (تصفية), etc.
  - Chart labels: Daily (يومي), Monthly (شهري), Annual (سنوي), etc.
- `frontend/src/locales/en.json` — English (current hardcoded strings extracted)
- `frontend/src/lib/i18n.ts` — minimal i18n hook using `next-intl` or lightweight custom:
  ```ts
  export function useTranslation() {
      const locale = useLocale(); // from cookie or user preference
      const t = (key: string) => messages[locale][key] || key;
      return { t, locale, dir: locale === 'ar' ? 'rtl' : 'ltr' };
  }
  ```

**Risk:** LOW
**Est:** 4h

### T2.3 Arabic number formatting
**Frontend (modify):**
- `frontend/src/lib/formatters.ts` — extend `formatCurrency`, `formatCompact`, `formatPercent`:
  ```ts
  // Current: formatCurrency(1234.56) → "$1,234.56"
  // Arabic:  formatCurrency(1234.56, 'ar-EG') → "١٬٢٣٤٫٥٦ ج.م"
  ```
- Use `Intl.NumberFormat('ar-EG', { style: 'currency', currency: 'EGP' })` (already available in all browsers)
- Date formatting: `Intl.DateTimeFormat('ar-EG')` for Arabic date strings

**Risk:** LOW — uses browser-native APIs
**Est:** 2h

### T2.4 RTL chart rendering (Recharts)
**Frontend (modify):**
- Recharts doesn't natively support RTL. Fix:
  - Mirror `XAxis` orientation: `reversed={isRTL}`
  - Swap `YAxis` to right side: `orientation={isRTL ? 'right' : 'left'}`
  - Flip tooltip positioning
  - Legend alignment: `align={isRTL ? 'right' : 'left'}`
- Apply to: `daily-trend-chart.tsx`, `monthly-trend-chart.tsx`, `billing-breakdown-chart.tsx`, `customer-type-chart.tsx`, all chart components

**Risk:** MEDIUM — must test each chart type
**Est:** 3h

### T2.5 Language switcher
**Frontend (new):**
- `frontend/src/components/layout/language-switcher.tsx` — EN/AR toggle in sidebar footer (next to theme toggle)
- Persist preference in cookie + user profile (API)
- Backend: `PATCH /api/v1/members/me/preferences` — save `{locale: 'ar'}`

**Risk:** LOW
**Est:** 1h

### T2 Verification
```bash
# Switch to Arabic → entire UI flips to RTL
# Numbers show Arabic-Indic digits
# Charts have YAxis on right, XAxis reversed
# All navigation labels in Arabic
# Theme toggle + language toggle coexist
npm run build && npx tsc --noEmit
```

---

## T3: Natural Language "Ask a Question"
**Priority:** P0 — #1 feature every competitor has | **Est:** ~12 hours
**Dependencies:** Unlock the Vault T1 (rolling analytics), Iron Curtain T2 (exception handling)

### T3.1 Build NL query parser
**What exists:** `ai_light/client.py` calls OpenRouter. `explore/sql_builder.py` generates safe parameterized SQL from structured queries. `explore/manifest_parser.py` knows all available dbt models, columns, and metrics.

**The key insight:** We don't need a full text-to-SQL engine. We have `sql_builder.py` that takes structured `{model, dimensions, metrics, filters}` input. We just need AI to convert "what were my top products last month?" into that structured format.

**Backend (new):**
- `src/datapulse/ai_light/nl_query.py` — new module (~150 lines):
  ```python
  class NLQueryParser:
      def __init__(self, catalog: dict, client: OpenRouterClient):
          pass
      
      async def parse(self, question: str, locale: str = "en") -> ExploreQuery:
          """Convert natural language to structured ExploreQuery.
          
          Uses the dbt catalog as context for the LLM:
          - Available models, dimensions, metrics
          - Column descriptions from schema.yml
          
          Prompt: "Given these available fields: [catalog]. 
          Convert this question to JSON: {model, dimensions, metrics, filters, order_by, limit}.
          Question: [user question]"
          
          Returns ExploreQuery that sql_builder.py can execute.
          """
  ```
- `src/datapulse/api/routes/explore.py` — add:
  - `POST /api/v1/explore/ask` — accepts `{"question": "...", "locale": "en|ar"}`
  - Internally: parse question → build SQL via `sql_builder` → execute → return results + generated chart suggestion

**Frontend (new):**
- `frontend/src/components/shared/ask-bar.tsx` — search-like input at the top of every page:
  - Placeholder: "Ask a question... e.g. 'top 10 products by revenue this month'"
  - Arabic: "اسأل سؤال... مثال: 'أفضل 10 منتجات بالإيرادات هذا الشهر'"
  - On submit → calls `/api/v1/explore/ask`
  - Shows: result table + auto-generated chart + "View as Custom Report" link
- `frontend/src/hooks/use-nl-query.ts` — SWR mutation hook
- Wire into app layout (persistent search bar at top, always visible)

**Risk:** HIGH — AI parsing quality depends on prompt engineering
**Est:** 8h

### T3.2 Add follow-up questions
**Backend (modify):**
- `nl_query.py` — add conversation context:
  - `parse(question, previous_query=None)` — if previous query exists, AI understands "now show me by month" means "same filters, add month dimension"
- API: `POST /api/v1/explore/ask` accepts optional `previous_query_id`

**Frontend (modify):**
- `ask-bar.tsx` — show suggested follow-up questions after results:
  - "Break this down by category"
  - "Show me the trend over time"
  - "Compare with last year"

**Risk:** MEDIUM
**Est:** 2h

### T3.3 Arabic NL support
**Backend (modify):**
- `nl_query.py` — prompt includes: "The user may ask in Arabic or English. Parse the intent regardless of language."
- Column name mapping: add Arabic aliases to dbt schema.yml `meta` field:
  ```yaml
  - name: drug_name
    meta:
      alias_ar: "اسم الدواء"
  ```
- The NL parser reads these aliases and maps Arabic terms to column names

**Risk:** MEDIUM — Arabic NLP quality varies by model
**Est:** 2h

### T3 Verification
```bash
# English
curl -X POST localhost:8000/api/v1/explore/ask -d '{"question":"top 10 products by revenue this month"}'
# Arabic
curl -X POST localhost:8000/api/v1/explore/ask -d '{"question":"أفضل 10 منتجات بالإيرادات","locale":"ar"}'
# Follow-up
curl -X POST localhost:8000/api/v1/explore/ask -d '{"question":"break down by category","previous_query_id":"..."}'
```

---

## T4: Data Connectors (Beyond Excel/CSV)
**Priority:** P1 — #1 acquisition blocker per competitor analysis | **Est:** ~14 hours
**Dependencies:** T1 (signup flow), Iron Curtain T1 (upload security)

### T4.1 Google Sheets connector
**What exists:** `UploadService` handles file-based ingestion. `bronze/loader.py` processes DataFrames into PostgreSQL. Polars can read from URLs.

**Backend (new):**
- `src/datapulse/connectors/google_sheets.py` — new module:
  ```python
  class GoogleSheetsConnector:
      def __init__(self, credentials_json: str):
          # Uses gspread + google-auth
          pass
      
      def list_sheets(self, spreadsheet_url: str) -> list[SheetInfo]:
          """List all sheets in a spreadsheet with row counts"""
      
      def fetch_data(self, spreadsheet_url: str, sheet_name: str) -> pl.DataFrame:
          """Fetch sheet data as Polars DataFrame"""
      
      def schedule_sync(self, config: SyncConfig) -> None:
          """Register periodic sync (daily/hourly)"""
  ```
- Install: `gspread`, `google-auth`
- API: `POST /api/v1/connectors/google-sheets/connect` — OAuth flow
- API: `POST /api/v1/connectors/google-sheets/sync` — trigger manual sync
- Feed into existing `bronze/loader.py` pipeline (DataFrame → Parquet → PostgreSQL)

**Frontend (new):**
- `frontend/src/components/upload/google-sheets-connector.tsx` — OAuth connect button + sheet selector
- Wire into UploadPage as second tab: "File Upload | Google Sheets"

**Risk:** HIGH — OAuth + external API
**Est:** 6h

### T4.2 Direct database connector (MySQL/PostgreSQL)
**Backend (new):**
- `src/datapulse/connectors/database.py`:
  ```python
  class DatabaseConnector:
      def __init__(self, connection_string: str):
          # Uses SQLAlchemy create_engine with read-only user
          pass
      
      def list_tables(self) -> list[TableInfo]:
          """Reflect available tables/views"""
      
      def fetch_table(self, table_name: str, limit: int = 100000) -> pl.DataFrame:
          """Read table into Polars DataFrame"""
  ```
- API: `POST /api/v1/connectors/database/test` — test connection
- API: `POST /api/v1/connectors/database/sync` — import selected tables
- Store connection configs encrypted in `connector_configs` table (new migration)

**Risk:** HIGH — credential security, network access
**Est:** 5h

### T4.3 Connector management UI
**Frontend (new):**
- `frontend/src/app/(app)/upload/page.tsx` — redesign as "Data Sources" page:
  - Tab 1: File Upload (existing)
  - Tab 2: Google Sheets (T4.1)
  - Tab 3: Database (T4.2)
  - Tab 4: (future: Shopify, POS)
- `frontend/src/components/connectors/connector-card.tsx` — shows connected sources with sync status, last sync time, row count

**Risk:** MEDIUM
**Est:** 3h

### T4 Verification
```bash
# Google Sheets
curl -X POST localhost:8000/api/v1/connectors/google-sheets/connect -d '{"spreadsheet_url":"..."}'
# Database
curl -X POST localhost:8000/api/v1/connectors/database/test -d '{"connection_string":"mysql://..."}'
# Verify data flows into bronze layer
docker exec datapulse-db psql -c "SELECT COUNT(*) FROM bronze.sales"
```

---

## T5: Team Management + Onboarding (First 5 Minutes)
**Priority:** P1 — First impression determines conversion | **Est:** ~8 hours
**Dependencies:** T1 (signup flow)

### T5.1 Guided onboarding wizard
**What exists:** `OnboardingService` with 3 steps (connect_data, first_report, first_goal). API routes. DB persistence. Frontend components directory.

**Frontend (new/modify):**
- `frontend/src/components/onboarding/onboarding-wizard.tsx` — full-screen modal on first login:
  - Step 1: "Connect Your Data" → upload widget or Google Sheets connect
  - Step 2: "See Your First Report" → auto-generate dashboard preview
  - Step 3: "Set Your First Goal" → revenue target input
  - Progress bar, skip button, "I'll do this later"
- Show wizard when `onboarding_completed = false` (check via `GET /onboarding/status`)
- After completion → confetti animation (reuse `success-animation.tsx` from T6.6 UX)

**Risk:** LOW
**Est:** 3h

### T5.2 Team member management UI
**What exists:** `RBACService` with invite, update role, remove member. `src/datapulse/api/routes/members.py` with full CRUD. Sectors support.

**Frontend (new):**
- `frontend/src/app/(app)/team/page.tsx` — page exists but verify completeness:
  - Member list with role badges (owner/admin/editor/viewer)
  - "Invite Member" button → email + role selector dialog
  - Role change dropdown per member
  - "Remove" with `ConfirmDialog` danger variant (already exists)
  - Sector assignment checkboxes
- `frontend/src/hooks/use-members.ts` — hook exists, verify CRUD methods

**Risk:** LOW — backend is complete
**Est:** 3h

### T5.3 In-app help tooltips
**Frontend (new):**
- `frontend/src/components/shared/help-tooltip.tsx` — small `?` icon with popover explaining each section:
  - Dashboard KPIs: "These numbers show your sales performance for the selected period"
  - Trend chart: "The daily trend shows revenue patterns. Look for dips on weekends."
  - Customer health: "Green = active buyer, Red = at risk of churning"
- Content stored in `frontend/src/lib/help-content.ts` (EN) + `help-content-ar.ts` (AR)
- Show only on first 3 visits (localStorage counter), then hide

**Risk:** LOW
**Est:** 2h

### T5 Verification
```bash
# Onboarding wizard appears on new user's first login
# Invite member → email sent (mock in dev) → new user joins
# Help tooltips visible on first visit, hidden after 3
npm run build
```

---

## T6: Embedded Analytics + Public API
**Priority:** P2 — Opens B2B/partner channel | **Est:** ~10 hours
**Dependencies:** T1 (billing, plan enforcement)

### T6.1 Expand embed to support dashboards
**What exists:** `embed/token.py` generates scoped JWT. `POST /embed/{token}/query` executes explore queries. Frontend embed page exists.

**Backend (modify):**
- `src/datapulse/api/routes/embed.py` — add:
  - `GET /embed/{token}/dashboard` — returns full dashboard data (same as `/analytics/dashboard` but scoped by embed token)
  - `GET /embed/{token}/kpis` — returns KPI summary
  - `GET /embed/{token}/chart/{chart_type}` — returns specific chart data

**Frontend (new):**
- `frontend/src/app/embed/[token]/dashboard/page.tsx` — embeddable dashboard (no sidebar, no nav, just charts)
- `frontend/src/app/embed/[token]/kpi/page.tsx` — embeddable KPI cards
- Add `?theme=light|dark` URL param for iframe theming

**Risk:** MEDIUM
**Est:** 4h

### T6.2 Public REST API documentation
**What exists:** FastAPI auto-generates OpenAPI spec at `/docs` (Swagger) and `/redoc`. But it's behind auth.

**Backend (modify):**
- `src/datapulse/api/app.py` — expose `/docs` publicly (read-only docs, not the API itself)
- Add API key authentication example in Swagger description
- Group endpoints by category in OpenAPI tags

**Frontend (new):**
- `frontend/src/app/(marketing)/api-docs/page.tsx` — redirect to `/docs` or embed Swagger UI
- Add "API" link in marketing footer

**Risk:** LOW
**Est:** 2h

### T6.3 Webhook system for integrations
**Backend (new):**
- `src/datapulse/core/webhooks.py` — outbound webhook dispatcher:
  ```python
  class WebhookDispatcher:
      async def dispatch(self, tenant_id, event_type, payload):
          """Send event to all registered webhook URLs for this tenant"""
  ```
- New migration `039_create_webhook_configs.sql`
- Events: `pipeline.completed`, `anomaly.detected`, `target.achieved`, `report.sent`
- API: CRUD for webhook registrations at `/api/v1/webhooks`

**Frontend (new):**
- Webhook management page in settings (URL, events, secret, test button)

**Risk:** MEDIUM
**Est:** 4h

### T6 Verification
```bash
# Embed dashboard
curl localhost:8000/embed/{token}/dashboard | jq .
# API docs accessible
curl localhost:8000/docs  # returns OpenAPI HTML
# Webhook delivery
curl -X POST localhost:8000/api/v1/webhooks/test
```

---

## Dependencies Map

```
T1 (Revenue Engine)  ──→ T4 (Connectors)
         │                      │
         └──→ T5 (Onboarding)  │
                                │
T2 (Arabic/RTL)  ──→ T3 (NL Query Arabic support)
                                │
T6 (Embed + API)  ←── T1 (plan enforcement for API keys)
```

- **T1** first (no revenue = no business)
- **T2** parallel with T1 (pure frontend, independent)
- **T3** after T2 (Arabic NL support needs locale infrastructure)
- **T4** after T1 (connectors need plan enforcement)
- **T5** after T1 (onboarding leads to signup)
- **T6** after T1 (API keys need billing/plan enforcement)

---

## Competitive Positioning After Market Strike

| Feature | Before | After | vs Competitors |
|---------|--------|-------|----------------|
| Revenue model | None (internal tool) | Stripe billing, 3 tiers | Matches all |
| Arabic/RTL | None | Full RTL + Arabic UI + Arabic numbers | **Only analytics platform with Arabic** |
| NL "ask a question" | None | AI-powered, EN + AR | Matches Zoho Zia, Power BI Copilot |
| Data connectors | Excel/CSV only | + Google Sheets, MySQL/PostgreSQL | Approaching Metabase (20+) |
| Signup → value | No signup flow | Guided 3-step onboarding | Matches Zoho, Metabase |
| Team management | Backend only | Full invite/role/sector UI | Matches all |
| Embedded analytics | Token + query only | Full dashboard embedding | Approaching Sisense, Zoho |
| Plan enforcement | Plans defined, never checked | Feature gates + usage limits | Standard SaaS |
| Public API | Swagger behind auth | Public docs + webhook events | Matches Metabase, Zoho |

### What Makes DataPulse Win in MENA:
1. **Arabic-first analytics** — nobody else does this
2. **Pharmacy/retail domain expertise** — pre-built dbt models for drug sales, RFM, churn
3. **Ask questions in Arabic** — "ايه أكتر منتج مبيعاً الشهر ده؟"
4. **Affordable** — $49/mo vs Power BI $14/user × 5 users = $70/mo (and Power BI doesn't do Arabic)

---

## What We're NOT Building (deferred)

| Item | Why | When |
|------|-----|------|
| Drag-drop dashboard builder | Complex UI framework, 20+ days | Phase 7 |
| Shopify/POS connectors | Needs OAuth + API partnership | Phase 6 expansion |
| Collaboration (comments, sharing) | Lower priority than revenue | Phase 9 |
| Mobile push notifications | Needs Firebase, separate infrastructure | Phase 10 |
| Custom roles | Fixed 4 roles sufficient for launch | Post-launch |
| Reseller portal + payouts | B2B growth channel, not launch-critical | 3 months post-launch |

---

## All Plans in Repo

```
plans/
├── dragon-roar.md       — ~95% complete (data integrity audit)
├── iron-curtain.md      — Ready (hardening, 6 tiers, ~49h)
├── unlock-the-vault.md  — Ready (activate dead features, 6 tiers, ~55h)
└── market-strike.md     — Ready (competitive features, 6 tiers, ~70h)
```

**Execution order:**
1. Iron Curtain (security + quality) — 2 weeks
2. Unlock the Vault (activate existing code) — 2 weeks
3. Market Strike (competitive features) — 3 weeks
4. **Launch** 🚀
