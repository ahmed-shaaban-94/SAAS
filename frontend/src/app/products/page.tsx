"use client";

/**
 * /products — Product Analytics on the v2 shell.
 *
 * Migrated from `(app)/products/page.tsx` as part of the UI-unification
 * sprint. The visual language matches `/dashboard` (Daily Operations
 * Overview): `KpiCard` from the design-handoff kit plus `DashboardShell`
 * chrome. KPIs are domain-specific for products (total revenue, SKU
 * count, top-product share, Pareto concentration) rather than a copy of
 * the dashboard's 4 headline metrics.
 *
 * Feature-parity audit vs v1 `(app)/products/page.tsx`:
 *   - Breadcrumbs → replaced by <DashboardShell breadcrumbs={...}>
 *   - Header → replaced by <h1 className="page-title"> + <p className="page-sub">
 *   - PageTransition → DashboardShell has its own entry feel
 *   - FilterBar → PORTED (drives filters for all hooks on the page)
 *   - View switcher (Ranking / Category) → PORTED
 *   - ProductOverview — rendered with hideSummary so its legacy
 *     SummaryStats row doesn't duplicate the new KpiCard grid
 *   - ABC / Pareto section → PORTED
 *
 * The /products/[key] detail page stays on the (app) layout for now.
 */

import { useMemo, useState } from "react";
import { BarChart3, FolderTree, Boxes, Crown, LayoutGrid } from "lucide-react";

import { DashboardShell } from "@/components/dashboard-v2/shell";
import { FilterBar } from "@/components/filters/filter-bar";
import { KpiCard, type KpiColor, type KpiDir } from "@/components/dashboard/new";
import { ProductOverview } from "@/components/products/product-overview";
import { ProductHierarchyView } from "@/components/products/product-hierarchy";
import { ParetoChart } from "@/components/products/pareto-chart";
import { ABCSummary } from "@/components/products/abc-summary";
import { AnalyticsSectionHeader } from "@/components/layout/analytics-section-header";
import { LoadingCard } from "@/components/loading-card";
import { useFilters } from "@/contexts/filter-context";
import { useTopProducts } from "@/hooks/use-top-products";
import { useDailyTrend } from "@/hooks/use-daily-trend";
import { useABCAnalysis } from "@/hooks/use-abc-analysis";
import { formatCurrency, formatNumber } from "@/lib/formatters";
import { cn } from "@/lib/utils";
import type { TimeSeriesPoint } from "@/types/api";

const VIEWS = [
  { key: "ranking" as const, label: "Ranking", icon: BarChart3 },
  { key: "hierarchy" as const, label: "Category / Brand", icon: FolderTree },
];

/**
 * Transform a raw time-series into the inverted 0-40 viewBox the KpiCard
 * sparkline expects (smaller y = higher value). Same helper pattern as
 * `/dashboard/page.tsx` so the visuals stay consistent.
 */
function toSparkline(points: TimeSeriesPoint[] | undefined): number[] {
  if (!points?.length) return [];
  const values = points.map((p) => Number(p.value) || 0);
  const max = Math.max(...values, 1);
  return values.map((v) => 32 - (v / max) * 28);
}

export default function ProductsPage() {
  const [view, setView] = useState<"ranking" | "hierarchy">("ranking");
  const { filters } = useFilters();

  const { data: topProducts, isLoading: topLoading } = useTopProducts(filters);
  const { data: dailyTrend, isLoading: trendLoading } = useDailyTrend(filters);
  const { data: abc, isLoading: abcLoading } = useABCAnalysis("product");

  const kpiLoading = topLoading || trendLoading || abcLoading;

  const kpis = useMemo(() => {
    if (!topProducts) return null;
    const topProduct = topProducts.items[0];
    const revenueTrendSparkline = toSparkline(dailyTrend?.points);
    const growthPct = dailyTrend?.growth_pct;
    const growthDir: KpiDir = (growthPct ?? 0) >= 0 ? "up" : "down";
    const classACount = abc?.class_a_count ?? 0;
    const classAShare = abc?.class_a_pct ?? 0;

    return [
      {
        id: "revenue",
        label: "Total Revenue",
        value: formatCurrency(topProducts.total),
        delta:
          growthPct != null
            ? {
                dir: growthDir,
                text: `${growthPct > 0 ? "+" : ""}${growthPct.toFixed(1)}%`,
              }
            : { dir: "up" as KpiDir, text: "—" },
        sub: growthPct != null ? "vs previous period" : "no comparison available",
        color: "accent" as KpiColor,
        sparkline: revenueTrendSparkline,
        icon: BarChart3,
      },
      {
        id: "active-skus",
        label: "Active SKUs",
        value: formatNumber(topProducts.active_count ?? topProducts.items.length),
        delta: { dir: "up" as KpiDir, text: `Top ${topProducts.items.length}` },
        sub: "with sales in period",
        color: "purple" as KpiColor,
        sparkline: [] as number[],
        icon: Boxes,
      },
      {
        id: "top-product-share",
        label: "Top Product Share",
        value: topProduct ? `${topProduct.pct_of_total.toFixed(1)}%` : "—",
        delta: topProduct
          ? { dir: "up" as KpiDir, text: formatCurrency(topProduct.value) }
          : { dir: "up" as KpiDir, text: "—" },
        sub: topProduct ? topProduct.name : "no product data",
        color: "amber" as KpiColor,
        sparkline: [] as number[],
        icon: Crown,
      },
      {
        id: "pareto",
        label: "Pareto 80/20 (Class A)",
        value: `${classAShare.toFixed(0)}%`,
        delta: { dir: "up" as KpiDir, text: `${classACount} SKUs` },
        sub: "drive the top 80% of revenue",
        color: "red" as KpiColor,
        sparkline: [] as number[],
        icon: LayoutGrid,
      },
    ];
  }, [topProducts, dailyTrend, abc]);

  return (
    <DashboardShell
      activeHref="/products"
      breadcrumbs={[
        { label: "DataPulse", href: "/dashboard" },
        { label: "Operations" },
        { label: "Products" },
      ]}
    >
      <div className="page">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h1 className="page-title">Products.</h1>
            <p className="page-sub">
              Revenue, SKU activity, and Pareto concentration across the full catalog.
            </p>
          </div>
          <div className="viz-panel-soft flex gap-1 rounded-2xl p-1 self-start">
            {VIEWS.map((v) => (
              <button
                key={v.key}
                onClick={() => setView(v.key)}
                className={cn(
                  "flex items-center gap-1.5 rounded-xl px-3 py-1.5 text-xs font-medium transition-all",
                  view === v.key
                    ? "bg-accent/20 text-accent shadow-[0_10px_24px_rgba(0,199,242,0.18)]"
                    : "text-text-secondary hover:text-text-primary",
                )}
              >
                <v.icon className="h-3.5 w-3.5" />
                {v.label}
              </button>
            ))}
          </div>
        </div>

        <section
          className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4"
          aria-label="Product KPIs"
        >
          {kpiLoading || !kpis
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

        {view === "ranking" ? <ProductOverview hideSummary /> : <ProductHierarchyView />}

        <div style={{ marginTop: 24 }}>
          <AnalyticsSectionHeader title="ABC / Pareto Analysis" icon={BarChart3} />
          <div className="grid gap-4 md:grid-cols-2 md:gap-6 lg:grid-cols-3">
            <div className="md:col-span-2">
              <ParetoChart />
            </div>
            <ABCSummary />
          </div>
        </div>
      </div>
    </DashboardShell>
  );
}
