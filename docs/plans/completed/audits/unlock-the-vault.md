# Unlock the Vault — Activate What's Already Built

**Date:** 2026-04-09 | **Codebase:** DataPulse SaaS
**Scope:** 6 Tiers, ~55 hours | **Goal:** Activate dead features, surface hidden analytics, wire disconnected modules
**Philosophy:** Build NOTHING from scratch. Every tier unlocks value from code that ALREADY EXISTS.

---

## Context

A deep graph analysis (`dp_context`, `dp_impact`, `dp_query`) revealed a striking pattern: DataPulse has **massive computation debt**. The dbt gold layer computes 12 feature models every pipeline run, but **5 of them have ZERO callers** — no API endpoint reads them, no frontend displays them, no user has ever seen the data. Meanwhile, 4 backend services (`ScenarioService`, `ViewsService`, `ScheduleRepository`, `NotificationService`) are fully coded with database tables, CRUD APIs, and business logic — but either have no frontend UI or are missing a critical delivery layer (email).

This plan surfaces all that hidden value. No new algorithms, no new database schemas, no new frameworks. Just wiring.

---

## Graph Evidence (dp_context queries)

| Symbol | Callers | Imports | Tests | Status |
|--------|---------|---------|-------|--------|
| `feat_product_lifecycle` | 0 | 0 | 0 | DEAD — computed every dbt run, read by nobody |
| `feat_revenue_daily_rolling` | 0 | 0 | 0 | DEAD — 7/30/90-day MAs, volatility, trend ratios |
| `feat_revenue_site_rolling` | 0 | 0 | 0 | DEAD — site-level rolling analytics |
| `feat_seasonality_daily` | 0 | 0 | 0 | DEAD — seasonal pattern detection |
| `feat_seasonality_monthly` | 0 | 0 | 0 | DEAD — monthly seasonal decomposition |
| `ScenarioService` | 0 | 0 | 0 | ORPHAN — service class exists, never imported |
| `ViewsService` | 0 | 0 | 0 | ORPHAN — CRUD complete, no frontend |
| `ScheduleRepository` | 0 | 0 | 0 | ORPHAN — DB table + CRUD, no executor |

**Total wasted dbt compute per pipeline run:** 5 feature models = ~2-3 min of SQL computation generating data nobody sees.

---

## T1: Surface Hidden Gold (Product Lifecycle + Rolling Analytics)
**Priority:** P0 — Highest ROI, zero backend changes needed | **Est:** ~10 hours
**Dependencies:** None

The dbt models already compute the data. We just need: repository method → service method → API route → frontend hook → UI component.

### T1.1 Expose Product Lifecycle classification
**What exists:** `dbt/models/marts/features/feat_product_lifecycle.sql` computes: `lifecycle_phase` (Growth/Mature/Decline/Dormant), `avg_recent_growth`, `quarters_active`, `total_lifetime_revenue`, `total_lifetime_quantity`, `first_sale_quarter`, `last_sale_quarter`.

**Backend (new):**
- `src/datapulse/analytics/lifecycle_repository.py` — new file (~60 lines):
  ```python
  class LifecycleRepository:
      def get_lifecycle_summary(self, session) -> list[dict]:
          """SELECT lifecycle_phase, COUNT(*) as product_count, 
                    SUM(total_lifetime_revenue) as phase_revenue
             FROM public_marts.feat_product_lifecycle
             GROUP BY lifecycle_phase"""
      
      def get_products_by_phase(self, session, phase: str, limit: int = 20) -> list[dict]:
          """Products in a specific lifecycle phase, sorted by revenue"""
  ```
- `src/datapulse/analytics/service.py` — add 2 methods: `get_lifecycle_summary()`, `get_lifecycle_by_phase(phase)`
- `src/datapulse/api/routes/analytics.py` — add 2 endpoints:
  - `GET /api/v1/analytics/product-lifecycle` → lifecycle phase distribution
  - `GET /api/v1/analytics/product-lifecycle/{phase}` → products in that phase
- `src/datapulse/api/deps.py` — wire `LifecycleRepository` into `get_analytics_service`

**Frontend (new):**
- `frontend/src/hooks/use-product-lifecycle.ts` — SWR hook for lifecycle data
- `frontend/src/components/products/lifecycle-chart.tsx` — Recharts stacked bar (phases) + table of products per phase
- Wire into ProductsPage (`frontend/src/app/(app)/products/page.tsx`)

**Risk:** LOW — read-only queries on existing materialized table
**Est:** 4h

### T1.2 Expose Rolling Revenue Analytics (trend strength indicators)
**What exists:** `feat_revenue_daily_rolling` computes: `ma_7d_revenue`, `ma_30d_revenue`, `ma_90d_revenue`, `volatility_30d`, `trend_ratio_7d_30d`, `trend_ratio_30d_90d`, `deviation_from_ma30`, `same_day_last_week`, `same_day_last_year`.

**Backend (new):**
- `src/datapulse/analytics/rolling_repository.py` — new file (~80 lines):
  ```python
  class RollingRepository:
      def get_trend_strength(self, session, days: int = 30) -> dict:
          """Latest trend ratios, volatility, deviation from moving averages"""
      
      def get_rolling_series(self, session, start_date, end_date) -> list[dict]:
          """Time series of rolling MAs for chart overlay"""
  ```
- `src/datapulse/api/routes/analytics.py` — add:
  - `GET /api/v1/analytics/trend-strength` → current trend indicators
  - `GET /api/v1/analytics/rolling-averages` → time series for chart overlay

**Frontend (new):**
- `frontend/src/hooks/use-trend-strength.ts` — SWR hook
- `frontend/src/components/dashboard/trend-strength-card.tsx` — compact card showing:
  - 7d vs 30d trend ratio (accelerating / decelerating / stable)
  - 30d volatility (calm / normal / volatile)
  - Deviation from 30-day MA (above / below / on track)
- Add to dashboard page as a new card alongside KPI grid

**Risk:** LOW
**Est:** 3h

### T1.3 Expose Seasonality Patterns
**What exists:** `feat_seasonality_daily` + `feat_seasonality_monthly` compute seasonal patterns.

**Backend (new):**
- `src/datapulse/analytics/seasonality_repository.py` — new file:
  - `get_daily_pattern()` → average revenue by day of week (Mon-Sun)
  - `get_monthly_pattern()` → average revenue by month (Jan-Dec) with seasonal index
- API: `GET /api/v1/analytics/seasonality/daily`, `GET /api/v1/analytics/seasonality/monthly`

**Frontend (new):**
- `frontend/src/hooks/use-seasonality.ts`
- `frontend/src/components/dashboard/seasonality-card.tsx` — small heatmap showing which days/months are peak, with "best day" and "worst day" callout
- Add to InsightsPage (`frontend/src/app/(app)/insights/page.tsx`)

**Risk:** LOW
**Est:** 3h

### T1 Verification
```bash
# Backend tests
pytest tests/test_lifecycle_repository.py tests/test_rolling_repository.py tests/test_seasonality_repository.py
# API smoke test
curl localhost:8000/api/v1/analytics/product-lifecycle | jq .
curl localhost:8000/api/v1/analytics/trend-strength | jq .
curl localhost:8000/api/v1/analytics/seasonality/daily | jq .
# Frontend
npm run build && npx tsc --noEmit
```

---

## T2: Wire Disconnected Services (Views + Scenarios + Explore)
**Priority:** P0 — Features are built, just needs UI | **Est:** ~8 hours
**Dependencies:** None

### T2.1 Add "Save View" UI for saved filter views
**What exists:** `ViewsService` has full CRUD. DB table `public.saved_views` with RLS. API routes at `/api/v1/views`. Max 20 views per user. Fields: `name`, `filters` (JSONB), `is_default`, `created_at`.

**Frontend (new):**
- `frontend/src/hooks/use-saved-views.ts` — SWR hook for CRUD on `/api/v1/views`
- `frontend/src/components/filters/save-view-dialog.tsx` — modal dialog (name input + save button), triggered from filter bar
- `frontend/src/components/filters/view-switcher.tsx` — dropdown in filter bar to load saved views
- Wire into `frontend/src/contexts/filter-context.tsx`:
  - On "load view": set all filters from saved JSONB
  - On "save view": serialize current filters to JSONB and POST
- Add "Set as default" toggle that auto-loads on page visit

**Backend changes:** None — already complete.
**Risk:** LOW — purely additive frontend feature
**Est:** 3h

### T2.2 Add Scenario History (save + compare)
**What exists:** `ScenarioService` computes price/volume/cost adjustments with elasticity modeling. `ScenarioRepository` has CRUD for persistence. API route at `POST /api/v1/scenarios/simulate`.

**What's missing:** No save endpoint, no history list, no comparison.

**Backend (new):**
- `src/datapulse/api/routes/scenarios.py` — add:
  - `POST /api/v1/scenarios/save` — persist simulation result with name
  - `GET /api/v1/scenarios/history` — list saved scenarios
  - `GET /api/v1/scenarios/{id}` — load specific saved scenario
  - `DELETE /api/v1/scenarios/{id}` — delete saved scenario
- `src/datapulse/scenarios/repository.py` — verify `save()`, `list()`, `get_by_id()`, `delete()` methods exist (they do)
- Wire `ScenarioService` + `ScenarioRepository` into `deps.py`

**Frontend (new):**
- `frontend/src/hooks/use-scenario-history.ts`
- `frontend/src/components/scenarios/scenario-history-panel.tsx` — sidebar list of saved scenarios with load/delete
- `frontend/src/components/scenarios/scenario-compare.tsx` — side-by-side view of 2 scenarios
- Add "Save This Scenario" button to existing ScenariosPage

**Risk:** MEDIUM — ScenarioService is orphaned, needs integration testing
**Est:** 3h

### T2.3 Add Saved Queries to Explore
**What exists:** `sql_builder.py` generates parameterized SQL from explore queries. Full query execution with `POST /api/v1/explore/query`. No persistence.

**Backend (new):**
- New migration `036_create_saved_queries.sql`:
  ```sql
  CREATE TABLE IF NOT EXISTS public.saved_queries (
      id SERIAL PRIMARY KEY,
      tenant_id INT NOT NULL REFERENCES bronze.tenants(tenant_id),
      user_id TEXT NOT NULL,
      name TEXT NOT NULL,
      description TEXT DEFAULT '',
      query_config JSONB NOT NULL,  -- {model, dimensions, metrics, filters, order_by, limit}
      created_at TIMESTAMPTZ DEFAULT now(),
      updated_at TIMESTAMPTZ DEFAULT now(),
      UNIQUE(tenant_id, user_id, name)
  );
  ALTER TABLE public.saved_queries ENABLE ROW LEVEL SECURITY;
  ALTER TABLE public.saved_queries FORCE ROW LEVEL SECURITY;
  ```
- `src/datapulse/explore/saved_queries_repository.py` — CRUD
- `src/datapulse/api/routes/explore.py` — add:
  - `GET /api/v1/explore/saved` — list saved queries
  - `POST /api/v1/explore/saved` — save a query
  - `DELETE /api/v1/explore/saved/{id}` — delete

**Frontend (new):**
- `frontend/src/hooks/use-saved-queries.ts`
- `frontend/src/components/custom-report/saved-queries-panel.tsx` — sidebar panel in CustomReportPage
- Add "Save Query" button and "Load Saved" dropdown to report builder

**Risk:** LOW — new table + read-only pattern
**Est:** 2h

### T2 Verification
```bash
# Test saved views
curl -X POST localhost:8000/api/v1/views -d '{"name":"My View","filters":{"brand":"Aspirin"}}'
# Test scenario save
curl -X POST localhost:8000/api/v1/scenarios/save -d '{"name":"Price +10%","result":{...}}'
# Test saved queries
curl -X POST localhost:8000/api/v1/explore/saved -d '{"name":"Top Products","query_config":{...}}'
# Frontend builds
npm run build
```

---

## T3: Report Email Delivery (the biggest missing piece)
**Priority:** P0 — Reports infrastructure 90% built, delivery 0% built | **Est:** ~12 hours
**Dependencies:** None

### T3.1 Build email service
**What exists:** `notifications.py` already sends to Slack via `httpx.post()`. Same pattern for email.

**Backend (new):**
- `src/datapulse/core/email.py` — new module (~100 lines):
  ```python
  class EmailService:
      def __init__(self, settings: Settings):
          self.smtp_host = settings.smtp_host
          self.smtp_port = settings.smtp_port
          self.smtp_user = settings.smtp_user
          self.smtp_password = settings.smtp_password
          self.from_email = settings.from_email
      
      async def send(self, to: list[str], subject: str, html: str, attachments: list[Path] = []):
          """Send email via SMTP (aiosmtplib)"""
  ```
- `src/datapulse/core/config.py` — add Settings fields:
  ```python
  smtp_host: str = ""
  smtp_port: int = 587
  smtp_user: str = ""
  smtp_password: str = ""
  from_email: str = "reports@smartdatapulse.tech"
  ```
- Install: `aiosmtplib` (async SMTP client)
**Risk:** MEDIUM — new external dependency
**Est:** 3h

### T3.2 Build report execution scheduler
**What exists:** `ScheduleRepository` has CRUD. `report_schedules` table has `cron_expression`, `enabled`, `recipients` (JSONB), `template_id`. `template_engine.py` renders SQL → data → PDF.

**Backend (new):**
- `src/datapulse/reports/executor.py` — new module (~120 lines):
  ```python
  class ReportExecutor:
      def __init__(self, session, email_service, template_engine):
          pass
      
      async def run_due_schedules(self):
          """Called by scheduler every minute:
          1. Query enabled schedules where cron matches current time
          2. For each: render template → generate PDF → email to recipients
          3. Update last_sent_at and next_run_at
          """
  ```
- `src/datapulse/scheduler.py` — add job:
  ```python
  scheduler.add_job(report_executor.run_due_schedules, 'interval', minutes=1, id='report_delivery')
  ```
- Add `last_sent_at TIMESTAMPTZ` and `last_error TEXT` columns to `report_schedules` table (new migration)

**Risk:** MEDIUM — scheduler integration, email delivery can fail
**Est:** 4h

### T3.3 Build report schedule management UI
**What exists:** API routes at `/api/v1/report-schedules` (CRUD). No frontend.

**Frontend (new):**
- `frontend/src/hooks/use-report-schedules.ts` — SWR hook for schedule CRUD
- `frontend/src/components/reports/schedule-form.tsx` — form: template selector, cron expression builder (daily/weekly/monthly presets), recipient email list, enable/disable toggle
- `frontend/src/components/reports/schedule-list.tsx` — list of schedules with status (last sent, next run, errors)
- Wire into SchedulesPage (`frontend/src/app/(app)/reports/schedules/page.tsx`) — page already exists, just empty

**Risk:** LOW
**Est:** 3h

### T3.4 Add "Email This Report" one-shot button
**Backend (new):**
- `POST /api/v1/reports/{template_id}/email` — render + email immediately (no schedule)
- Reuses `template_engine.py` + `email.py`

**Frontend:**
- Add "Email Report" button to ReportsPage next to "Download PDF"

**Risk:** LOW
**Est:** 2h

### T3 Verification
```bash
# Test email service (dev mode → log to console, no real SMTP)
pytest tests/test_email_service.py
# Test schedule execution
pytest tests/test_report_executor.py
# Test one-shot email
curl -X POST localhost:8000/api/v1/reports/monthly-overview/email -d '{"recipients":["test@example.com"]}'
# Frontend
npm run build
```

---

## T4: Comparison Presets + Period Intelligence
**Priority:** P1 — Backend supports it, UI doesn't offer shortcuts | **Est:** ~6 hours
**Dependencies:** T1 (rolling analytics provide context)

### T4.1 Add WoW / MoM / YoY quick-select presets
**What exists:** `useComparison()` hook already accepts arbitrary date ranges. `ComparisonRepository.get_top_movers()` computes period deltas. The backend handles any `(start_date, end_date)` pair.

**Frontend (new):**
- `frontend/src/components/comparison/preset-buttons.tsx` — row of buttons:
  - "vs Last Week" → auto-compute `{current: last 7 days, previous: 7 days before that}`
  - "vs Last Month" → auto-compute `{current: last 30 days, previous: 30 days before that}`
  - "vs Same Period Last Year" → auto-compute `{current: last 30 days, previous: same 30 days last year}`
  - "Custom" → existing date range picker
- Wire into the filter bar on DashboardPage
- When a preset is selected, ALL charts on the page show comparison overlays

**Backend changes:** None — already supports arbitrary date ranges.

**Frontend (modify):**
- `frontend/src/contexts/filter-context.tsx` — add `comparisonPreset` state (none/wow/mom/yoy/custom)
- `frontend/src/hooks/use-comparison-trend.ts` — read comparison preset from context, auto-compute date ranges
- `frontend/src/components/dashboard/daily-trend-chart.tsx` — show comparison series as dashed line overlay when comparison active
- `frontend/src/components/dashboard/monthly-trend-chart.tsx` — same

**Risk:** MEDIUM — touches multiple chart components
**Est:** 4h

### T4.2 Add "This vs That" comparison mode to detail pages
**What exists:** Product, Customer, Staff detail pages show single-entity analytics. `ComparisonRepository` can compare arbitrary entities.

**Frontend (new):**
- Add "Compare with..." button on ProductDetailPage, CustomerDetailPage, StaffDetailPage
- Opens entity picker → side-by-side comparison view
- Reuses existing detail hooks with 2 different keys

**Backend changes:** None — detail endpoints already accept entity keys.
**Risk:** MEDIUM
**Est:** 2h

### T4 Verification
```bash
# Test comparison presets
npm run build
npx vitest run
# Manual: select "vs Last Month" → all charts show overlay
```

---

## T5: Embed + Notification Completeness
**Priority:** P1 — Existing infrastructure, just needs activation | **Est:** ~7 hours
**Dependencies:** None

### T5.1 Build embed token generator UI
**What exists:** `POST /api/v1/embed/token` generates JWT tokens. `GET /embed/{token}` serves embedded view. Token scoped to tenant + resource. Configurable TTL (1-72h).

**Frontend (new):**
- `frontend/src/components/embed/embed-generator.tsx` — modal dialog:
  - Resource type selector (chart/dashboard/report)
  - TTL selector (1h/8h/24h/72h)
  - "Generate" button → calls `POST /api/v1/embed/token`
  - Display: embed URL + HTML iframe snippet + copy-to-clipboard
  - Preview panel showing the embedded view
- Add "Embed" button to dashboard page and chart cards (kebab menu)

**Backend changes:** None — API exists.
**Risk:** LOW
**Est:** 3h

### T5.2 Wire notification triggers into business events
**What exists:** `NotificationService` has `create()`, `list()`, `mark_read()`, `mark_all_read()`. SSE stream at `/notifications/stream`. Frontend bell icon + center panel. DB table + RLS.

**What's missing:** Nothing CREATES notifications. No module calls `NotificationService.create()`.

**Backend (modify):**
- `src/datapulse/pipeline/executor.py` — after pipeline completion:
  ```python
  notification_service.create(tenant_id, type="pipeline", title="Pipeline Complete", 
      message=f"Pipeline run {run_id} completed in {duration}s", link="/quality")
  ```
- `src/datapulse/anomalies/service.py` — after anomaly detection:
  ```python
  notification_service.create(tenant_id, type="anomaly", title=f"Anomaly Detected: {metric}",
      message=f"{metric} deviated by {deviation}% from expected", link="/alerts")
  ```
- `src/datapulse/targets/repository.py` — when target achievement crosses threshold:
  ```python
  notification_service.create(tenant_id, type="target", title=f"Target {pct}% achieved",
      message=f"{target_name} reached {pct}% of goal", link="/goals")
  ```
- `src/datapulse/reports/executor.py` (from T3.2) — after report delivery:
  ```python
  notification_service.create(tenant_id, type="report", title=f"Report Sent",
      message=f"{template_name} sent to {len(recipients)} recipients", link="/reports")
  ```

**Risk:** LOW — additive, each trigger is 3 lines
**Est:** 2h

### T5.3 Add notification preferences
**Backend (new):**
- New migration `037_notification_preferences.sql`:
  ```sql
  CREATE TABLE IF NOT EXISTS public.notification_preferences (
      id SERIAL PRIMARY KEY,
      tenant_id INT NOT NULL,
      user_id TEXT NOT NULL,
      type TEXT NOT NULL,  -- pipeline, anomaly, target, report
      enabled BOOLEAN DEFAULT true,
      UNIQUE(tenant_id, user_id, type)
  );
  ```
- `src/datapulse/notifications_center/service.py` — check preferences before creating notification
- `GET /api/v1/notifications/preferences` and `PUT /api/v1/notifications/preferences`

**Frontend (new):**
- `frontend/src/components/notifications/preferences-panel.tsx` — toggles for each notification type
- Wire into notification center dropdown (gear icon)

**Risk:** LOW
**Est:** 2h

### T5 Verification
```bash
# Test notification triggers
pytest tests/test_notification_triggers.py
# Test embed token
curl -X POST localhost:8000/api/v1/embed/token -d '{"resource_type":"dashboard","ttl_hours":8}'
# Frontend
npm run build
```

---

## T6: AI Depth (Explanations + Root Cause)
**Priority:** P2 — Augments existing AI-Light module | **Est:** ~12 hours
**Dependencies:** T1 (rolling analytics feed context to AI)

### T6.1 Add anomaly root cause analysis
**What exists:** `ai_light/service.py` detects anomalies (>2sigma deviations). `diagnostics.py` has `get_why_changed()` which does waterfall decomposition by dimension. But they're not connected.

**Backend (modify):**
- `src/datapulse/ai_light/service.py` — add method `explain_anomaly(metric, date_range)`:
  1. Call `diagnostics.get_why_changed()` to get dimension-level breakdown
  2. Call rolling analytics (T1.2) to get trend context
  3. Build prompt: "Revenue dropped 15%. Top contributors: Customer X (-30%), Product Y (-20%). 7d MA trend was declining since [date]. Explain why."
  4. Return: AI narrative + structured data (contributors, trend, seasonality context)

**Frontend (modify):**
- `frontend/src/components/alerts/anomaly-detail-drawer.tsx` — new: click an anomaly → drawer opens with root cause explanation, waterfall chart of contributors, trend overlay

**Risk:** MEDIUM — AI prompt engineering, OpenRouter cost
**Est:** 4h

### T6.2 Add forecast explanation
**What exists:** Forecasting computes predictions but returns numbers only. No "why is revenue forecasted to grow 12%?" narrative.

**Backend (modify):**
- `src/datapulse/ai_light/service.py` — add method `explain_forecast(forecast_data)`:
  1. Get seasonality patterns (T1.3) for context
  2. Get trend strength (T1.2) for momentum
  3. Build prompt: "Revenue forecast for next 3 months: [values]. Seasonal pattern: [pattern]. Current trend: [accelerating/stable]. Historical accuracy: [MAPE]. Explain the forecast."
  4. Return: AI narrative + confidence assessment

**Frontend (modify):**
- `frontend/src/components/dashboard/forecast-card.tsx` — add "Why this forecast?" expandable section with AI explanation

**Risk:** MEDIUM
**Est:** 3h

### T6.3 Add AI cost tracking
**What exists:** `ai_light/client.py` calls OpenRouter. No usage tracking.

**Backend (new):**
- `src/datapulse/ai_light/usage.py` — track each API call:
  ```python
  async def track_usage(tenant_id, model, prompt_tokens, completion_tokens, cost_usd):
      """Insert into ai_usage_log table"""
  ```
- New migration `038_create_ai_usage_log.sql`
- API: `GET /api/v1/ai-light/usage` → usage summary by day/month

**Frontend (new):**
- Add usage counter to InsightsPage: "AI calls this month: 47 | Est. cost: $0.12"
- Add to billing page if billing module is active

**Risk:** LOW
**Est:** 2h

### T6.4 Add regenerate + feedback loop
**Frontend (modify):**
- All AI-generated content (summary card, anomaly explanations, forecast explanations): add:
  - "Regenerate" button → re-call API with same context
  - "Thumbs up / Thumbs down" → `POST /api/v1/ai-light/feedback`
- Store feedback in DB for future prompt improvement

**Backend (new):**
- `POST /api/v1/ai-light/feedback` — save `{content_type, content_id, rating, comment}`
- New table `ai_feedback` (lightweight)

**Risk:** LOW
**Est:** 3h

### T6 Verification
```bash
# Test anomaly explanation
curl localhost:8000/api/v1/ai-light/anomalies?explain=true | jq .
# Test forecast explanation  
curl localhost:8000/api/v1/ai-light/forecast-explanation | jq .
# Test usage tracking
curl localhost:8000/api/v1/ai-light/usage | jq .
# Frontend
npm run build
```

---

## Dependencies Map

```
T1 (Surface Hidden Gold)  ─────────────────┐
                                            ├──→ T6 (AI Depth)
T2 (Wire Disconnected Services)             │
                                            │
T3 (Report Email Delivery)  ──→ T5.2 (Notification triggers)
                                            │
T4 (Comparison Presets)  ←── T1 (rolling)   │
                                            │
T5 (Embed + Notifications) ────────────────┘
```

- **T1, T2, T3, T5** can proceed in parallel
- **T4** depends on T1 (rolling analytics provide trend context for comparisons)
- **T6** depends on T1 (seasonality + rolling data feed AI prompts)
- **T5.2** depends on T3.2 (report executor creates notification triggers)

---

## Impact Summary

| Tier | New API Endpoints | New Frontend Components | Lines of Code | User Value |
|------|-------------------|------------------------|---------------|------------|
| T1 | 7 | 5 | ~500 | Users finally see product lifecycle, trend strength, seasonality |
| T2 | 5 | 7 | ~400 | Save views, save queries, save scenarios — stop repeating work |
| T3 | 3 | 4 | ~600 | Reports actually arrive in email — the #1 missing delivery mechanism |
| T4 | 0 | 4 | ~300 | One-click WoW/MoM/YoY comparisons across entire dashboard |
| T5 | 3 | 4 | ~350 | Embed dashboards externally, get notified when things happen |
| T6 | 4 | 3 | ~500 | AI explains WHY revenue dropped, WHY forecast predicts growth |

**Total: 22 new endpoints, 27 new components, ~2,650 lines**

---

## What We're NOT Building (out of scope)

| Item | Why Not |
|------|---------|
| Google Sheets connector | New data source = new bronze ingestion code, not "unlocking" existing value |
| Stripe billing integration | Revenue infrastructure, not analytics activation |
| Dashboard drag-drop builder | Complex UI framework, deferred to Phase 7 |
| Multi-language AI (Arabic) | Prompt engineering + i18n, deferred to Phase 8 |
| Mobile push notifications | Requires native push service (Firebase), beyond current SSE |
| Kubernetes / S3 / Celery | Infrastructure scaling, deferred to Phase 10 |
