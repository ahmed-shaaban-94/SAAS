"use client";

/**
 * Inventory v2 — preview of the hybrid operations inventory page.
 *
 * Composition:
 *   - Shell (sidebar + pulse bar) shared with /dashboard — same chrome
 *   - Inventory overview KPIs
 *   - Stock-movement chart + reorder alerts (two-column)
 *   - Stock-level table (full width)
 *
 * Proof-of-concept for the uniform-chrome promise: the same DashboardShell
 * wrapping a different page type renders consistently. Widgets are the real,
 * production-wired components from /(app)/inventory.
 */

import dynamic from "next/dynamic";
import { DashboardShell } from "@/components/dashboard-v2/shell";
import { InventoryOverview } from "@/components/inventory/inventory-overview";
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

export default function InventoryV2Page() {
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
