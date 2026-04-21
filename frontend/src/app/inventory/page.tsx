"use client";

/**
 * /inventory — operations inventory page on the v2 shell.
 *
 * Pharma Ops batch (Apr 2026): replaced the StatCard-based
 * `InventoryOverview` with a 4-tile `KpiCard` grid matching /dashboard,
 * /products, /customers, /staff, /sites, /returns. KPIs bind to existing
 * hooks — no new backend work.
 *
 * The /inventory/[drug_code] detail page stays on the (app) layout for
 * now — it is a drill-down surface. Migrating it is a follow-up.
 */

import { useMemo } from "react";
import dynamic from "next/dynamic";
import { Boxes, AlertTriangle, ShoppingCart, Package } from "lucide-react";

import { DashboardShell } from "@/components/dashboard-v2/shell";
import { FilterBar } from "@/components/filters/filter-bar";
import { KpiCard, type KpiColor, type KpiDir } from "@/components/dashboard/new";
import { LoadingCard } from "@/components/loading-card";
import { useFilters } from "@/contexts/filter-context";
import { useReorderAlerts } from "@/hooks/use-reorder-alerts";
import { useStockLevels } from "@/hooks/use-stock-levels";
import { useStockValuation } from "@/hooks/use-stock-valuation";
import { formatCurrency, formatNumber } from "@/lib/formatters";

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
  const { filters } = useFilters();
  const stockLevels = useStockLevels(filters);
  const reorderAlerts = useReorderAlerts(filters);
  const valuation = useStockValuation(filters);

  const kpiLoading = stockLevels.isLoading || reorderAlerts.isLoading || valuation.isLoading;

  const kpis = useMemo(() => {
    const totalStockValue = (valuation.data ?? []).reduce(
      (sum, item) => sum + item.stock_value,
      0,
    );
    const alerts = reorderAlerts.data ?? [];
    const belowReorder = alerts.length;
    const stockoutCount = alerts.filter((item) => item.current_quantity <= 0).length;
    const trackedItems = stockLevels.data?.length ?? 0;

    return [
      {
        id: "stock-value",
        label: "Total Stock Value",
        value: formatCurrency(totalStockValue),
        delta: { dir: "up" as KpiDir, text: "on-hand valuation" },
        sub: "across all branches",
        color: "accent" as KpiColor,
        sparkline: [] as number[],
        icon: Boxes,
      },
      {
        id: "below-reorder",
        label: "Below Reorder Point",
        value: formatNumber(belowReorder),
        delta: {
          dir: (belowReorder === 0 ? "up" : "down") as KpiDir,
          text: belowReorder === 0 ? "all healthy" : "needs action",
        },
        sub: "SKU-branch pairs",
        color: "amber" as KpiColor,
        sparkline: [] as number[],
        icon: AlertTriangle,
      },
      {
        id: "stockouts",
        label: "Stockouts",
        value: formatNumber(stockoutCount),
        delta: {
          dir: (stockoutCount === 0 ? "up" : "down") as KpiDir,
          text: stockoutCount === 0 ? "no stockouts" : "lost sales risk",
        },
        sub: "SKUs with zero on-hand",
        color: "red" as KpiColor,
        sparkline: [] as number[],
        icon: ShoppingCart,
      },
      {
        id: "tracked",
        label: "Tracked SKUs",
        value: formatNumber(trackedItems),
        delta: { dir: "up" as KpiDir, text: "in stock ledger" },
        sub: "unique drug × branch pairs",
        color: "purple" as KpiColor,
        sparkline: [] as number[],
        icon: Package,
      },
    ];
  }, [reorderAlerts.data, stockLevels.data, valuation.data]);

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

        <section
          className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4"
          aria-label="Inventory KPIs"
        >
          {kpiLoading
            ? Array.from({ length: 4 }).map((_, i) => (
                <LoadingCard key={i} lines={3} className="h-[168px]" />
              ))
            : kpis.map((k) => (
                <KpiCard
                  key={k.id}
                  label={k.label}
                  value={k.value}
                  delta={k.delta}
                  sub={k.sub}
                  color={k.color}
                  sparkline={k.sparkline}
                  icon={k.icon}
                />
              ))}
        </section>

        <FilterBar />

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
