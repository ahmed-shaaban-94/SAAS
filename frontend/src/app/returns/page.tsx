"use client";

/**
 * /returns — Returns Analysis on the v2 shell.
 *
 * Migrated from `(app)/returns/page.tsx`. KPIs: total returns value,
 * return count, average return rate, return quantity — all pulled from
 * the existing `/api/v1/analytics/returns/trend` aggregate so no new
 * backend work is needed.
 */

import { useMemo } from "react";
import { Undo2, ListChecks, Percent, Boxes, TrendingDown } from "lucide-react";

import { DashboardShell } from "@/components/dashboard-v2/shell";
import { FilterBar } from "@/components/filters/filter-bar";
import { KpiCard, type KpiColor, type KpiDir } from "@/components/dashboard/new";
import { ReturnsOverview } from "@/components/returns/returns-overview";
import { ReturnsTrendChart } from "@/components/returns/returns-trend-chart";
import { ReturnRateGauge } from "@/components/returns/return-rate-gauge";
import { AnalyticsSectionHeader } from "@/components/layout/analytics-section-header";
import { LoadingCard } from "@/components/loading-card";
import { useFilters } from "@/contexts/filter-context";
import { useReturnsTrend } from "@/hooks/use-returns-trend";
import { useReturns } from "@/hooks/use-returns";
import { formatCurrency, formatNumber } from "@/lib/formatters";

function trendToSparkline(values: number[]): number[] {
  if (!values.length) return [];
  const max = Math.max(...values, 1);
  return values.map((v) => 32 - (v / max) * 28);
}

export default function ReturnsPage() {
  const { filters } = useFilters();
  const { data: trend, isLoading: trendLoading } = useReturnsTrend();
  const { data: returns, isLoading: returnsLoading } = useReturns(filters);

  const kpiLoading = trendLoading || returnsLoading;

  const kpis = useMemo(() => {
    if (!trend && !returns) return null;
    const totalValue = trend?.total_return_amount ?? 0;
    const totalCount = trend?.total_returns ?? 0;
    const avgRate = trend?.avg_return_rate ?? 0;
    const totalQty = (returns ?? []).reduce((s, r) => s + r.return_quantity, 0);

    const sparkValues = trend?.points.map((p) => p.return_amount) ?? [];

    return [
      {
        id: "value",
        label: "Total Returns Value",
        value: formatCurrency(totalValue),
        delta: { dir: "down" as KpiDir, text: "revenue reversed" },
        sub: "across all return records",
        color: "red" as KpiColor,
        sparkline: trendToSparkline(sparkValues),
        icon: Undo2,
      },
      {
        id: "count",
        label: "Return Events",
        value: formatNumber(totalCount),
        delta: { dir: "down" as KpiDir, text: `${(returns ?? []).length} detail rows` },
        sub: "distinct return transactions",
        color: "purple" as KpiColor,
        sparkline: [] as number[],
        icon: ListChecks,
      },
      {
        id: "rate",
        label: "Avg Return Rate",
        value: `${(avgRate * 100).toFixed(1)}%`,
        delta: {
          dir: (avgRate < 0.02 ? "up" : "down") as KpiDir,
          text: avgRate < 0.02 ? "under 2%" : "watch closely",
        },
        sub: "of gross revenue returned",
        color: "amber" as KpiColor,
        sparkline: [] as number[],
        icon: Percent,
      },
      {
        id: "qty",
        label: "Return Quantity",
        value: formatNumber(totalQty),
        delta: { dir: "down" as KpiDir, text: "units" },
        sub: "total product units returned",
        color: "accent" as KpiColor,
        sparkline: [] as number[],
        icon: Boxes,
      },
    ];
  }, [trend, returns]);

  return (
    <DashboardShell
      activeHref="/returns"
      breadcrumbs={[
        { label: "DataPulse", href: "/dashboard" },
        { label: "Operations" },
        { label: "Returns" },
      ]}
    >
      <div className="page">
        <div>
          <h1 className="page-title">Returns.</h1>
          <p className="page-sub">
            Product returns, refund value, and return-rate trend across customers and branches.
          </p>
        </div>

        <section
          className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4"
          aria-label="Returns KPIs"
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

        <ReturnsOverview hideSummary />

        <div style={{ marginTop: 24 }}>
          <AnalyticsSectionHeader
            title="Returns Trend"
            icon={TrendingDown}
            accentClassName="text-growth-red"
          />
          <div className="grid gap-6 lg:grid-cols-3">
            <div className="lg:col-span-2">
              <ReturnsTrendChart />
            </div>
            <ReturnRateGauge />
          </div>
        </div>
      </div>
    </DashboardShell>
  );
}
