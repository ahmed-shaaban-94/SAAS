"use client";

/**
 * /goals — Goals & Targets on the v2 shell.
 *
 * Ops Surfaces batch (Apr 2026): migrated from `(app)/goals/page.tsx`,
 * added a 4-tile KpiCard row (YTD Target, YTD Actual, Achievement %,
 * Budget Variance). `GoalsOverview` keeps its ProgressRing/BudgetSection
 * detail views below.
 */

import { useMemo } from "react";
import { Target, TrendingUp, CheckCircle2, Wallet } from "lucide-react";

import { DashboardShell } from "@/components/dashboard-v2/shell";
import { KpiCard, type KpiColor, type KpiDir } from "@/components/dashboard/new";
import { GoalsOverview } from "@/components/goals/goals-overview";
import { LoadingCard } from "@/components/loading-card";
import { useTargetSummary } from "@/hooks/use-targets";
import { useBudgetSummary } from "@/hooks/use-budget";
import { formatCurrency } from "@/lib/formatters";

export default function GoalsPage() {
  const year = new Date().getFullYear();
  const { data: target, isLoading: targetLoading } = useTargetSummary(year);
  const { data: budget, isLoading: budgetLoading } = useBudgetSummary(year);

  const kpiLoading = targetLoading || budgetLoading;

  const kpis = useMemo(() => {
    const ytdTarget = target?.ytd_target ?? 0;
    const ytdActual = target?.ytd_actual ?? 0;
    const achievementPct = target?.ytd_achievement_pct ?? 0;
    const budgetVariance = (budget?.ytd_actual ?? 0) - (budget?.ytd_budget ?? 0);
    const budgetAchievement = budget?.ytd_achievement_pct ?? 0;

    return [
      {
        id: "ytd-target",
        label: "YTD Target",
        value: formatCurrency(ytdTarget),
        delta: { dir: "up" as KpiDir, text: `${year}` },
        sub: "annual goal to-date",
        color: "accent" as KpiColor,
        sparkline: [] as number[],
        icon: Target,
      },
      {
        id: "ytd-actual",
        label: "YTD Actual",
        value: formatCurrency(ytdActual),
        delta: {
          dir: (ytdActual >= ytdTarget ? "up" : "down") as KpiDir,
          text: formatCurrency(ytdActual - ytdTarget),
        },
        sub: "vs target, positive = ahead",
        color: "purple" as KpiColor,
        sparkline: [] as number[],
        icon: TrendingUp,
      },
      {
        id: "achievement",
        label: "Target Achievement",
        value: `${achievementPct.toFixed(0)}%`,
        delta: {
          dir: (achievementPct >= 100 ? "up" : "down") as KpiDir,
          text: achievementPct >= 100 ? "on/above plan" : "behind plan",
        },
        sub: "revenue target YTD",
        color: "amber" as KpiColor,
        sparkline: [] as number[],
        icon: CheckCircle2,
      },
      {
        id: "budget-variance",
        label: "Budget Variance",
        value: formatCurrency(budgetVariance),
        delta: {
          dir: (budgetVariance >= 0 ? "up" : "down") as KpiDir,
          text: `${budgetAchievement.toFixed(0)}% of budget`,
        },
        sub: "actual minus budget, YTD",
        color: "red" as KpiColor,
        sparkline: [] as number[],
        icon: Wallet,
      },
    ];
  }, [target, budget, year]);

  return (
    <DashboardShell
      activeHref="/goals"
      breadcrumbs={[
        { label: "DataPulse", href: "/dashboard" },
        { label: "Planning" },
        { label: "Goals" },
      ]}
    >
      <div className="page">
        <div>
          <h1 className="page-title">Goals & targets.</h1>
          <p className="page-sub">
            Set and track sales targets and budget across the organization.
          </p>
        </div>

        <section
          className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4"
          aria-label="Goals KPIs"
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

        <GoalsOverview />
      </div>
    </DashboardShell>
  );
}
