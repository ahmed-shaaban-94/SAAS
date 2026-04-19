"use client";

/**
 * /inventory — operations inventory page on the v2 shell.
 *
 * This is the in-place cutover from v1 `(app)/inventory` + the
 * `/inventory-v2` preview. The preview route is retired and redirected
 * here by `next.config.mjs`.
 *
 * Feature-parity audit vs v1 `(app)/inventory/page.tsx`:
 *   - Breadcrumbs → replaced by <DashboardShell breadcrumbs={...}>
 *   - Header → replaced by <h1 className="page-title"> + <p className="page-sub">
 *   - PageTransition → v2 shell has its own entry feel
 *   - FilterBar → PORTED (drives date-range filters via FilterProvider)
 *   - OpsSuiteNav → DROPPED (v2 left sidebar already navigates between
 *     ops pages; keeping a horizontal sub-nav would duplicate the UX)
 *
 * The /inventory/[drug_code] detail page stays on the (app) layout for
 * now — it is a drill-down surface. Migrating it is a follow-up.
 */

import dynamic from "next/dynamic";

import { DashboardShell } from "@/components/dashboard-v2/shell";
import { InventoryOverview } from "@/components/inventory/inventory-overview";
import { FilterBar } from "@/components/filters/filter-bar";
import { LoadingCard } from "@/components/loading-card";

const StockLevelTable = dynamic(
  () =>
    import("@/components/inventory/stock-level-table").then((m) => ({
      default: m.StockLevelTable,
    })),
  { loading: () => <LoadingCard lines={8} />, ssr: false },
);

const StockMovementChart = dynamic(
  () =>
    import("@/components/inventory/stock-movement-chart").then((m) => ({
      default: m.StockMovementChart,
    })),
  { loading: () => <LoadingCard lines={4} />, ssr: false },
);

const ReorderAlertsList = dynamic(
  () =>
    import("@/components/inventory/reorder-alerts-list").then((m) => ({
      default: m.ReorderAlertsList,
    })),
  { loading: () => <LoadingCard lines={4} />, ssr: false },
);

export default function InventoryPage() {
  return (
    <DashboardShell
      activeHref="/inventory"
      breadcrumbs={[
        { label: "DataPulse", href: "/dashboard" },
        { label: "Operations" },
        { label: "Inventory" },
      ]}
    >
      <div className="page">
        <div>
          <h1 className="page-title">Inventory.</h1>
          <p className="page-sub">
            Stock levels, movement activity, and reorder risk across every
            branch — one surface, same chrome as the overview.
          </p>
        </div>

        <FilterBar />

        <InventoryOverview />

        <div className="widget-grid">
          <StockMovementChart />
          <ReorderAlertsList />
        </div>

        <div style={{ marginTop: 24 }}>
          <StockLevelTable />
        </div>
      </div>
    </DashboardShell>
  );
}
