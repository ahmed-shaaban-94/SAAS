"use client";

/**
 * /staff — Staff Performance on the v2 shell.
 *
 * Migrated from `(app)/staff/page.tsx`. KPIs: team revenue, active head
 * count, top performer share, average quota attainment.
 */

import { useMemo } from "react";
import { Users, UserCheck, Crown, Target, Trophy } from "lucide-react";

import { DashboardShell } from "@/components/dashboard-v2/shell";
import { FilterBar } from "@/components/filters/filter-bar";
import { KpiCard, type KpiColor, type KpiDir } from "@/components/dashboard/new";
import { StaffOverview } from "@/components/staff/staff-overview";
import { GamifiedLeaderboard } from "@/components/staff/gamified-leaderboard";
import { StaffQuotaSection } from "@/components/staff/staff-quota-section";
import { AnalyticsSectionHeader } from "@/components/layout/analytics-section-header";
import { LoadingCard } from "@/components/loading-card";
import { useFilters } from "@/contexts/filter-context";
import { useTopStaff } from "@/hooks/use-top-staff";
import { useDailyTrend } from "@/hooks/use-daily-trend";
import { useStaffQuota } from "@/hooks/use-staff-quota";
import { formatCurrency, formatNumber } from "@/lib/formatters";
import type { TimeSeriesPoint } from "@/types/api";

function toSparkline(points: TimeSeriesPoint[] | undefined): number[] {
  if (!points?.length) return [];
  const values = points.map((p) => Number(p.value) || 0);
  const max = Math.max(...values, 1);
  return values.map((v) => 32 - (v / max) * 28);
}

export default function StaffPage() {
  const { filters } = useFilters();
  const { data: topStaff, isLoading: topLoading } = useTopStaff(filters);
  const { data: dailyTrend, isLoading: trendLoading } = useDailyTrend(filters);
  const { data: quota, isLoading: quotaLoading } = useStaffQuota();

  const kpiLoading = topLoading || trendLoading || quotaLoading;

  const kpis = useMemo(() => {
    if (!topStaff) return null;
    const top = topStaff.items[0];
    const growthPct = dailyTrend?.growth_pct;
    const growthDir: KpiDir = (growthPct ?? 0) >= 0 ? "up" : "down";

    // Average revenue-achievement across the team; null rows skipped.
    const attainmentValues = quota
      .map((q) => q.revenue_achievement_pct)
      .filter((v): v is number => v != null);
    const avgAttainment =
      attainmentValues.length > 0
        ? attainmentValues.reduce((a, b) => a + b, 0) / attainmentValues.length
        : null;

    return [
      {
        id: "revenue",
        label: "Team Revenue",
        value: formatCurrency(topStaff.total),
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
        label: "Active Staff",
        value: formatNumber(topStaff.active_count ?? topStaff.items.length),
        delta: { dir: "up" as KpiDir, text: `of ${topStaff.items.length} total` },
        sub: "with sales in period",
        color: "purple" as KpiColor,
        sparkline: [] as number[],
        icon: UserCheck,
      },
      {
        id: "top-performer",
        label: "Top Performer Share",
        value: top ? `${top.pct_of_total.toFixed(1)}%` : "—",
        delta: top
          ? { dir: "up" as KpiDir, text: formatCurrency(top.value) }
          : { dir: "up" as KpiDir, text: "—" },
        sub: top ? top.name : "no staff data",
        color: "amber" as KpiColor,
        sparkline: [] as number[],
        icon: Crown,
      },
      {
        id: "quota",
        label: "Avg Quota Attainment",
        value:
          avgAttainment != null ? `${avgAttainment.toFixed(0)}%` : "—",
        delta: {
          dir: ((avgAttainment ?? 0) >= 100 ? "up" : "down") as KpiDir,
          text:
            avgAttainment != null
              ? `${attainmentValues.length} tracked`
              : "no targets set",
        },
        sub: "this month's revenue targets",
        color: "red" as KpiColor,
        sparkline: [] as number[],
        icon: Target,
      },
    ];
  }, [topStaff, dailyTrend, quota]);

  return (
    <DashboardShell
      activeHref="/staff"
      breadcrumbs={[
        { label: "DataPulse", href: "/dashboard" },
        { label: "Operations" },
        { label: "Staff" },
      ]}
    >
      <div className="page">
        <div>
          <h1 className="page-title">Staff.</h1>
          <p className="page-sub">
            Individual and team performance, quota attainment, and leaderboards.
          </p>
        </div>

        <section
          className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4"
          aria-label="Staff KPIs"
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

        <StaffOverview hideSummary />

        <div style={{ marginTop: 24 }}>
          <AnalyticsSectionHeader title="Quota Attainment" icon={Target} />
          <StaffQuotaSection />
        </div>

        <div style={{ marginTop: 24 }}>
          <AnalyticsSectionHeader
            title="Leaderboard"
            icon={Trophy}
            accentClassName="text-chart-amber"
          />
          <GamifiedLeaderboard />
        </div>
      </div>
    </DashboardShell>
  );
}
