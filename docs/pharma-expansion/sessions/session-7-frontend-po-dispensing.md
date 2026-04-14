# Session 7: Frontend — Purchase Orders, Suppliers, Dispensing Pages

## Context Brief

**DataPulse** frontend is Next.js 14 with TypeScript, Tailwind, SWR, Recharts, dark/light theme.

**What already exists**:
- Session 6: Operations nav group in sidebar, `frontend/src/types/inventory.ts` + `expiry.ts`, inventory + expiry pages + hooks + components
- Backend APIs complete: `/api/v1/purchase-orders/*` (7 endpoints, Session 4), `/api/v1/suppliers/*` (5 endpoints, Session 4), `/api/v1/dispensing/*` (5 endpoints, Session 5), `/api/v1/margins/analysis` (Session 4)
- All frontend patterns established in Session 6 (same page structure, chart pattern, hook pattern)

**Goal**: Build remaining 4 page routes — Purchase Orders, PO Detail, Suppliers, Dispensing — with components and hooks.

---

## Task List

### 1. Create TypeScript Types

#### `frontend/src/types/purchase-orders.ts`
```typescript
export interface PurchaseOrder {
  po_number: string;
  po_date: string;
  supplier_code: string;
  supplier_name: string;
  site_code: string;
  site_name: string;
  status: "draft" | "submitted" | "partial" | "received" | "cancelled";
  expected_date: string | null;
  total_ordered_value: number;
  total_received_value: number;
  line_count: number;
}

export interface POLine {
  po_number: string;
  line_number: number;
  drug_code: string;
  drug_name: string;
  ordered_quantity: number;
  unit_price: number;
  received_quantity: number;
  line_total: number;
  fulfillment_pct: number;
}

export interface POCreateRequest {
  po_date: string;
  supplier_code: string;
  site_code: string;
  expected_date?: string;
  lines: Array<{ drug_code: string; quantity: number; unit_price: number }>;
}
```

#### `frontend/src/types/suppliers.ts`
```typescript
export interface SupplierInfo {
  supplier_code: string;
  supplier_name: string;
  contact_name: string | null;
  contact_phone: string | null;
  contact_email: string | null;
  address: string | null;
  payment_terms_days: number;
  lead_time_days: number;
  is_active: boolean;
}

export interface SupplierPerformance {
  supplier_name: string;
  total_orders: number;
  avg_lead_days: number | null;
  fill_rate: number | null;
  total_spend: number;
  cancelled_count: number;
}
```

#### `frontend/src/types/dispensing.ts`
```typescript
export interface DispenseRate {
  product_key: number;
  drug_code: string;
  drug_name: string;
  drug_brand: string;
  site_code: string;
  site_name: string;
  avg_daily_dispense: number;
  avg_weekly_dispense: number;
  avg_monthly_dispense: number;
  active_days: number;
}

export interface DaysOfStock {
  product_key: number;
  drug_code: string;
  drug_name: string;
  site_code: string;
  current_quantity: number;
  days_of_stock: number | null;
  avg_daily_dispense: number;
}

export interface VelocityClassification {
  product_key: number;
  drug_code: string;
  drug_name: string;
  drug_brand: string;
  lifecycle_stage: string | null;
  velocity_class: "fast_mover" | "normal_mover" | "slow_mover" | "dead_stock";
  avg_daily_dispense: number;
}

export interface StockoutRisk {
  product_key: number;
  drug_code: string;
  drug_name: string;
  site_code: string;
  current_quantity: number;
  days_of_stock: number | null;
  risk_level: "stockout" | "critical" | "at_risk";
  suggested_reorder_qty: number;
}
```

---

### 2. Create SWR Hooks (8 hooks)

1. `use-purchase-orders.ts` — GET `/api/v1/purchase-orders` (with status filter)
2. `use-po-detail.ts` — GET `/api/v1/purchase-orders/{po_number}` + lines
3. `use-po-create.ts` — POST mutation hook for creating POs
4. `use-suppliers.ts` — GET `/api/v1/suppliers`
5. `use-supplier-detail.ts` — GET `/api/v1/suppliers/{supplier_code}`
6. `use-supplier-performance.ts` — GET `/api/v1/suppliers/{supplier_code}/performance`
7. `use-dispense-rate.ts` — GET `/api/v1/dispensing/rates`
8. `use-days-of-stock.ts` — GET `/api/v1/dispensing/days-of-stock`
9. `use-velocity.ts` — GET `/api/v1/dispensing/velocity`
10. `use-stockout-risk.ts` — GET `/api/v1/dispensing/stockout-risk`
11. `use-reconciliation.ts` — GET `/api/v1/dispensing/reconciliation`

For mutation hooks (PO create):
```typescript
import useSWRMutation from "swr/mutation";
import { fetchAPI } from "@/lib/api-client";

export function usePOCreate() {
  const { trigger, isMutating, error } = useSWRMutation(
    "/api/v1/purchase-orders",
    (url, { arg }: { arg: POCreateRequest }) => fetchAPI(url, undefined, { method: "POST", body: JSON.stringify(arg) }),
  );
  return { createPO: trigger, isCreating: isMutating, error };
}
```

---

### 3. Create Pages

#### `frontend/src/app/(app)/purchase-orders/page.tsx`
- `POListTable` — paginated table with status badges (colored pills: draft=gray, submitted=blue, partial=orange, received=green, cancelled=red)
- `POCreateForm` — modal/drawer with supplier picker, site selector, line item editor
- Quick stats at top: total POs, pending POs, total value

#### `frontend/src/app/(app)/purchase-orders/[po_number]/page.tsx`
- `POHeader` — PO info + status badge + action buttons (Submit, Cancel)
- `POLineItems` — table of line items with received quantity progress bars
- `POStatusPipeline` — visual pipeline: draft -> submitted -> partial -> received
- `DeliveryTimeline` — timeline of receipt events (if partially delivered)

#### `frontend/src/app/(app)/suppliers/page.tsx`
- `SupplierTable` — searchable table with is_active filter
- `SupplierDetail` — slide-over panel with contact info
- `SupplierPerformanceChart` — bar chart of avg lead time, fill rate per supplier

#### `frontend/src/app/(app)/dispensing/page.tsx`
- `DispenseRateCards` — top 10 fastest-moving products with daily rates
- `DaysOfStockChart` — horizontal bar chart sorted by days_of_stock ascending (most critical first)
- `VelocityGrid` — 4-quadrant view: fast/normal/slow/dead with product counts
- `StockoutRiskTable` — products at risk, sorted by risk_level
- `ReconciliationSummary` — variance summary between physical counts and calculated stock

Create `loading.tsx` for each page.

---

### 4. Create Components (~14 components)

**Purchase Orders** (`frontend/src/components/purchase-orders/`):
1. `po-list-table.tsx` — sortable, filterable table with status column
2. `po-create-form.tsx` — form with line item add/remove
3. `po-line-items.tsx` — table showing ordered vs received with progress
4. `po-status-pipeline.tsx` — visual step indicator

**Suppliers** (`frontend/src/components/suppliers/`):
5. `supplier-table.tsx` — searchable list
6. `supplier-performance-chart.tsx` — Recharts bar chart via ChartCard

**Dispensing** (`frontend/src/components/dispensing/`):
7. `dispense-rate-cards.tsx` — grid of rate KPI cards
8. `days-of-stock-chart.tsx` — horizontal bar chart
9. `velocity-grid.tsx` — 2x2 quadrant grid with counts
10. `stockout-risk-table.tsx` — table with risk level badges
11. `reconciliation-summary.tsx` — variance table

**PO Status Pipeline pattern**:
```typescript
const STEPS = ["draft", "submitted", "partial", "received"] as const;
const STEP_COLORS = { draft: "gray", submitted: "blue", partial: "amber", received: "green", cancelled: "red" };

export function POStatusPipeline({ currentStatus }: { currentStatus: string }) {
  return (
    <div className="flex items-center gap-2">
      {STEPS.map((step, i) => {
        const isActive = STEPS.indexOf(currentStatus as any) >= i;
        return (
          <div key={step} className="flex items-center gap-2">
            <div className={`h-8 w-8 rounded-full flex items-center justify-center text-xs font-bold
              ${isActive ? `bg-${STEP_COLORS[step]}-500 text-white` : "bg-muted text-muted-foreground"}`}>
              {i + 1}
            </div>
            <span className={isActive ? "font-medium" : "text-muted-foreground"}>{step}</span>
            {i < STEPS.length - 1 && <div className={`h-0.5 w-8 ${isActive ? "bg-accent" : "bg-muted"}`} />}
          </div>
        );
      })}
    </div>
  );
}
```

---

## Files Summary

| Action | Count | Path Pattern |
|--------|-------|-------------|
| CREATE | 3 | `frontend/src/types/{purchase-orders,suppliers,dispensing}.ts` |
| CREATE | 11 | `frontend/src/hooks/use-{po,supplier,dispense,velocity,stockout,reconciliation}*.ts` |
| CREATE | 4 | pages in `frontend/src/app/(app)/{purchase-orders,suppliers,dispensing}/page.tsx` |
| CREATE | 4 | loading states |
| CREATE | 1 | `frontend/src/app/(app)/purchase-orders/[po_number]/page.tsx` |
| CREATE | 11 | components across 3 directories |

---

## Verification Commands

```bash
cd frontend && npx tsc --noEmit
cd frontend && npm run build
```

## Exit Criteria

- [ ] All 4 new page routes render correctly with loading skeletons
- [ ] PO list page shows status badges with correct colors
- [ ] PO create form has line item add/remove functionality
- [ ] PO detail page shows status pipeline + line items with progress bars
- [ ] Supplier table has search + active filter
- [ ] Supplier performance chart uses ChartCard + useChartTheme
- [ ] Dispensing page displays all 5 analytics views
- [ ] Velocity grid shows 4-quadrant classification
- [ ] Stockout risk table sorted by severity
- [ ] TypeScript compiles with zero errors
- [ ] Build succeeds
