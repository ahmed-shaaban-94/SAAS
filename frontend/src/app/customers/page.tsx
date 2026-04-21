"use client";

/**
 * /customers — Customer Intelligence on the v2 shell.
 *
 * Migrated from `(app)/customers/page.tsx` as part of the UI-unification
 * sprint. Same visual language as `/dashboard` and `/products`.
 */

import { useMemo } from "react";
import { Users, UserCheck, Crown, HeartPulse } from "lucide-react";

import { DashboardShell } from "@/components/dashboard-v2/shell";
import { FilterBar } from "@/components/filters/filter-bar";
import { KpiCard, type KpiColor, type KpiDir } from "@/components/dashboard/new";
import { CustomerOverview } from "@/components/customers/customer-overview";
import { RFMMatrix } from "@/components/customers/rfm-matrix";
import { SegmentFunnel } from "@/components/customers/segment-funnel";
import { AnalyticsSectionHeader } from "@/components/layout/analytics-section-header";
import { LoadingCard } from "@/components/loading-card";
import { useFilters } from "@/contexts/filter-context";
import { useTopCustomers } from "@/hooks/use-top-customers";
import { useDailyTrend } from "@/hooks/use-daily-trend";
import { useAtRiskCustomers } from "@/hooks/use-customer-health";
import { formatCurrency, formatNumber } from "@/lib/formatters";
import type { TimeSeriesPoint } from "@/types/api";

function toSparkline(points: TimeSeriesPoint[] | undefined): number[] {
  if (!points?.length) return [];
  const values = points.map((p) => Number(p.value) || 0);
  const max = Math.max(...values, 1);
  return values.map((v) => 32 - (v / max) * 28);
}

export default function CustomersPage() {
  const { filters } = useFilters();
  const { data: topCustomers, isLoading: topLoading } = useTopCustomers(filters);
  const { data: dailyTrend, isLoading: trendLoading } = useDailyTrend(filters);
  const { data: atRisk, isLoading: atRiskLoading } = useAtRiskCustomers(100);

  const kpiLoading = topLoading || trendLoading || atRiskLoading;

  const kpis = useMemo(() => {
    if (!topCustomers) return null;
    const top = topCustomers.items[0];
    const growthPct = dailyTrend?.growth_pct;
    const growthDir: KpiDir = (growthPct ?? 0) >= 0 ? "up" : "down";
    const atRiskCount = atRisk?.length ?? 0;

    return [
      {
        id: "revenue",
        label: "Total Customer Revenue",
        value: formatCurrency(topCustomers.total),
        delta:
          growthPct != null
            ? { dir: growthDir, text: `${growthPct > 0 ? "+" : ""}${growthPct.toFixed(1)}%` }
            : { dir: "up" as KpiDir, text: "—" },
        sub: growthPct != null ? "vs previous period" : "no comparison available",
        color: "accent" as KpiColor,
        sparkline: toSparkline(dailyTrend?.points),
        icon: Users,
      },
      {
        id: "active",
        label: "Active Customers",
        value: formatNumber(topCustomers.active_count ?? topCustomers.items.length),
        delta: { dir: "up" as KpiDir, text: `Top ${topCustomers.items.length}` },
        sub: "with purchases in period",
        color: "purple" as KpiColor,
        sparkline: [] as number[],
        icon: UserCheck,
      },
      {
        id: "top-share",
        label: "Top Customer Share",
        value: top ? `${top.pct_of_total.toFixed(1)}%` : "—",
        delta: top
          ? { dir: "up" as KpiDir, text: formatCurrency(top.value) }
          : { dir: "up" as KpiDir, text: "—" },
        sub: top ? top.name : "no customer data",
        color: "amber" as KpiColor,
        sparkline: [] as number[],
        icon: Crown,
      },
      {
        id: "at-risk",
        label: "At-Risk Customers",
        value: formatNumber(atRiskCount),
        delta: { dir: "down" as KpiDir, text: "needs attention" },
        sub: "from health scoring",
        color: "red" as KpiColor,
        sparkline: [] as number[],
        icon: HeartPulse,
      },
    ];
  }, [topCustomers, dailyTrend, atRisk]);

  return (
    <DashboardShell
      activeHref="/customers"
      breadcrumbs={[
        { label: "DataPulse", href: "/dashboard" },
        { label: "Operations" },
        { label: "Customers" },
      ]}
    >
      <div className="page">
        <div>
          <h1 className="page-title">Customers.</h1>
          <p className="page-sub">
            Revenue contribution, segmentation, and churn risk across the customer base.
          </p>
        </div>

        <section
          className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4"
          aria-label="Customer KPIs"
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

        <CustomerOverview hideSummary />

        <div style={{ marginTop: 24 }}>
          <AnalyticsSectionHeader title="Customer Segmentation (RFM)" icon={UserCheck} />
          <div className="space-y-6">
            <RFMMatrix />
            <SegmentFunnel />
          </div>
        </div>
      </div>
    </DashboardShell>
  );
}
