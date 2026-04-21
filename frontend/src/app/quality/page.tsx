"use client";

/**
 * /quality — Pipeline Health on the v2 shell.
 *
 * Ops Surfaces batch (Apr 2026): migrated from `(app)/quality/page.tsx`,
 * added a 4-tile KpiCard row (pass rate, run count, failed, warned).
 * `DataOpsCommandBar` and `QualityOverview` keep their existing layout
 * below.
 */

import { useMemo } from "react";
import { ShieldCheck, Activity, ShieldX, AlertTriangle } from "lucide-react";

import { DashboardShell } from "@/components/dashboard-v2/shell";
import { KpiCard, type KpiColor, type KpiDir } from "@/components/dashboard/new";
import { DataOpsCommandBar } from "@/components/data-ops/command-bar";
import { QualityOverview } from "@/components/quality/quality-overview";
import { LoadingCard } from "@/components/loading-card";
import { useQualityScorecard } from "@/hooks/use-quality-scorecard";
import { formatNumber } from "@/lib/formatters";

export default function QualityPage() {
  const { data, isLoading } = useQualityScorecard();

  const kpis = useMemo(() => {
    const passRate = data.overall_pass_rate ?? 0;
    const totalRuns = data.total_runs ?? 0;
    const totalFailed = data.runs.reduce((s, r) => s + r.failed, 0);
    const totalWarned = data.runs.reduce((s, r) => s + r.warned, 0);

    return [
      {
        id: "pass-rate",
        label: "Overall Pass Rate",
        value: `${passRate.toFixed(0)}%`,
        delta: {
          dir: (passRate >= 90 ? "up" : "down") as KpiDir,
          text: passRate >= 90 ? "healthy" : passRate >= 70 ? "watch" : "critical",
        },
        sub: "across all quality checks",
        color: "accent" as KpiColor,
        sparkline: [] as number[],
        icon: ShieldCheck,
      },
      {
        id: "total-runs",
        label: "Pipeline Runs",
        value: formatNumber(totalRuns),
        delta: { dir: "up" as KpiDir, text: "recent history" },
        sub: "in the scorecard window",
        color: "purple" as KpiColor,
        sparkline: [] as number[],
        icon: Activity,
      },
      {
        id: "failed",
        label: "Failed Checks",
        value: formatNumber(totalFailed),
        delta: {
          dir: (totalFailed === 0 ? "up" : "down") as KpiDir,
          text: totalFailed === 0 ? "all clean" : "needs attention",
        },
        sub: "quality gate failures",
        color: "red" as KpiColor,
        sparkline: [] as number[],
        icon: ShieldX,
      },
      {
        id: "warned",
        label: "Warnings",
        value: formatNumber(totalWarned),
        delta: {
          dir: (totalWarned === 0 ? "up" : "down") as KpiDir,
          text: totalWarned === 0 ? "none" : "soft issues",
        },
        sub: "advisory checks over threshold",
        color: "amber" as KpiColor,
        sparkline: [] as number[],
        icon: AlertTriangle,
      },
    ];
  }, [data]);

  return (
    <DashboardShell
      activeHref="/quality"
      breadcrumbs={[
        { label: "DataPulse", href: "/dashboard" },
        { label: "Data Ops" },
        { label: "Pipeline Health" },
      ]}
    >
      <div className="page">
        <div>
          <h1 className="page-title">Pipeline health.</h1>
          <p className="page-sub">
            Freshness, completeness, and quality checks across every pipeline run.
          </p>
        </div>

        <section
          className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4"
          aria-label="Pipeline quality KPIs"
        >
          {isLoading
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

        <DataOpsCommandBar />

        <QualityOverview />
      </div>
    </DashboardShell>
  );
}
