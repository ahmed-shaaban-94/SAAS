"use client";

/**
 * /sites — Site Comparison on the v2 shell.
 *
 * Migrated from `(app)/sites/page.tsx`. KPIs: network revenue, active
 * branches, top-branch share, spread (top ÷ bottom) as a concentration
 * signal.
 */

import { useMemo } from "react";
import { Building2, Store, Crown, Ratio, Radar } from "lucide-react";

import { DashboardShell } from "@/components/dashboard-v2/shell";
import { FilterBar } from "@/components/filters/filter-bar";
import { KpiCard, type KpiColor, type KpiDir } from "@/components/dashboard/new";
import { SiteOverview } from "@/components/sites/site-overview";
import { RadarComparison } from "@/components/sites/radar-comparison";
import { AnalyticsSectionHeader } from "@/components/layout/analytics-section-header";
import { LoadingCard } from "@/components/loading-card";
import { useFilters } from "@/contexts/filter-context";
import { useSites } from "@/hooks/use-sites";
import { useDailyTrend } from "@/hooks/use-daily-trend";
import { formatCurrency, formatNumber } from "@/lib/formatters";
import type { TimeSeriesPoint } from "@/types/api";

function toSparkline(points: TimeSeriesPoint[] | undefined): number[] {
  if (!points?.length) return [];
  const values = points.map((p) => Number(p.value) || 0);
  const max = Math.max(...values, 1);
  return values.map((v) => 32 - (v / max) * 28);
}

export default function SitesPage() {
  const { filters } = useFilters();
  const { data: sites, isLoading: sitesLoading } = useSites(filters);
  const { data: dailyTrend, isLoading: trendLoading } = useDailyTrend(filters);

  const kpiLoading = sitesLoading || trendLoading;

  const kpis = useMemo(() => {
    if (!sites) return null;
    const top = sites.items[0];
    const bottom = sites.items[sites.items.length - 1];
    const growthPct = dailyTrend?.growth_pct;
    const growthDir: KpiDir = (growthPct ?? 0) >= 0 ? "up" : "down";

    const spreadRatio =
      top && bottom && bottom.value > 0 ? top.value / bottom.value : null;

    return [
      {
        id: "revenue",
        label: "Network Revenue",
        value: formatCurrency(sites.total),
        delta:
          growthPct != null
            ? { dir: growthDir, text: `${growthPct > 0 ? "+" : ""}${growthPct.toFixed(1)}%` }
            : { dir: "up" as KpiDir, text: "—" },
        sub: growthPct != null ? "vs previous period" : "no comparison available",
        color: "accent" as KpiColor,
        sparkline: toSparkline(dailyTrend?.points),
        icon: Building2,
      },
      {
        id: "branches",
        label: "Active Branches",
        value: formatNumber(sites.active_count ?? sites.items.length),
        delta: { dir: "up" as KpiDir, text: "all reporting" },
        sub: "with sales in period",
        color: "purple" as KpiColor,
        sparkline: [] as number[],
        icon: Store,
      },
      {
        id: "top-branch",
        label: "Top Branch Share",
        value: top ? `${top.pct_of_total.toFixed(1)}%` : "—",
        delta: top
          ? { dir: "up" as KpiDir, text: formatCurrency(top.value) }
          : { dir: "up" as KpiDir, text: "—" },
        sub: top ? top.name : "no site data",
        color: "amber" as KpiColor,
        sparkline: [] as number[],
        icon: Crown,
      },
      {
        id: "spread",
        label: "Top/Bottom Spread",
        value: spreadRatio != null ? `${spreadRatio.toFixed(1)}×` : "—",
        delta: {
          dir: ((spreadRatio ?? 0) < 3 ? "up" : "down") as KpiDir,
          text: spreadRatio != null && spreadRatio >= 3 ? "imbalanced" : "healthy",
        },
        sub: "top branch vs bottom branch revenue",
        color: "red" as KpiColor,
        sparkline: [] as number[],
        icon: Ratio,
      },
    ];
  }, [sites, dailyTrend]);

  return (
    <DashboardShell
      activeHref="/sites"
      breadcrumbs={[
        { label: "DataPulse", href: "/dashboard" },
        { label: "Operations" },
        { label: "Sites" },
      ]}
    >
      <div className="page">
        <div>
          <h1 className="page-title">Sites.</h1>
          <p className="page-sub">
            Branch performance across the network — revenue, concentration, and multi-dimensional comparison.
          </p>
        </div>

        <section
          className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4"
          aria-label="Site KPIs"
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

        <SiteOverview hideSummary />

        <div style={{ marginTop: 24 }}>
          <AnalyticsSectionHeader title="Multi-Dimensional Comparison" icon={Radar} />
          <RadarComparison />
        </div>
      </div>
    </DashboardShell>
  );
}
