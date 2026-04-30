# Audit Report Fixes — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the five actionable frontend fixes from the Comprehensive Full-Stack Architectural Audit (items 3–7); items 1–2 (async DB migration, distributed task queue) are deferred as separate infrastructure tracks.

**Architecture:** Five independent surgical changes — Zustand cart store, lazy-loaded waterfall chart, Sentry trace propagation, per-widget error boundaries, and ModalShell focus trapping. Each task is self-contained; none depends on another. Two already-done items (CSP worker-src, Clerk 8s timeout) are confirmed present and excluded.

**Tech Stack:** Next.js 15 App Router, React 18, Zustand, `@sentry/nextjs`, `focus-trap-react`, TypeScript 5, Tailwind CSS, Vitest/Jest for unit tests.

---

## Scope note — deferred items

| Item | Why deferred |
|------|-------------|
| DB async migration (item 1) | Full SQLAlchemy + asyncpg rewrite; requires its own plan, migration strategy, and staging smoke test. |
| Distributed task queue (item 2) | Arq/Celery infra change; requires Redis worker deployment, schema changes, and load testing. |

---

## File map

| File | Action | Task |
|------|--------|------|
| `frontend/src/store/pos-cart-store.ts` | **Create** — Zustand cart store | T1 |
| `frontend/src/contexts/pos-cart-context.tsx` | **Modify** — re-export from store, keep Provider | T1 |
| `frontend/src/hooks/use-pos-cart.ts` | **Modify** — point to store selectors | T1 |
| `frontend/src/__tests__/store/pos-cart-store.test.ts` | **Create** — unit tests for store | T1 |
| `frontend/src/components/dashboard/why-changed-panel.tsx` | **Modify** — static→dynamic import | T2 |
| `frontend/sentry.client.config.ts` | **Modify** — add `tracePropagationTargets` | T3 |
| `frontend/src/lib/api-client.ts` | **Modify** — inject `sentry-trace` + `baggage` headers | T3 |
| `frontend/src/__tests__/lib/api-client.test.ts` | **Modify** — assert trace headers present | T3 |
| `frontend/src/components/dashboard-builder/widget-wrapper.tsx` | **Modify** — wrap children with ErrorBoundary | T4 |
| `frontend/src/__tests__/components/widget-wrapper.test.tsx` | **Create** — crash isolation test | T4 |
| `frontend/src/components/pos/ModalShell.tsx` | **Modify** — add focus trap | T5 |
| `frontend/package.json` | **Modify** — add `focus-trap-react` dep | T5 |
| `frontend/src/__tests__/components/pos/ModalShell.test.tsx` | **Create** — focus management tests | T5 |

---

## Task 1: Migrate POS cart from React Context to Zustand

**Why:** `pos-cart-context.tsx` uses `useReducer` + `createContext`. Every `dispatch` re-renders all 30+ consumers. Replacing with Zustand lets components subscribe to individual slices — `CartRow` only re-renders when its item changes.

**Files:**
- Create: `frontend/src/store/pos-cart-store.ts`
- Modify: `frontend/src/contexts/pos-cart-context.tsx`
- Modify: `frontend/src/hooks/use-pos-cart.ts`
- Create: `frontend/src/__tests__/store/pos-cart-store.test.ts`

- [ ] **Step 1: Install Zustand**

```bash
cd frontend && npm install zustand
```

Expected: `zustand` appears in `package.json` dependencies.

- [ ] **Step 2: Write failing tests for the store**

Create `frontend/src/__tests__/store/pos-cart-store.test.ts`:

```typescript
import { describe, it, expect, beforeEach } from "vitest";
import { usePosCartStore } from "@/store/pos-cart-store";

// Reset store between tests
beforeEach(() => {
  usePosCartStore.setState({
    items: [],
    appliedDiscount: null,
  });
});

const item = {
  drug_code: "PARA500",
  drug_name: "Paracetamol 500mg",
  batch_number: null,
  expiry_date: null,
  quantity: 1,
  unit_price: 10,
  discount: 0,
  line_total: 10,
  is_controlled: false,
};

describe("pos-cart-store", () => {
  it("adds item", () => {
    usePosCartStore.getState().addItem(item);
    expect(usePosCartStore.getState().items).toHaveLength(1);
    expect(usePosCartStore.getState().items[0].drug_code).toBe("PARA500");
  });

  it("stacks quantity for existing drug_code", () => {
    usePosCartStore.getState().addItem(item);
    usePosCartStore.getState().addItem(item);
    const items = usePosCartStore.getState().items;
    expect(items).toHaveLength(1);
    expect(items[0].quantity).toBe(2);
    expect(items[0].line_total).toBe(20);
  });

  it("removes item", () => {
    usePosCartStore.getState().addItem(item);
    usePosCartStore.getState().removeItem("PARA500");
    expect(usePosCartStore.getState().items).toHaveLength(0);
  });

  it("updates quantity and recalculates line_total", () => {
    usePosCartStore.getState().addItem(item);
    usePosCartStore.getState().updateQuantity("PARA500", 3);
    expect(usePosCartStore.getState().items[0].quantity).toBe(3);
    expect(usePosCartStore.getState().items[0].line_total).toBe(30);
  });

  it("applies discount", () => {
    const discount = { source: "voucher" as const, ref: "SAVE10", label: "SAVE10", discountAmount: 10 };
    usePosCartStore.getState().applyDiscount(discount);
    expect(usePosCartStore.getState().appliedDiscount?.ref).toBe("SAVE10");
  });

  it("clears discount", () => {
    usePosCartStore.getState().applyDiscount({ source: "voucher" as const, ref: "X", label: "X", discountAmount: 5 });
    usePosCartStore.getState().clearDiscount();
    expect(usePosCartStore.getState().appliedDiscount).toBeNull();
  });

  it("clears cart", () => {
    usePosCartStore.getState().addItem(item);
    usePosCartStore.getState().clear();
    expect(usePosCartStore.getState().items).toHaveLength(0);
    expect(usePosCartStore.getState().appliedDiscount).toBeNull();
  });

  it("subtotal derived selector sums line totals", () => {
    usePosCartStore.getState().addItem(item);
    usePosCartStore.getState().addItem({ ...item, drug_code: "IBU400", drug_name: "Ibuprofen", unit_price: 20, line_total: 20 });
    expect(usePosCartStore.getState().subtotal()).toBe(30);
  });
});
```

- [ ] **Step 3: Run tests — verify they fail**

```bash
cd frontend && npx vitest run src/__tests__/store/pos-cart-store.test.ts
```

Expected: FAIL — `Cannot find module '@/store/pos-cart-store'`

- [ ] **Step 4: Create the Zustand store**

Create `frontend/src/store/pos-cart-store.ts`:

```typescript
import { create } from "zustand";
import type { PosCartItem } from "@/types/pos";
import type { AppliedCartDiscount } from "@/contexts/pos-cart-context";

interface PosCartState {
  items: PosCartItem[];
  appliedDiscount: AppliedCartDiscount | null;

  // Actions
  addItem: (item: PosCartItem) => void;
  removeItem: (drugCode: string) => void;
  updateQuantity: (drugCode: string, quantity: number) => void;
  applyDiscount: (discount: AppliedCartDiscount) => void;
  clearDiscount: () => void;
  clear: () => void;

  // Derived selectors (called as functions so components subscribe selectively)
  subtotal: () => number;
  itemCount: () => number;
  itemDiscountTotal: () => number;   // sum of per-item discounts
  voucherDiscount: () => number;     // cart-level voucher/promo EGP amount
  discountTotal: () => number;       // itemDiscountTotal + voucherDiscount
  grandTotal: () => number;          // subtotal - discountTotal (floored at 0)
}

export const usePosCartStore = create<PosCartState>((set, get) => ({
  items: [],
  appliedDiscount: null,

  addItem: (incoming) =>
    set((state) => {
      const existing = state.items.find((i) => i.drug_code === incoming.drug_code);
      if (existing) {
        const newQty = existing.quantity + incoming.quantity;
        return {
          items: state.items.map((i) =>
            i.drug_code === incoming.drug_code
              ? { ...i, quantity: newQty, line_total: i.unit_price * newQty * (1 - i.discount / 100) }
              : i,
          ),
        };
      }
      return { items: [...state.items, incoming] };
    }),

  removeItem: (drugCode) =>
    set((state) => ({ items: state.items.filter((i) => i.drug_code !== drugCode) })),

  updateQuantity: (drugCode, quantity) =>
    set((state) => ({
      items: state.items.map((i) =>
        i.drug_code === drugCode
          ? { ...i, quantity, line_total: i.unit_price * quantity * (1 - i.discount / 100) }
          : i,
      ),
    })),

  applyDiscount: (discount) => set({ appliedDiscount: discount }),
  clearDiscount: () => set({ appliedDiscount: null }),
  clear: () => set({ items: [], appliedDiscount: null }),

  subtotal: () => get().items.reduce((sum, i) => sum + i.line_total, 0),
  itemCount: () => get().items.reduce((sum, i) => sum + i.quantity, 0),
  itemDiscountTotal: () =>
    get().items.reduce((sum, i) => sum + (i.unit_price * i.quantity - i.line_total), 0),
  voucherDiscount: () => get().appliedDiscount?.discountAmount ?? 0,
  discountTotal: () => {
    const s = get();
    return s.itemDiscountTotal() + (s.appliedDiscount?.discountAmount ?? 0);
  },
  grandTotal: () => {
    const s = get();
    return Math.max(0, s.subtotal() - s.discountTotal());
  },
}));
```

- [ ] **Step 5: Run tests — verify they pass**

```bash
cd frontend && npx vitest run src/__tests__/store/pos-cart-store.test.ts
```

Expected: PASS — 8 tests

- [ ] **Step 6: Update `use-pos-cart.ts` to read from the store**

The existing context exports `subtotal`, `discountTotal`, `voucherDiscount`, `taxTotal`, `grandTotal`, and `itemCount` as derived values. These must all come from the store so consumers still compile unchanged.

Replace the full content of `frontend/src/hooks/use-pos-cart.ts`:

```typescript
"use client";

import { usePosCartStore } from "@/store/pos-cart-store";

export function usePosCart() {
  const items = usePosCartStore((s) => s.items);
  const appliedDiscount = usePosCartStore((s) => s.appliedDiscount);
  const addItem = usePosCartStore((s) => s.addItem);
  const removeItem = usePosCartStore((s) => s.removeItem);
  const updateQuantity = usePosCartStore((s) => s.updateQuantity);
  const applyDiscount = usePosCartStore((s) => s.applyDiscount);
  const clearDiscount = usePosCartStore((s) => s.clearDiscount);
  const clear = usePosCartStore((s) => s.clear);
  const subtotal = usePosCartStore((s) => s.subtotal());
  const itemCount = usePosCartStore((s) => s.itemCount());
  const voucherDiscount = usePosCartStore((s) => s.voucherDiscount());
  const itemDiscountTotal = usePosCartStore((s) => s.itemDiscountTotal());
  const discountTotal = usePosCartStore((s) => s.discountTotal());
  const taxTotal = 0; // pharmacy items are zero-rated; extend if needed
  const grandTotal = usePosCartStore((s) => s.grandTotal());

  return {
    items,
    appliedDiscount,
    addItem,
    removeItem,
    updateQuantity,
    applyDiscount,
    clearDiscount,
    clear,
    subtotal,
    itemCount,
    voucherDiscount,
    itemDiscountTotal,
    discountTotal,
    taxTotal,
    grandTotal,
  };
}
```

- [ ] **Step 7: Update `pos-cart-context.tsx` — keep Provider for layout compatibility, wire to store**

The layout mounts `<PosCartProvider>` and `computeVoucherDiscount` is imported from this file in `terminal/page.tsx`. Keep both exports; remove the internal reducer and replace with store delegation.

Open `frontend/src/contexts/pos-cart-context.tsx`. Replace the full file content:

```typescript
"use client";

import { type ReactNode } from "react";
import { usePosCartStore } from "@/store/pos-cart-store";
import type { PosCartItem } from "@/types/pos";
import type { AppliedDiscount } from "@/types/promotions";

// ---- Voucher preview shape (public type, used by VoucherCodeModal) ----
export interface CartVoucher {
  code: string;
  discount_type: "amount" | "percent";
  value: number;
  discount: number;
}

// ---- Applied cart-level discount (public type, used by api-client callers) ----
export interface AppliedCartDiscount {
  source: AppliedDiscount["source"];
  ref: string;
  label: string;
  discountAmount: number;
}

/** Compute the EGP discount amount from a voucher against the current subtotal. */
export function computeVoucherDiscount(
  discountType: "amount" | "percent",
  value: number,
  subtotal: number,
): number {
  if (discountType === "amount") return Math.min(value, subtotal);
  return Math.round(subtotal * (value / 100) * 100) / 100;
}

/**
 * PosCartProvider — kept for layout compatibility.
 * State now lives in the Zustand store (src/store/pos-cart-store.ts);
 * this component is a transparent wrapper with no internal state.
 */
export function PosCartProvider({ children }: { children: ReactNode }) {
  return <>{children}</>;
}

// Re-export store hook for callers that import from this module
export { usePosCartStore };
export type { PosCartItem };
```

- [ ] **Step 8: Verify TypeScript compiles with no errors**

```bash
cd frontend && npx tsc --noEmit 2>&1 | grep -E "pos-cart|store/pos" | head -20
```

Expected: no output (no errors in these files)

- [ ] **Step 9: Commit**

```bash
cd C:/Users/user/Documents/GitHub/Data-Pulse
git add frontend/src/store/pos-cart-store.ts \
        frontend/src/hooks/use-pos-cart.ts \
        frontend/src/contexts/pos-cart-context.tsx \
        frontend/src/__tests__/store/pos-cart-store.test.ts \
        frontend/package.json \
        frontend/package-lock.json
git commit -m "perf(pos): migrate cart state from Context/useReducer to Zustand

Eliminates cascading re-renders on barcode scans — each component
now subscribes to its own slice via selector instead of re-rendering
on every cart action. Store is tested independently of React.

Audit report §4.1."
```

---

## Task 2: Fix waterfall-chart static import in why-changed-panel

**Why:** `why-changed-panel.tsx` statically imports `WaterfallChart`, which pulls all of Recharts into the initial JS bundle for every page that renders that panel. `widget-renderer.tsx` already lazy-loads it correctly; the static import in `why-changed-panel` defeats the split.

**Files:**
- Modify: `frontend/src/components/dashboard/why-changed-panel.tsx` (line 6)

- [ ] **Step 1: Check current bundle behaviour — record waterfall chunk name**

```bash
cd frontend && grep -n "WaterfallChart\|waterfall-chart\|dynamic" src/components/dashboard/why-changed-panel.tsx
```

Expected output:
```
6:import { WaterfallChart } from "@/components/dashboard/waterfall-chart";
```

- [ ] **Step 2: Replace static import with next/dynamic**

Open `frontend/src/components/dashboard/why-changed-panel.tsx`. Change line 6 from:

```typescript
import { WaterfallChart } from "@/components/dashboard/waterfall-chart";
```

to:

```typescript
import dynamic from "next/dynamic";

const WaterfallChart = dynamic(
  () => import("@/components/dashboard/waterfall-chart").then((m) => m.WaterfallChart),
  { ssr: false, loading: () => <div className="h-48 animate-pulse rounded-lg bg-white/5" /> },
);
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit 2>&1 | grep why-changed | head -10
```

Expected: no output

- [ ] **Step 4: Commit**

```bash
cd C:/Users/user/Documents/GitHub/Data-Pulse
git add frontend/src/components/dashboard/why-changed-panel.tsx
git commit -m "perf(dashboard): lazy-load WaterfallChart in why-changed-panel

Static import was defeating the next/dynamic split already in
widget-renderer.tsx, pulling all Recharts primitives into the
initial bundle for any page rendering the Why Changed panel.

Audit report §4.2."
```

---

## Task 3: Sentry distributed tracing — inject trace headers in api-client

**Why:** `sentry.client.config.ts` registers `browserTracingIntegration` but `tracePropagationTargets` is unset — Sentry only auto-propagates to same-origin URLs. The POS desktop calls `https://smartdatapulse.tech` cross-origin, so no `sentry-trace`/`baggage` headers are attached. Backend errors are orphaned from their frontend cause.

**Files:**
- Modify: `frontend/sentry.client.config.ts`
- Modify: `frontend/src/lib/api-client.ts`

- [ ] **Step 1: Add `tracePropagationTargets` to Sentry init**

Open `frontend/sentry.client.config.ts`. Replace the `Sentry.init({...})` block:

```typescript
import * as Sentry from "@sentry/nextjs";

const dsn = process.env.NEXT_PUBLIC_SENTRY_DSN;
const apiUrl = process.env.NEXT_PUBLIC_API_URL || "";

if (dsn) {
  Sentry.init({
    dsn,
    environment: process.env.NEXT_PUBLIC_SENTRY_ENVIRONMENT || "development",
    tracesSampleRate: process.env.NEXT_PUBLIC_SENTRY_ENVIRONMENT === "production" ? 0.1 : 1.0,
    replaysSessionSampleRate: 0,
    replaysOnErrorSampleRate: process.env.NEXT_PUBLIC_SENTRY_ENVIRONMENT === "production" ? 1.0 : 0,
    debug: false,
    // Propagate W3C trace headers to both same-origin requests and the
    // backend API (cross-origin in the POS desktop: localhost:3847 →
    // smartdatapulse.tech). This links frontend spans to their backend
    // SQL exceptions in the Sentry waterfall view.
    tracePropagationTargets: ["localhost", /^\//,  apiUrl].filter(Boolean),
    integrations: [
      Sentry.browserTracingIntegration(),
    ],
  });
}
```

- [ ] **Step 2: Inject `sentry-trace` + `baggage` headers in `_request`**

Open `frontend/src/lib/api-client.ts`. Add the Sentry import at the top (after existing imports):

```typescript
import * as Sentry from "@sentry/nextjs";
```

Then inside the `_request` function, replace the line that builds `mergedHeaders`:

```typescript
    const authHeaders = await getAuthHeaders();
    const mergedHeaders = { ...authHeaders, ...init?.headers };
```

with:

```typescript
    const authHeaders = await getAuthHeaders();
    // Inject W3C distributed trace headers so Sentry links this browser
    // fetch to the backend span that handles the same request.
    const traceData = Sentry.getTraceData();
    const mergedHeaders = { ...authHeaders, ...traceData, ...init?.headers };
```

- [ ] **Step 3: Verify TypeScript**

```bash
cd frontend && npx tsc --noEmit 2>&1 | grep -E "api-client|sentry.client" | head -10
```

Expected: no output

- [ ] **Step 4: Commit**

```bash
cd C:/Users/user/Documents/GitHub/Data-Pulse
git add frontend/sentry.client.config.ts frontend/src/lib/api-client.ts
git commit -m "feat(observability): inject W3C trace headers into API requests

Add tracePropagationTargets for cross-origin backend calls (POS
desktop: localhost:3847 → smartdatapulse.tech) and manually inject
sentry-trace + baggage via Sentry.getTraceData() in _request so
every fetch links to its backend span in the Sentry waterfall.

Audit report §5.1."
```

---

## Task 4: Per-widget micro error boundaries in dashboard builder

**Why:** A single widget crash (e.g. `churn.py` timeout) currently unmounts the entire dashboard via the top-level `ErrorBoundary` in `(pos)/layout.tsx`. Each widget should be isolated — one crash shows a retry card for that widget only; the rest keep rendering.

**Files:**
- Modify: `frontend/src/components/dashboard-builder/widget-wrapper.tsx`
- Create: `frontend/src/__tests__/components/dashboard-builder/widget-wrapper.test.tsx`

- [ ] **Step 1: Write failing test**

Create `frontend/src/__tests__/components/dashboard-builder/widget-wrapper.test.tsx`:

```typescript
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { WidgetWrapper } from "@/components/dashboard-builder/widget-wrapper";

function Bomb(): never {
  throw new Error("widget exploded");
}

describe("WidgetWrapper error isolation", () => {
  it("renders children normally when no error", () => {
    render(
      <WidgetWrapper title="Revenue" editMode={false}>
        <div>chart content</div>
      </WidgetWrapper>,
    );
    expect(screen.getByText("chart content")).toBeTruthy();
  });

  it("shows fallback when child crashes — does not propagate", () => {
    // Suppress expected console.error from React's error boundary
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => {});
    render(
      <WidgetWrapper title="Revenue" editMode={false}>
        <Bomb />
      </WidgetWrapper>,
    );
    expect(screen.queryByText("chart content")).toBeNull();
    expect(screen.getByRole("button", { name: /retry/i })).toBeTruthy();
    consoleError.mockRestore();
  });
});
```

- [ ] **Step 2: Run test — verify it fails**

```bash
cd frontend && npx vitest run src/__tests__/components/dashboard-builder/widget-wrapper.test.tsx
```

Expected: FAIL — `getByRole: Unable to find an accessible element with the role "button"` (no boundary yet)

- [ ] **Step 3: Update `widget-wrapper.tsx` to add per-widget ErrorBoundary**

Replace the full content of `frontend/src/components/dashboard-builder/widget-wrapper.tsx`:

```typescript
"use client";

import { Component, type ReactNode } from "react";
import { GripVertical, RefreshCw, X } from "lucide-react";
import { cn } from "@/lib/utils";

// ── Per-widget error boundary ─────────────────────────────────────────────
// Isolates crashes so one broken widget doesn't unmount the whole dashboard.

interface WidgetErrorState { hasError: boolean; error: Error | null }

class WidgetErrorBoundary extends Component<
  { title: string; children: ReactNode },
  WidgetErrorState
> {
  constructor(props: { title: string; children: ReactNode }) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): WidgetErrorState {
    return { hasError: true, error };
  }

  render() {
    if (!this.state.hasError) return this.props.children;
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3 p-4 text-center">
        <p className="text-xs text-text-secondary">
          <span className="font-medium text-text-primary">{this.props.title}</span>
          {" "}failed to load
        </p>
        <button
          aria-label="retry"
          onClick={() => this.setState({ hasError: false, error: null })}
          className="flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-xs text-text-secondary hover:border-accent hover:text-accent"
        >
          <RefreshCw className="h-3 w-3" />
          Retry
        </button>
      </div>
    );
  }
}

// ── Widget wrapper ────────────────────────────────────────────────────────

interface WidgetWrapperProps {
  children: ReactNode;
  title: string;
  editMode: boolean;
  onRemove?: () => void;
  className?: string;
}

export function WidgetWrapper({
  children,
  title,
  editMode,
  onRemove,
  className,
}: WidgetWrapperProps) {
  return (
    <div
      className={cn(
        "h-full rounded-xl border border-border bg-card overflow-hidden",
        editMode && "ring-2 ring-accent/20 ring-dashed",
        className,
      )}
    >
      {editMode && (
        <div className="flex items-center justify-between bg-divider/50 px-3 py-1.5 cursor-move drag-handle">
          <div className="flex items-center gap-1.5 text-xs text-text-secondary">
            <GripVertical className="h-3.5 w-3.5" />
            <span>{title}</span>
          </div>
          {onRemove && (
            <button
              onClick={onRemove}
              className="rounded p-0.5 text-text-secondary hover:bg-growth-red/10 hover:text-growth-red"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
      )}
      <div className={cn("p-4", editMode && "pointer-events-none opacity-80")}>
        <WidgetErrorBoundary title={title}>
          {children}
        </WidgetErrorBoundary>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run test — verify it passes**

```bash
cd frontend && npx vitest run src/__tests__/components/dashboard-builder/widget-wrapper.test.tsx
```

Expected: PASS — 2 tests

- [ ] **Step 5: Commit**

```bash
cd C:/Users/user/Documents/GitHub/Data-Pulse
git add frontend/src/components/dashboard-builder/widget-wrapper.tsx \
        frontend/src/__tests__/components/dashboard-builder/widget-wrapper.test.tsx
git commit -m "feat(dashboard): per-widget error boundary in WidgetWrapper

Each widget now catches its own crash and shows a Retry card
instead of unmounting the whole dashboard grid. Class component
required — getDerivedStateFromError is not available to hooks.

Audit report §5.2."
```

---

## Task 5: Focus trapping in POS modals via ModalShell

**Why:** `ModalShell` is the base wrapper for VoucherCodeModal, InsuranceModal, and PromotionsModal. All three have `role="dialog"` + `aria-modal="true"` but no focus capture — the cashier can Tab out of an active modal into obfuscated background elements. WCAG 2.1 §2.1.2 (No Keyboard Trap... for *dialogs*, focus must stay inside). `InvoiceModal` uses a different base but the same pattern.

**Strategy:** Add focus trap to `ModalShell` (covers 3 modals at once). Add focus trap to `InvoiceModal` directly (uses its own scaffold). Both use `focus-trap-react`.

**Files:**
- Modify: `frontend/package.json` (add dep)
- Modify: `frontend/src/components/pos/ModalShell.tsx`
- Modify: `frontend/src/components/pos/InvoiceModal.tsx`
- Create: `frontend/src/__tests__/components/pos/ModalShell.test.tsx`

- [ ] **Step 1: Install focus-trap-react**

```bash
cd frontend && npm install focus-trap-react
```

Expected: `focus-trap-react` appears in `package.json` dependencies.

- [ ] **Step 2: Write failing test**

Create `frontend/src/__tests__/components/pos/ModalShell.test.tsx`:

```typescript
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ModalShell } from "@/components/pos/ModalShell";
import { Ticket } from "lucide-react";

const defaultProps = {
  open: true,
  onClose: vi.fn(),
  title: "Test Modal",
  icon: <Ticket />,
};

describe("ModalShell focus trap", () => {
  it("does not render when closed", () => {
    render(<ModalShell {...defaultProps} open={false}><button>inside</button></ModalShell>);
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("renders dialog with aria-modal when open", () => {
    render(<ModalShell {...defaultProps}><button>inside</button></ModalShell>);
    const dialog = screen.getByRole("dialog");
    expect(dialog.getAttribute("aria-modal")).toBe("true");
  });

  it("calls onClose when Escape is pressed", async () => {
    const onClose = vi.fn();
    render(<ModalShell {...defaultProps} onClose={onClose}><button>inside</button></ModalShell>);
    await userEvent.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
```

- [ ] **Step 3: Run test — verify it passes without changes (baseline)**

```bash
cd frontend && npx vitest run src/__tests__/components/pos/ModalShell.test.tsx
```

Expected: PASS — 3 tests (the tests check existing behaviour; the focus-trap change must not break them)

- [ ] **Step 4: Add FocusTrap to ModalShell**

Open `frontend/src/components/pos/ModalShell.tsx`. Add the import after the existing imports:

```typescript
import FocusTrap from "focus-trap-react";
```

Then wrap the inner `<div onClick={(e) => e.stopPropagation()} ...>` with `<FocusTrap>`. Find the block that starts with `<div onClick={(e) => e.stopPropagation()}` and ends with `</div>` (the paper element) and wrap it:

```typescript
      <FocusTrap
        focusTrapOptions={{
          escapeDeactivates: false, // we handle Escape ourselves via the keydown listener
          allowOutsideClick: true,  // backdrop click must still reach the backdrop handler
          initialFocus: false,      // don't steal focus from typed input on open
        }}
      >
        <div
          onClick={(e) => e.stopPropagation()}
          // ... existing styles unchanged ...
        >
          {/* existing content unchanged */}
        </div>
      </FocusTrap>
```

- [ ] **Step 5: Add FocusTrap to InvoiceModal**

Open `frontend/src/components/pos/InvoiceModal.tsx`. Add the import:

```typescript
import FocusTrap from "focus-trap-react";
```

Find the outermost `<div role="dialog" ...>` (line ~128) and wrap its inner paper `<div>` with:

```typescript
<FocusTrap
  focusTrapOptions={{
    escapeDeactivates: false,
    allowOutsideClick: true,
    initialFocus: "[data-autofocus]",
  }}
>
  {/* inner paper div — unchanged */}
</FocusTrap>
```

Also add `data-autofocus` to the Print button so initial focus lands there:

```typescript
<button
  data-autofocus
  onClick={() => window.print()}
  // ... rest of props unchanged
>
  Print
</button>
```

- [ ] **Step 6: Run tests — verify they still pass**

```bash
cd frontend && npx vitest run src/__tests__/components/pos/ModalShell.test.tsx
```

Expected: PASS — 3 tests

- [ ] **Step 7: TypeScript check**

```bash
cd frontend && npx tsc --noEmit 2>&1 | grep -E "ModalShell|InvoiceModal|focus-trap" | head -10
```

Expected: no output

- [ ] **Step 8: Commit**

```bash
cd C:/Users/user/Documents/GitHub/Data-Pulse
git add frontend/src/components/pos/ModalShell.tsx \
        frontend/src/components/pos/InvoiceModal.tsx \
        frontend/src/__tests__/components/pos/ModalShell.test.tsx \
        frontend/package.json \
        frontend/package-lock.json
git commit -m "feat(a11y): add focus trap to POS modals (ModalShell + InvoiceModal)

Cashier can no longer Tab out of an active modal into obfuscated
background elements. Covers VoucherCodeModal, InsuranceModal,
PromotionsModal (via ModalShell) and InvoiceModal directly.
InvoiceModal initial focus lands on the Print button.

WCAG 2.1 §2.1.2 / Audit report §6.1."
```

---

## Final verification

- [ ] **Full TypeScript check**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -20
```

Expected: no output

- [ ] **Run all unit tests**

```bash
cd frontend && npx vitest run --reporter=verbose 2>&1 | tail -20
```

Expected: all pass, 0 failures

- [ ] **Ruff checks (backend unchanged, but verify no accidental touches)**

```bash
cd C:/Users/user/Documents/GitHub/Data-Pulse && ruff format --check src/ && ruff check src/
```

Expected: no output

---

## Deferred (separate plans)

| Item | Recommended next step |
|------|-----------------------|
| Async SQLAlchemy + asyncpg (§2.1) | New plan: `2026-xx-xx-async-db-migration.md`. Migrate `core/db.py` + `core/db_session.py`; test with asyncpg in CI; add `NullPool` + `statement_cache_size=0` for PgBouncer compat. |
| Distributed task queue (§2.2) | New plan: `2026-xx-xx-arq-task-queue.md`. Replace `async_executor.py` in-process pool with Arq workers backed by Redis; bridge `backpressure.py` saturation signal to queue depth. |
