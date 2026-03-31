# Enhancement 3 — Analytics Dashboard Upgrades

> **Status**: PLANNED
> **Date**: 2026-03-31
> **Scope**: KPI sparklines, billing/customer type analysis, period comparison, top movers, site detail page, product hierarchy
> **Model**: All agents and subagents use Opus

---

## Overview

Enhancement 3 upgrades the DataPulse dashboard from a "data display" tool to a **decision-support** tool. The core insight: dbt models already compute `avg_basket_size`, `walk_in_ratio`, `insurance_ratio`, billing breakdowns, and growth percentages — but the API layer only exposes ~40% of available columns. Most of this enhancement is about **wiring existing data** to new frontend components.

**Key deliverables:**
- Sparkline trends inside KPI cards
- Metric info tooltips explaining every KPI
- 4 new KPI cards (basket size, returns, MTD/YTD transactions)
- Billing method breakdown donut chart
- Walk-in vs Insurance stacked bar chart
- Period-over-period comparison on trend charts
- Top movers (biggest gainers/losers) card
- Site detail page (`/sites/[key]`)
- Product category/brand hierarchy view

---

## Architecture Changes

| Layer | Changes |
|-------|---------|
| **Pydantic Models** | ~8 new models (BillingBreakdown, CustomerTypeBreakdown, TopMovers, SiteDetail, ProductHierarchy, etc.) |
| **Repository** | 3 new repo files (`comparison_repository.py`, `hierarchy_repository.py`, `breakdown_repository.py` if needed) + methods in existing repos |
| **Service** | ~6 new service methods |
| **API Routes** | 5 new endpoints |
| **Frontend Types** | ~10 new TypeScript interfaces |
| **Frontend Hooks** | 7 new SWR hooks |
| **Frontend Components** | 8 new components |
| **Frontend Pages** | 1 new page (`/sites/[key]`) |
| **dbt** | No changes needed — all data already exists |

---

## Phase 1: Quick Visual Wins

> **Effort**: Low | **Impact**: High | **Dependency**: None

### 1.1 — Expand KPI Metrics

Currently, the KPI grid shows 7 cards focused on net sales amounts. The `metrics_summary` table has additional fields that are not exposed.

#### 1.1a: Add fields to KPISummary Pydantic model

**File**: `src/datapulse/analytics/models.py`

Add 4 new fields to `KPISummary`:

```python
avg_basket_size: JsonDecimal      # from agg_sales_daily AVG
daily_returns: int                 # from metrics_summary
mtd_transactions: int              # from metrics_summary
ytd_transactions: int              # from metrics_summary
```

All fields have defaults (0) for backward compatibility.

#### 1.1b: Update repository query

**File**: `src/datapulse/analytics/repository.py`

Modify `get_kpi_summary()` SQL to also SELECT `daily_returns`, `mtd_transactions`, `ytd_transactions` from `metrics_summary`. Add a second query to get `avg_basket_size` from `agg_sales_daily` for the target date:

```sql
SELECT AVG(avg_basket_size) AS avg_basket_size
FROM public_marts.agg_sales_daily
WHERE date_key = :date_key
```

#### 1.1c: Update TypeScript interface

**File**: `frontend/src/types/api.ts`

Add `avg_basket_size: number`, `daily_returns: number`, `mtd_transactions: number`, `ytd_transactions: number` to `KPISummary` interface.

#### 1.1d: Add new KPI cards to the grid

**File**: `frontend/src/components/dashboard/kpi-grid.tsx`

Add 4 new cards with appropriate Lucide icons:
- `RotateCcw` for returns
- `ShoppingCart` for basket size
- `Hash` for transaction counts

Layout: primary 7 cards on first row, 4 secondary cards on second row with slightly lighter visual weight.

---

### 1.2 — KPI Sparklines

Tiny inline trend charts inside KPI cards showing the last 7 days of data.

#### 1.2a: Add sparkline repository method

**File**: `src/datapulse/analytics/repository.py`

```python
def get_kpi_sparkline(self, target_date: date, days: int = 7) -> list[TimeSeriesPoint]:
    """Last N days of daily_net_amount from metrics_summary."""
```

SQL:
```sql
SELECT full_date AS period, daily_net_amount AS value
FROM public_marts.metrics_summary
WHERE full_date BETWEEN (:target_date - INTERVAL ':days days') AND :target_date
ORDER BY full_date
```

#### 1.2b: Add sparkline field to KPISummary

**File**: `src/datapulse/analytics/models.py`

```python
sparkline: list[TimeSeriesPoint] = []  # backward-compatible default
```

#### 1.2c: Wire in service layer

**File**: `src/datapulse/analytics/service.py`

In `get_dashboard_summary()`, after getting the KPI row, call `repo.get_kpi_sparkline(target)` and include in returned `KPISummary`.

#### 1.2d: Update TypeScript + hook

**File**: `frontend/src/types/api.ts` — Add `sparkline?: TimeSeriesPoint[]` to `KPISummary`.

No new hook needed — existing `use-summary.ts` already returns `KPISummary`.

#### 1.2e: Add sparkline rendering to KPICard

**File**: `frontend/src/components/dashboard/kpi-card.tsx`

Add optional `sparkline` prop. When present, render a tiny Recharts `<AreaChart>`:
- Height: 32px
- No axes, no labels, no tooltip
- Gradient fill matching the card's accent color
- Transparent background

#### 1.2f: Pass sparkline data from grid

**File**: `frontend/src/components/dashboard/kpi-grid.tsx`

Pass `sparkline={data.sparkline}` to the "Today Net Sales" card. Other cards don't get sparklines in Phase 1.

---

### 1.3 — Metric Info Tooltips

(i) icon on each KPI card explaining the metric.

#### 1.3a: Create MetricTooltip component

**File (NEW)**: `frontend/src/components/shared/metric-tooltip.tsx`

Uses `@radix-ui/react-popover` (already installed). Small `(i)` icon button, popover on hover/click.

Props: `description: string`

#### 1.3b: Wire into KPI cards

**File**: `frontend/src/components/dashboard/kpi-card.tsx` — Add optional `tooltip?: string` prop.

**File**: `frontend/src/components/dashboard/kpi-grid.tsx` — Add tooltip text to each card:

| Card | Tooltip |
|------|---------|
| Today Net Sales | "Net sales amount for the selected target date after discounts and returns" |
| MTD Net Sales | "Month-to-date cumulative net sales from the 1st of the current month" |
| YTD Net Sales | "Year-to-date cumulative net sales from January 1st" |
| MoM Growth | "Month-over-month growth comparing current MTD to same date last month" |
| YoY Growth | "Year-over-year growth comparing current YTD to same date last year" |
| Daily Transactions | "Number of individual line-item transactions on the target date" |
| Daily Customers | "Count of unique customers who made purchases on the target date" |
| Avg Basket Size | "Average transaction value per invoice on the target date" |
| Daily Returns | "Number of return transactions recorded on the target date" |
| MTD Transactions | "Month-to-date cumulative transaction count" |
| YTD Transactions | "Year-to-date cumulative transaction count" |

### Phase 1 Testing

**Backend**:
- Test `get_kpi_sparkline` returns correct number of points (7)
- Test expanded `KPISummary` model with new fields has correct defaults
- Test backward compatibility (old responses still parse)

**Frontend E2E** (`frontend/e2e/dashboard.spec.ts`):
- Test tooltip appears on (i) icon hover
- Test sparkline SVG element exists inside KPI card
- Test new KPI cards render (basket size, returns, transactions)

---

## Phase 2: Billing & Customer Type Analysis

> **Effort**: Medium | **Impact**: High | **Dependency**: None (independent of Phase 1)

### 2.1 — Billing Method Breakdown

New donut chart showing Cash vs Credit vs Delivery vs Pick-Up sales split.

#### 2.1a: Add Pydantic models

**File**: `src/datapulse/analytics/models.py`

```python
class BillingBreakdownItem(BaseModel):
    model_config = ConfigDict(frozen=True)
    billing_way: str
    transaction_count: int
    total_net_amount: JsonDecimal
    pct_of_total: JsonDecimal

class BillingBreakdown(BaseModel):
    model_config = ConfigDict(frozen=True)
    items: list[BillingBreakdownItem]
    total_transactions: int
    total_net_amount: JsonDecimal
```

#### 2.1b: Add repository method

**File**: `src/datapulse/analytics/repository.py`

```python
def get_billing_breakdown(self, filters: AnalyticsFilter) -> BillingBreakdown:
```

SQL against `agg_sales_daily` (grain: date_key, site_key, **billing_way**):

```sql
SELECT billing_way,
       SUM(transaction_count) AS transaction_count,
       SUM(total_net_amount) AS total_net_amount
FROM public_marts.agg_sales_daily
WHERE {date/site filters}
GROUP BY billing_way
ORDER BY total_net_amount DESC
```

Compute `pct_of_total` in Python (same pattern as `_build_ranking`).

#### 2.1c: Add service + route

**File**: `src/datapulse/analytics/service.py` — Add `get_billing_breakdown(filters)`.

**File**: `src/datapulse/api/routes/analytics.py` — New endpoint:

```
GET /analytics/billing-breakdown
Rate limit: 60/minute
Auth: required
Response: BillingBreakdown
Query params: start_date, end_date, site_key (standard AnalyticsQueryParams)
```

#### 2.1d: Frontend types + hook + chart

**File**: `frontend/src/types/api.ts` — Add `BillingBreakdownItem`, `BillingBreakdown` interfaces.

**File (NEW)**: `frontend/src/hooks/use-billing-breakdown.ts` — SWR hook.

**File (NEW)**: `frontend/src/components/dashboard/billing-breakdown-chart.tsx`

Recharts `<PieChart>` with donut variant (`innerRadius`):
- Legend below chart on mobile, right side on desktop
- Uses `CHART_COLORS` from constants
- Shows billing method name, count, and percentage

#### 2.1e: Add to dashboard

**File**: `frontend/src/app/(app)/dashboard/page.tsx`

New section "Sales Distribution" after Trends, containing the donut chart.

---

### 2.2 — Customer Type Breakdown (Walk-in vs Insurance)

Stacked bar chart showing customer type distribution over time.

#### 2.2a: Add Pydantic models

**File**: `src/datapulse/analytics/models.py`

```python
class CustomerTypeBreakdownItem(BaseModel):
    model_config = ConfigDict(frozen=True)
    period: str               # "2024-01"
    walk_in_count: int
    insurance_count: int
    regular_count: int        # total - walk_in - insurance
    total_count: int

class CustomerTypeBreakdown(BaseModel):
    model_config = ConfigDict(frozen=True)
    items: list[CustomerTypeBreakdownItem]
```

#### 2.2b: Add repository method

**File**: `src/datapulse/analytics/repository.py`

Query `agg_sales_monthly` which already has `walk_in_count`, `insurance_count`, `transaction_count`:

```sql
SELECT LPAD(year::text, 4, '0') || '-' || LPAD(month::text, 2, '0') AS period,
       SUM(walk_in_count) AS walk_in_count,
       SUM(insurance_count) AS insurance_count,
       SUM(transaction_count) AS total_count
FROM public_marts.agg_sales_monthly
WHERE {filters}
GROUP BY year, month
ORDER BY year, month
```

Compute `regular_count = total_count - walk_in_count - insurance_count` in Python.

#### 2.2c: Add service + route

```
GET /analytics/customer-type-breakdown
Rate limit: 60/minute
Auth: required
Response: CustomerTypeBreakdown
```

#### 2.2d: Frontend types + hook + chart

**File (NEW)**: `frontend/src/hooks/use-customer-type-breakdown.ts`

**File (NEW)**: `frontend/src/components/dashboard/customer-type-chart.tsx`

Recharts `<BarChart>` with stacked bars:
- X-axis = month
- Stacks: Walk-in (teal), Insurance (blue), Regular (gray)
- Responsive container

#### 2.2e: Add to dashboard

Place alongside billing breakdown chart in a 2-column grid row under "Sales Distribution".

### Phase 2 Testing

**Backend**:
- `test_billing_breakdown_empty`: returns zero totals for no data
- `test_billing_breakdown_pct_of_total`: percentages sum to ~100
- `test_customer_type_regular_count`: verify `regular = total - walk_in - insurance`
- `test_customer_type_breakdown_ordering`: results ordered by year, month

**Frontend E2E** (`frontend/e2e/dashboard.spec.ts`):
- Test billing donut chart renders with legend items
- Test customer type stacked bar chart renders

---

## Phase 3: Comparative Analytics

> **Effort**: Medium | **Impact**: High | **Dependency**: None (independent of Phase 1-2)

### 3.1 — Period-over-Period Toggle

Frontend-only logic — no new backend endpoints needed.

#### 3.1a: Create comparison hook

**File (NEW)**: `frontend/src/hooks/use-comparison-trend.ts`

Custom hook that:
1. Takes current filters + `compare: boolean` flag
2. When `compare=true`, computes previous period dates (same duration, shifted back)
3. Fetches both current and previous period using `fetchAPI<TrendResult>` in parallel
4. Returns `{ current: TrendResult, previous: TrendResult | null, isLoading }`

Uses `date-fns` (already in project via `date-utils.ts`) for reliable date arithmetic.

#### 3.1b: Enhance DailyTrendChart

**File**: `frontend/src/components/dashboard/daily-trend-chart.tsx`

- Add toggle button "Compare Previous Period" in chart header
- When active, render second `<Area>` with dashed stroke and 40% opacity
- X-axis labels stay as current period; previous period aligned by index (day 1 = day 1)

#### 3.1c: Enhance MonthlyTrendChart

**File**: `frontend/src/components/dashboard/monthly-trend-chart.tsx`

Same toggle + overlay pattern as daily chart.

---

### 3.2 — Top Movers

Shows products/customers/staff with the biggest growth or decline vs previous period.

#### 3.2a: Add Pydantic models

**File**: `src/datapulse/analytics/models.py`

```python
class MoverItem(BaseModel):
    model_config = ConfigDict(frozen=True)
    key: int
    name: str
    current_value: JsonDecimal
    previous_value: JsonDecimal
    change_pct: JsonDecimal
    direction: str               # "up" or "down"

class TopMovers(BaseModel):
    model_config = ConfigDict(frozen=True)
    gainers: list[MoverItem]
    losers: list[MoverItem]
    entity_type: str             # "product", "customer", "staff"
```

#### 3.2b: Add repository

**File (NEW)**: `src/datapulse/analytics/comparison_repository.py`

```python
class ComparisonRepository:
    def get_top_movers(
        self,
        entity_type: str,
        current_filters: AnalyticsFilter,
        previous_filters: AnalyticsFilter,
        limit: int = 5,
    ) -> TopMovers:
```

Runs two ranking queries (current + previous period) using the existing `_get_ranking` pattern, then computes deltas in Python.

Handles edge cases:
- Entity in current but not previous = "new" (skip or show as +100%)
- Entity in previous but not current = "churned" (show as -100%)

#### 3.2c: Add service + route

**File**: `src/datapulse/analytics/service.py` — Computes previous period from current filters automatically.

**File**: `src/datapulse/api/routes/analytics.py`:

```
GET /analytics/top-movers?entity_type=product
Rate limit: 60/minute
Auth: required
Query params: entity_type (product|customer|staff), standard filter params
Response: TopMovers
```

#### 3.2d: Frontend types + hook + component

**File (NEW)**: `frontend/src/hooks/use-top-movers.ts`

**File (NEW)**: `frontend/src/components/dashboard/top-movers-card.tsx`

Two-column card:
- **Gainers** column: green arrows, name, current value, +% change
- **Losers** column: red arrows, name, current value, -% change
- Tab selector for product/customer/staff entity type

#### 3.2e: Add to dashboard

Place "Top Movers" section after Rankings on the dashboard page.

### Phase 3 Testing

**Backend**:
- Test `get_top_movers` with both periods having data
- Test entity missing in previous period (new entity = handle gracefully)
- Test `entity_type` validation rejects invalid values
- Test comparison period date computation

**Frontend E2E**:
- Test "Compare Previous Period" toggle on trend charts
- Test toggle shows second line on chart
- Test top movers card renders gainers and losers sections

---

## Phase 4: Missing Pages & Drill-down

> **Effort**: Medium | **Impact**: High | **Dependency**: None (independent of Phase 1-3)

### 4.1 — Site Detail Page

Currently, `/sites` shows a comparison view but there's no drill-down to a single site.

#### 4.1a: Add Pydantic model

**File**: `src/datapulse/analytics/models.py`

```python
class SiteDetail(BaseModel):
    model_config = ConfigDict(frozen=True)
    site_key: int
    site_code: str
    site_name: str
    area_manager: str
    total_net_amount: JsonDecimal
    transaction_count: int
    unique_customers: int
    unique_staff: int
    walk_in_ratio: JsonDecimal
    insurance_ratio: JsonDecimal
    return_rate: JsonDecimal
    monthly_trend: list[TimeSeriesPoint] = []
```

#### 4.1b: Add repository method

**File**: `src/datapulse/analytics/detail_repository.py`

```python
def get_site_detail(self, site_key: int) -> SiteDetail | None:
```

Query `agg_sales_by_site` joined with `dim_site` (which has `area_manager`, `governorate`). Aggregate across all months. Monthly trend via same table grouped by year/month.

**Important**: Add `"public_marts.agg_sales_by_site"` and `"site_key"` to the existing whitelists in `DetailRepository`.

#### 4.1c: Add service + route

```
GET /analytics/sites/{site_key}
Rate limit: 100/minute
Auth: required
Path param: site_key (int, ge=1)
Response: SiteDetail
404 if not found
```

#### 4.1d: Frontend types + hook

**File (NEW)**: `frontend/src/hooks/use-site-detail.ts`

#### 4.1e: Create site detail page

**File (NEW)**: `frontend/src/app/(app)/sites/[key]/page.tsx`
**File (NEW)**: `frontend/src/app/(app)/sites/[key]/loading.tsx`
**File (NEW)**: `frontend/src/components/sites/site-detail-view.tsx`

Layout follows existing detail page pattern (product/customer/staff):
- Header with site name + area manager badge
- Summary stats grid: total sales, transactions, unique customers, unique staff, walk-in ratio, insurance ratio, return rate
- Monthly trend chart

#### 4.1f: Make site names clickable

**File**: `frontend/src/components/sites/site-comparison-cards.tsx`

Wrap site names in `<Link href={/sites/${key}}>`.

---

### 4.2 — Product Category/Brand Hierarchy

Collapsible tree view on the products page: Category > Brand > Product.

#### 4.2a: Add Pydantic models

**File**: `src/datapulse/analytics/models.py`

```python
class ProductInCategory(BaseModel):
    model_config = ConfigDict(frozen=True)
    product_key: int
    drug_name: str
    total_net_amount: JsonDecimal
    transaction_count: int

class BrandGroup(BaseModel):
    model_config = ConfigDict(frozen=True)
    brand: str
    total_net_amount: JsonDecimal
    products: list[ProductInCategory]

class CategoryGroup(BaseModel):
    model_config = ConfigDict(frozen=True)
    category: str
    total_net_amount: JsonDecimal
    brands: list[BrandGroup]

class ProductHierarchy(BaseModel):
    model_config = ConfigDict(frozen=True)
    categories: list[CategoryGroup]
```

#### 4.2b: Add repository

**File (NEW)**: `src/datapulse/analytics/hierarchy_repository.py`

```python
class HierarchyRepository:
    def get_product_hierarchy(self, filters: AnalyticsFilter) -> ProductHierarchy:
```

Query:
```sql
SELECT drug_category, drug_brand, product_key, drug_name,
       SUM(total_net_amount) AS total_net_amount,
       SUM(transaction_count) AS transaction_count
FROM public_marts.agg_sales_by_product
WHERE {filters}
GROUP BY drug_category, drug_brand, product_key, drug_name
ORDER BY drug_category, drug_brand, total_net_amount DESC
```

Group in Python into nested `CategoryGroup -> BrandGroup -> ProductInCategory`.

**Performance guard**: Use `ROW_NUMBER() OVER (PARTITION BY drug_brand ORDER BY total_net_amount DESC)` to limit to top 10 products per brand.

#### 4.2c: Wire into service + deps + route

**File**: `src/datapulse/api/deps.py` — Add `HierarchyRepository` to service factory.

```
GET /analytics/products/by-category
Rate limit: 60/minute
Auth: required
Response: ProductHierarchy
```

#### 4.2d: Frontend types + hook + component

**File (NEW)**: `frontend/src/hooks/use-product-hierarchy.ts`

**File (NEW)**: `frontend/src/components/products/product-hierarchy.tsx`

Collapsible tree view:
- Category rows expand to brands
- Brand rows expand to products
- Each row shows name + total net amount
- Lucide `ChevronRight`/`ChevronDown` for expand/collapse
- Local state (`useState` for expanded keys)
- Lazy render (only render expanded children)

#### 4.2e: Add to products page

**File**: `frontend/src/app/(app)/products/page.tsx`

Tab or toggle to switch between current ranking view and hierarchy view.

### Phase 4 Testing

**Backend**:
- Test `get_site_detail` returns None for non-existent site
- Test `get_site_detail` aggregates across months correctly
- Test `get_product_hierarchy` nesting structure (category -> brand -> product)
- Test `get_product_hierarchy` with empty data returns empty categories list

**Frontend E2E**:
- Test `/sites/1` page loads with site name and stats
- Test site name is clickable from sites list page
- Test product hierarchy expand/collapse interaction

---

## New Files Summary

| File | Phase | Purpose |
|------|-------|---------|
| `frontend/src/components/shared/metric-tooltip.tsx` | 1 | Reusable (i) info popover |
| `frontend/src/hooks/use-billing-breakdown.ts` | 2 | SWR hook for billing breakdown |
| `frontend/src/components/dashboard/billing-breakdown-chart.tsx` | 2 | Donut chart for billing methods |
| `frontend/src/hooks/use-customer-type-breakdown.ts` | 2 | SWR hook for customer types |
| `frontend/src/components/dashboard/customer-type-chart.tsx` | 2 | Stacked bar for walk-in/insurance |
| `frontend/src/hooks/use-comparison-trend.ts` | 3 | Hook for two-period fetch |
| `frontend/src/hooks/use-top-movers.ts` | 3 | SWR hook for top movers |
| `frontend/src/components/dashboard/top-movers-card.tsx` | 3 | Gainers/losers card |
| `src/datapulse/analytics/comparison_repository.py` | 3 | Top movers query logic |
| `frontend/src/hooks/use-site-detail.ts` | 4 | SWR hook for site detail |
| `frontend/src/app/(app)/sites/[key]/page.tsx` | 4 | Site detail page |
| `frontend/src/app/(app)/sites/[key]/loading.tsx` | 4 | Site detail loading skeleton |
| `frontend/src/components/sites/site-detail-view.tsx` | 4 | Site detail component |
| `src/datapulse/analytics/hierarchy_repository.py` | 4 | Product hierarchy query |
| `frontend/src/hooks/use-product-hierarchy.ts` | 4 | SWR hook for product hierarchy |
| `frontend/src/components/products/product-hierarchy.tsx` | 4 | Collapsible tree view |

## Modified Files Summary

| File | Phases | Changes |
|------|--------|---------|
| `src/datapulse/analytics/models.py` | 1,2,3,4 | ~8 new Pydantic models |
| `src/datapulse/analytics/repository.py` | 1,2 | `get_kpi_sparkline`, `get_billing_breakdown`, `get_customer_type_breakdown` |
| `src/datapulse/analytics/detail_repository.py` | 4 | `get_site_detail`, expand whitelists |
| `src/datapulse/analytics/service.py` | 1,2,3,4 | ~6 new service methods |
| `src/datapulse/api/routes/analytics.py` | 2,3,4 | 5 new endpoints |
| `src/datapulse/api/deps.py` | 4 | Wire `HierarchyRepository` |
| `frontend/src/types/api.ts` | 1,2,3,4 | ~10 new interfaces |
| `frontend/src/components/dashboard/kpi-card.tsx` | 1 | Sparkline + tooltip props |
| `frontend/src/components/dashboard/kpi-grid.tsx` | 1 | New cards, sparkline/tooltip data |
| `frontend/src/components/dashboard/daily-trend-chart.tsx` | 3 | Comparison toggle + overlay |
| `frontend/src/components/dashboard/monthly-trend-chart.tsx` | 3 | Comparison toggle + overlay |
| `frontend/src/app/(app)/dashboard/page.tsx` | 2,3 | Billing, customer type, movers sections |
| `frontend/src/app/(app)/products/page.tsx` | 4 | Hierarchy tab/toggle |
| `frontend/src/components/sites/site-comparison-cards.tsx` | 4 | Clickable site names |
| `tests/` | 1,2,3,4 | New tests for all repo/service methods |
| `frontend/e2e/dashboard.spec.ts` | 1,2,3 | E2E tests for new features |

## New API Endpoints

| Method | Path | Params | Response | Phase |
|--------|------|--------|----------|-------|
| GET | `/analytics/billing-breakdown` | Standard filters | `BillingBreakdown` | 2 |
| GET | `/analytics/customer-type-breakdown` | Standard filters | `CustomerTypeBreakdown` | 2 |
| GET | `/analytics/top-movers` | Filters + `entity_type` | `TopMovers` | 3 |
| GET | `/analytics/sites/{site_key}` | `site_key` (path) | `SiteDetail` | 4 |
| GET | `/analytics/products/by-category` | Standard filters | `ProductHierarchy` | 4 |

---

## Risks & Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| `repository.py` exceeding 400-line limit | Medium | Extract to `breakdown_repository.py` if needed; Phase 3-4 already use separate repo files |
| Product hierarchy query returning 17k+ rows | Medium | Use `ROW_NUMBER() OVER (PARTITION BY drug_brand)` to limit top 10 per brand |
| Period comparison date edge cases (Feb 28, year boundary) | Medium | Use `date-fns` `subDays`/`subMonths` for reliable shifting; test edge cases |
| Dashboard performance with many charts | Low | SWR deduplication + caching; new sections below fold (lazy render) |
| Comparison toggle fetching duplicate data | Low | SWR built-in deduplication; separate cache keys |

---

## Success Criteria

- [ ] KPI grid shows sparkline in "Today Net Sales" card
- [ ] (i) tooltips appear on all KPI cards with metric descriptions
- [ ] New KPI cards (basket size, returns, MTD/YTD transactions) render
- [ ] Billing breakdown donut chart displays on dashboard
- [ ] Customer type stacked bar chart displays on dashboard
- [ ] "Compare Previous Period" toggle overlays previous data on trend charts
- [ ] Top movers card shows gainers/losers for products/customers/staff
- [ ] `/sites/{key}` detail page loads with full metrics and monthly trend
- [ ] Products page has category/brand hierarchy view with expand/collapse
- [ ] All new endpoints require auth and respect RLS
- [ ] Backend test coverage remains 80%+
- [ ] E2E tests pass for all new features
- [ ] No existing tests broken

---

## Implementation Order

All 4 phases are **independently deployable**. Recommended order:

```
Phase 1 (Quick Wins) ──────┐
Phase 2 (Billing/CustType) ─┼── can run in parallel
Phase 3 (Comparison) ───────┘
Phase 4 (Pages/Drill-down) ──── after Phase 1-3 merged (uses patterns established)
```

Each phase = 1 PR, reviewable and mergeable independently.
