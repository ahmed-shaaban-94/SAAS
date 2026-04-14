# Session 6: Frontend — Inventory + Expiry Pages

## Context Brief

**DataPulse** frontend is Next.js 14 with TypeScript, Tailwind CSS, SWR for data fetching, Recharts for charts, dark/light theme via `next-themes`.

**What already exists**:
- Backend APIs complete: `/api/v1/inventory/*` (10 endpoints, Session 2), `/api/v1/expiry/*` (8 endpoints, Session 3)
- Frontend patterns established:
  - Pages: `"use client"` + `PageTransition` + `Breadcrumbs` + `Header` + `FilterBar`
  - Charts: `ChartCard` wrapper (`frontend/src/components/shared/chart-card.tsx`) + `useChartTheme()` hook
  - Data fetching: SWR hooks with `swrKey(url, filters)` + `fetchAPI<T>(url, filters)` from `frontend/src/lib/api-client.ts`
  - Navigation: `NAV_GROUPS` array in `frontend/src/lib/constants.ts` with `{label, href, icon, minRole}`
  - Loading: `LoadingCard` component for skeleton states
  - Dynamic imports for below-fold content
  - Sidebar: maps icon names via `iconMap` to lucide-react icons

**Goal**: Build all frontend pages for Inventory and Expiry domains — 3 pages + 3 loading states + 10 SWR hooks + 11 components. Add "Operations" nav group.

---

## Task List

### 1. Add Navigation Group

**Modify `frontend/src/lib/constants.ts`**:

Add a new nav group before the settings group:
```typescript
{
  id: "operations",
  label: "Operations",
  icon: "Warehouse",
  minRole: "editor",
  items: [
    { label: "Inventory",       href: "/inventory",        icon: "Package",       minRole: "editor" },
    { label: "Dispensing",      href: "/dispensing",       icon: "Activity",      minRole: "viewer" },
    { label: "Expiry Tracking", href: "/expiry",           icon: "Calendar",      minRole: "editor" },
    { label: "Purchase Orders", href: "/purchase-orders",  icon: "ClipboardList", minRole: "editor" },
    { label: "Suppliers",       href: "/suppliers",        icon: "Truck",         minRole: "editor" },
  ],
},
```

Ensure the icon names exist in the sidebar's `iconMap`. If `Warehouse`, `Package`, `Activity`, `ClipboardList`, `Truck` are not mapped, add them:
```typescript
import { Warehouse, Package, Activity, ClipboardList, Truck } from "lucide-react";
```

Gate the group visibility: only show if `NEXT_PUBLIC_FEATURE_PLATFORM=true` (check existing feature flag pattern in constants.ts).

---

### 2. Create TypeScript Types

#### `frontend/src/types/inventory.ts`
```typescript
export interface StockLevel {
  product_key: number;
  drug_code: string;
  drug_name: string;
  drug_brand: string;
  site_key: number;
  site_code: string;
  site_name: string;
  current_quantity: number;
  total_received: number;
  total_dispensed: number;
  total_wastage: number;
  last_movement_date: string | null;
}

export interface StockMovement {
  movement_key: number;
  movement_date: string;
  movement_type: string;
  drug_code: string;
  drug_name: string;
  site_code: string;
  batch_number: string | null;
  quantity: number;
  unit_cost: number | null;
  reference: string | null;
}

export interface StockValuation {
  product_key: number;
  drug_name: string;
  current_quantity: number;
  weighted_avg_cost: number;
  stock_value: number;
}

export interface ReorderAlert {
  product_key: number;
  drug_code: string;
  drug_name: string;
  site_code: string;
  site_name: string;
  current_quantity: number;
  reorder_point: number;
  risk_level: "stockout" | "critical" | "at_risk";
  suggested_reorder_qty: number;
  days_of_stock: number | null;
}

export interface ReorderConfig {
  drug_code: string;
  site_code: string;
  min_stock: number;
  reorder_point: number;
  max_stock: number;
  reorder_lead_days: number;
  is_active: boolean;
}
```

#### `frontend/src/types/expiry.ts`
```typescript
export interface BatchInfo {
  batch_key: number;
  drug_code: string;
  drug_name: string;
  site_code: string;
  batch_number: string;
  expiry_date: string;
  current_quantity: number;
  days_to_expiry: number;
  alert_level: "expired" | "critical" | "warning" | "caution" | "safe";
}

export interface ExpirySummary {
  site_code: string;
  site_name: string;
  expired_count: number;
  critical_count: number;
  warning_count: number;
  caution_count: number;
  total_expired_value: number;
}

export interface ExpiryCalendarDay {
  date: string;
  batch_count: number;
  total_quantity: number;
  alert_level: string;
}
```

---

### 3. Create SWR Hooks (10 hooks)

Follow existing hook pattern. Read `frontend/src/hooks/use-daily-trend.ts` or similar for reference.

```typescript
// Pattern:
import useSWR from "swr";
import { fetchAPI, swrKey } from "@/lib/api-client";
import type { FilterParams } from "@/types/filters";

export function useStockLevels(filters?: FilterParams) {
  const key = swrKey("/api/v1/inventory/stock-levels", filters);
  const { data, error, isLoading, mutate } = useSWR(
    key,
    () => fetchAPI<StockLevel[]>("/api/v1/inventory/stock-levels", filters),
    { refreshInterval: 300000 },
  );
  return { data, error, isLoading, mutate };
}
```

Create these hooks:
1. `use-stock-levels.ts` — GET `/api/v1/inventory/stock-levels`
2. `use-stock-movements.ts` — GET `/api/v1/inventory/movements`
3. `use-reorder-alerts.ts` — GET `/api/v1/inventory/reorder-alerts`
4. `use-stock-valuation.ts` — GET `/api/v1/inventory/valuation`
5. `use-product-stock.ts` — GET `/api/v1/inventory/stock-levels/{drug_code}` (takes drug_code param)
6. `use-product-movements.ts` — GET `/api/v1/inventory/movements/{drug_code}`
7. `use-reorder-config.ts` — GET `/api/v1/inventory/reorder-config` + PUT mutation
8. `use-expiry-calendar.ts` — GET `/api/v1/expiry/calendar`
9. `use-near-expiry.ts` — GET `/api/v1/expiry/near-expiry`
10. `use-expiry-summary.ts` — GET `/api/v1/expiry/summary`

---

### 4. Create Inventory Pages

#### `frontend/src/app/(app)/inventory/page.tsx`
```typescript
"use client";

import { Header } from "@/components/layout/header";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { PageTransition } from "@/components/layout/page-transition";
import { FilterBar } from "@/components/filters/filter-bar";
import { InventoryOverview } from "@/components/inventory/inventory-overview";
import dynamic from "next/dynamic";
import { LoadingCard } from "@/components/loading-card";

const StockLevelTable = dynamic(
  () => import("@/components/inventory/stock-level-table").then(m => ({ default: m.StockLevelTable })),
  { loading: () => <LoadingCard lines={8} />, ssr: false },
);
const StockMovementChart = dynamic(
  () => import("@/components/inventory/stock-movement-chart").then(m => ({ default: m.StockMovementChart })),
  { loading: () => <LoadingCard lines={4} />, ssr: false },
);
const ReorderAlertsList = dynamic(
  () => import("@/components/inventory/reorder-alerts-list").then(m => ({ default: m.ReorderAlertsList })),
  { loading: () => <LoadingCard lines={3} />, ssr: false },
);

export default function InventoryPage() {
  return (
    <PageTransition>
      <Breadcrumbs />
      <Header title="Inventory Management" description="Stock levels, movements, and reorder alerts" />
      <FilterBar />
      <InventoryOverview />
      <div className="grid gap-4 lg:grid-cols-2 mt-6">
        <StockMovementChart />
        <ReorderAlertsList />
      </div>
      <div className="mt-6">
        <StockLevelTable />
      </div>
    </PageTransition>
  );
}
```

#### `frontend/src/app/(app)/inventory/loading.tsx`
```typescript
import { LoadingCard } from "@/components/loading-card";

export default function InventoryLoading() {
  return (
    <div className="space-y-6">
      <LoadingCard className="h-10 w-48" />
      <LoadingCard className="h-6 w-96" />
      <div className="grid gap-4 md:grid-cols-4">
        <LoadingCard className="h-24" />
        <LoadingCard className="h-24" />
        <LoadingCard className="h-24" />
        <LoadingCard className="h-24" />
      </div>
      <LoadingCard className="h-80" />
    </div>
  );
}
```

#### `frontend/src/app/(app)/inventory/[drug_code]/page.tsx`
Product stock detail page:
- `StockHistoryChart` — Recharts AreaChart of stock level over time
- `MovementTimeline` — list of recent movements
- `BatchList` — batches for this product (from expiry API)
- `ReorderConfigForm` — editable form for reorder settings

---

### 5. Create Expiry Pages

#### `frontend/src/app/(app)/expiry/page.tsx`
Components:
- `ExpiryCalendar` — month view with color-coded days (red=expired, orange=critical, yellow=warning, green=safe)
- `NearExpiryList` — tabs for 30/60/90 days, shows batch list
- `ExpiredStockTable` — table of expired batches with quarantine/write-off actions
- `WriteOffSummaryChart` — Recharts showing write-off trends

#### `frontend/src/app/(app)/expiry/loading.tsx`

---

### 6. Create Components (11 components)

All in `frontend/src/components/inventory/` and `frontend/src/components/expiry/`.

**Inventory components**:
1. `inventory-overview.tsx` — 4 KPI cards (total stock value, items below reorder, stockout count, total items)
2. `stock-level-table.tsx` — paginated table with search, sortable columns
3. `stock-movement-chart.tsx` — Recharts AreaChart via `ChartCard` + `useChartTheme()`
4. `reorder-alerts-list.tsx` — color-coded alert cards (red/orange/yellow)
5. `stock-history-chart.tsx` — product-level stock history
6. `reorder-config-form.tsx` — form with min/reorder/max fields

**Expiry components**:
7. `expiry-calendar.tsx` — month grid with color-coded expiry counts
8. `near-expiry-list.tsx` — tabs (30d/60d/90d) with batch table
9. `expired-stock-table.tsx` — table with quarantine/write-off action buttons
10. `write-off-summary-chart.tsx` — Recharts chart
11. `quarantine-actions.tsx` — confirmation dialog for quarantine/write-off

**Chart pattern** (use for all charts):
```typescript
"use client";

import { AreaChart, Area, CartesianGrid, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { useChartTheme } from "@/hooks/use-chart-theme";
import { ChartCard } from "@/components/shared/chart-card";

export function StockMovementChart() {
  const chartTheme = useChartTheme();
  const { data, isLoading } = useStockMovements();

  if (isLoading) return <LoadingCard lines={4} />;

  return (
    <ChartCard title="STOCK MOVEMENTS" subtitle={`${data?.length ?? 0} movements`}>
      <ResponsiveContainer width="100%" height={300}>
        <AreaChart data={data ?? []}>
          <CartesianGrid stroke={chartTheme.gridStroke} />
          <XAxis dataKey="movement_date" tick={{ fill: chartTheme.tickFill, fontSize: chartTheme.tickFontSize }} />
          <YAxis tick={{ fill: chartTheme.tickFill, fontSize: chartTheme.tickFontSize }} />
          <Tooltip contentStyle={{ backgroundColor: chartTheme.tooltipBg, border: `1px solid ${chartTheme.tooltipBorder}`, color: chartTheme.tooltipColor }} />
          <Area type="monotone" dataKey="quantity" stroke={chartTheme.chartBlue} fill={chartTheme.chartBlue} fillOpacity={0.2} />
        </AreaChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}
```

---

## Files Summary

| Action | Path |
|--------|------|
| MODIFY | `frontend/src/lib/constants.ts` |
| CREATE | `frontend/src/types/inventory.ts` |
| CREATE | `frontend/src/types/expiry.ts` |
| CREATE | 10 hooks in `frontend/src/hooks/` |
| CREATE | `frontend/src/app/(app)/inventory/page.tsx` |
| CREATE | `frontend/src/app/(app)/inventory/loading.tsx` |
| CREATE | `frontend/src/app/(app)/inventory/[drug_code]/page.tsx` |
| CREATE | `frontend/src/app/(app)/inventory/[drug_code]/loading.tsx` |
| CREATE | `frontend/src/app/(app)/expiry/page.tsx` |
| CREATE | `frontend/src/app/(app)/expiry/loading.tsx` |
| CREATE | 6 components in `frontend/src/components/inventory/` |
| CREATE | 5 components in `frontend/src/components/expiry/` |

---

## Verification Commands

```bash
cd frontend && npx tsc --noEmit            # TypeScript check
cd frontend && npm run build                # Full build
cd frontend && npm run test -- --passWithNoTests  # Unit tests if any
```

## Exit Criteria

- [ ] Operations nav group appears in sidebar (only when feature flag enabled)
- [ ] Inventory dashboard page renders with 4 KPI cards + chart + table + alerts
- [ ] Product detail page shows stock history + movements + batches + reorder config
- [ ] Expiry dashboard shows calendar + near-expiry list + expired stock table
- [ ] All charts use `ChartCard` + `useChartTheme()` for dark/light support
- [ ] All hooks use `swrKey()` + `fetchAPI()` pattern
- [ ] Dynamic imports with `LoadingCard` skeleton for below-fold content
- [ ] TypeScript compiles with zero errors
- [ ] Build succeeds
