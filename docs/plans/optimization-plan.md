# DataPulse — Analytics Optimization Plan

> Merged from external analytics review + DataPulse-specific optimizations.
> Status: **PLANNED** — awaiting approval before implementation.

---

## Problem Statement

The biggest trust issue in the current analytics layer is not lack of features — it's the **semantic mismatch** where some fields are labeled as gross while the query logic uses net amounts. Fixing that first improves product credibility immediately.

Beyond naming, the platform has **underused dimensions** (billing, governorate, product lifecycle) and **missing cross-dimensional analysis** that would differentiate DataPulse from generic dashboards.

---

## Phase 0: Dashboard Visibility Fixes (URGENT)

**Must fix before optimization work begins.**

### Issue 1: c086 data not showing on dashboard

Despite dbt rebuild completing successfully (all models passed), c086 site data doesn't appear.

**Root cause investigation**:
- All bronze data loads with `tenant_id=1` (hardcoded default in migration 003)
- RLS filters by `SET LOCAL app.tenant_id` derived from JWT claims
- If JWT missing tenant claim → falls back to `default_tenant_id="1"`
- Need to verify: c086 rows exist in stg_sales, dim_site has c086, fct_sales joins succeed

**Debug queries**:
```sql
SELECT DISTINCT site_code FROM public_staging.stg_sales WHERE site_code LIKE '%c086%';
SELECT * FROM public_marts.dim_site;
SELECT site_key, COUNT(*) FROM public_marts.fct_sales GROUP BY site_key;
```

**Files**: `src/datapulse/bronze/loader.py`, `dbt/models/marts/dims/dim_site.sql`, `src/datapulse/api/deps.py`

### Issue 2: 4 dashboard sections not appearing

Revenue Forecast, Target vs Actual, Revenue Heatmap, and Site Locations exist in code but don't render.

**Causes**:
1. **LazySection** wraps all 4 — only renders when scrolled into viewport (IntersectionObserver)
2. **API endpoints returning empty/error** — each component shows empty state or skeleton on failure
3. **Dynamic imports with `ssr: false`** — client-only rendering

| Section | Component | API Endpoint | Empty State |
|---------|-----------|-------------|-------------|
| Revenue Forecast | ForecastCard | `/api/v1/forecasting/summary` | "No forecast data available" |
| Target vs Actual | TargetProgress | `/api/v1/targets/summary` | "No targets configured" |
| Revenue Heatmap | CalendarHeatmap | `/api/v1/analytics/heatmap` | Loading skeleton |
| Site Locations | EgyptMap | `/api/v1/analytics/sites` | Empty list |

**Fix approach**:
1. Verify each API endpoint returns data
2. Fix any failing endpoints
3. Review LazySection threshold — consider removing lazy wrapper for critical sections
4. Add visible error states instead of silent hiding

**Files**: `frontend/src/app/(app)/dashboard/page.tsx`, `frontend/src/components/dashboard/lazy-section.tsx`, API route files for each endpoint

---

## Phase A: Naming & Semantic Fix

**Priority**: CRITICAL — do this before any new features.

| Task | Where | Details |
|------|-------|---------|
| Audit `metrics_summary` dbt model | `dbt/models/marts/aggs/metrics_summary.sql` | Verify if `total_revenue` is gross or net |
| Audit `KpiSummary` Pydantic model | `src/datapulse/analytics/models.py` | Align field names with actual SQL logic |
| Rename ambiguous fields | dbt + Python + TypeScript | `revenue` → `gross_sales` or `net_sales` explicitly |
| Update frontend KPI labels | `frontend/src/components/dashboard/kpi-grid.tsx` | Match backend naming |
| Update API response types | `frontend/src/types/api.ts` | Sync with new field names |

**Files touched**:
- `dbt/models/marts/aggs/metrics_summary.sql`
- `src/datapulse/analytics/models.py`
- `src/datapulse/analytics/repository.py`
- `frontend/src/types/api.ts`
- `frontend/src/components/dashboard/kpi-grid.tsx`
- `frontend/src/hooks/use-summary.ts`

---

## Phase B: Core Financial KPIs

**Priority**: HIGH — foundational metrics every user expects.

### New KPIs (derived from existing `fct_sales` columns)

| KPI | Formula | Source Columns |
|-----|---------|---------------|
| `gross_sales` | `SUM(total_amount)` | `fct_sales.total_amount` |
| `discount_value` | `SUM(discount)` | `fct_sales.discount` |
| `discount_rate` | `discount_value / gross_sales` | Derived |
| `net_sales` | `gross_sales - discount_value` | Derived |
| `returns_value` | `SUM(return_amount)` | `fct_sales.return_amount` |
| `return_adjusted_revenue` | `net_sales - returns_value` | Derived |
| `returns_impact_pct` | `returns_value / net_sales` | Derived |

### Additional KPIs

| KPI | Formula | Notes |
|-----|---------|-------|
| Average Order Value | `net_sales / transaction_count` | Already partially exists |
| Average Basket Size | `item_count / transaction_count` | Need to verify column |
| Transactions | `COUNT(DISTINCT invoice_no)` | Exists, rename for clarity |
| Revenue by payment method | `SUM(net_sales) GROUP BY payment_method` | Uses `dim_billing` (currently unused) |

### UX Optimization: KPI Layers (not KPI explosion)

Instead of showing 15+ cards at once:

```
Level 1 — Hero KPIs (always visible, 4 cards):
  Net Sales | Gross Sales | Discount Rate | Return Rate

Level 2 — Expandable detail (click to expand):
  Discount Value | Returns Value | Return-Adjusted Revenue
  Transactions | AOV | Basket Size

Level 3 — Drill-down page (click KPI → dedicated view):
  Full breakdown by product/site/staff/customer
```

Uses existing `lazy-section` component for progressive disclosure.

**Files touched**:
- `dbt/models/marts/aggs/metrics_summary.sql`
- `src/datapulse/analytics/models.py`
- `src/datapulse/analytics/repository.py`
- `src/datapulse/analytics/service.py`
- `frontend/src/components/dashboard/kpi-grid.tsx`
- `frontend/src/components/dashboard/kpi-card.tsx`

---

## Phase C: Target & Forecast Pacing

**Priority**: HIGH — connects two existing features (forecasting + targets) that currently live in isolation.

### New Metrics

| Metric | Formula | Notes |
|--------|---------|-------|
| `forecast_vs_target_gap` | `forecasted_revenue - target` | Merge forecast + target services |
| `required_run_rate` | `(target - actual_ytd) / remaining_days` | Daily pace needed |
| `pacing_status` | Based on confidence bands | `on_track` / `at_risk` / `off_track` |
| `forecast_driver_attribution` | Decompose forecast by branch + category | "Cairo +12%, OTC pharma -3%" |
| `revenue_weighted_anomaly_severity` | `anomaly_score × revenue_share` | Business impact, not just stats |

### Pacing Status Logic

```
on_track:  forecasted_revenue >= target × 0.95
at_risk:   forecasted_revenue >= target × 0.80 AND < target × 0.95
off_track: forecasted_revenue < target × 0.80
```

**Files touched**:
- `src/datapulse/forecasting/service.py`
- `src/datapulse/forecasting/repository.py`
- `src/datapulse/targets/models.py`
- `src/datapulse/anomalies/service.py`
- `frontend/src/components/dashboard/forecast-card.tsx`
- `frontend/src/components/goals/goals-overview.tsx`

---

## Phase D: Growth Decomposition & Advanced Analytics

**Priority**: MEDIUM — differentiates DataPulse from basic dashboards.

### Contribution Analysis

| Analysis | Description |
|----------|-------------|
| Contribution to growth by product | Which products drove the revenue change |
| Contribution to growth by site | Which branches drove the revenue change |
| Contribution to growth by customer segment | Which segments drove the revenue change |
| Cross-dimensional: product × site | Growth matrix — which combos are winning/losing |
| Cross-dimensional: customer × product | Churn matrix — which customers stopped buying what |

### Customer Analytics Extensions

| Metric | Description |
|--------|-------------|
| New vs returning revenue | Revenue split by customer type |
| Repeat purchase rate | Customers with >1 purchase / total customers |
| Cohort retention by acquisition month | Monthly retention curves |
| Churn-risk scoring | Based on recency + frequency decline |
| Segment profitability | Revenue per segment, not just count |
| Segment return behavior | Return rate by customer segment |

### Staff Analytics Extensions

| Metric | Description |
|--------|-------------|
| Revenue per active day | Staff efficiency ratio |
| Consistency score | Std dev of daily sales (lower = more reliable) |
| Target attainment by staff | % of target reached per staff member |
| Return rate per staff | Quality indicator |

### Product Analytics Extensions

| Metric | Description |
|--------|-------------|
| Product lifecycle ↔ revenue link | Are "declining" products still significant? |
| Discount dependency by product | Products that only sell with discounts |
| Product concentration risk | Top 10 products' share of total revenue |
| Contribution to total growth | Per product contribution |

**Files touched**:
- `src/datapulse/analytics/advanced_repository.py`
- `src/datapulse/analytics/comparison_repository.py`
- `src/datapulse/analytics/models.py`
- `src/datapulse/analytics/service.py`
- `dbt/models/marts/aggs/` (new models)
- Frontend: new cards + drill-down components

---

## Phase E: Egyptian Market Intelligence

**Priority**: MEDIUM — competitive differentiator for Egyptian market.

### Governorate Analytics

| Feature | Details |
|---------|---------|
| Governorate-level aggregation | Use existing `governorate_map.sql` macro |
| Geographic heatmap KPIs | Feed Egypt map component with governorate data (component exists) |
| Regional concentration risk | Revenue dependency on specific governorates |
| Regional growth rates | Governorate-level YoY/MoM |

### Calendar Intelligence

| Feature | Details |
|---------|---------|
| Working day vs weekend comparison | Sales patterns by day type |
| Ramadan impact analysis | Revenue patterns during Islamic calendar events |
| Pay-cycle correlation | Salary week spike detection (typically 25th-5th) |
| Holiday impact | Egyptian national holidays effect on sales |

### Time Intelligence (via comparison mode, not separate KPIs)

Instead of adding DoD, WoW, MTD, YTD, 7/30/90-day as separate metrics:
- Extend existing `comparison_repository.py` + `period-picker.tsx`
- User selects comparison period from a single control
- One comparison engine, multiple period options

**Files touched**:
- `dbt/macros/governorate_map.sql` (extend)
- `dbt/models/marts/aggs/` (new governorate + calendar models)
- `src/datapulse/analytics/repository.py`
- `src/datapulse/analytics/comparison_repository.py`
- `frontend/src/components/dashboard/egypt-map.tsx`
- `frontend/src/components/comparison/period-picker.tsx`

---

## Not Applicable / Deferred

| Suggestion | Reason |
|------------|--------|
| Sell-through rate | No inventory data |
| COGS / margin metrics | No cost data |
| Same-store sales growth | Only 2 sites — limited value |
| Hourly/intraday trends | Need to verify timestamp granularity in bronze |
| Narrative AI reporting | Deferred to Phase 8 AI |

---

## Implementation Order Summary

```
Phase A ──► Phase B ──► Phase C ──► Phase D ──► Phase E
 (naming)   (KPIs)     (pacing)   (growth)    (egypt)
 ~1 day     ~2 days    ~2 days    ~3 days     ~2 days

A must complete before B (field names change)
B must complete before C (KPIs feed into pacing)
C and D can partially overlap
E is independent after B
```

## Dependency Graph

```
                    ┌──────────┐
                    │ Phase A  │
                    │ Naming   │
                    └────┬─────┘
                         │
                    ┌────▼─────┐
                    │ Phase B  │
                    │ Core KPIs│
                    └────┬─────┘
                         │
              ┌──────────┼──────────┐
              │          │          │
         ┌────▼───┐ ┌───▼────┐ ┌──▼───────┐
         │Phase C │ │Phase D │ │ Phase E  │
         │Pacing  │ │Growth  │ │ Egypt    │
         └────────┘ └────────┘ └──────────┘
```

---

## Success Criteria

- [ ] All KPI labels match their actual calculation (no gross/net confusion)
- [ ] 7 new financial KPIs available in dashboard
- [ ] Forecast vs target gap visible on goals page
- [ ] Pacing status (on_track/at_risk/off_track) shown for each target
- [ ] At least one contribution-to-growth view (by product)
- [ ] Egypt map fed with governorate-level data
- [ ] Existing comparison mode extended with MTD/YTD/rolling options
- [ ] All new endpoints have tests (80%+ coverage maintained)
- [ ] No breaking changes to existing API consumers
