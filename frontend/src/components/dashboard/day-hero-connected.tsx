"use client";

import { DayHero } from "./day-hero";
import { useDashboardData } from "@/contexts/dashboard-data-context";

/**
 * Connects DayHero to the dashboard data context.
 * Must be rendered inside <DashboardDataProvider>.
 */
export function DayHeroConnected() {
  const { data, isLoading } = useDashboardData();

  if (isLoading || !data) return null;

  return (
    <DayHero
      revenue={data.kpi.today_gross}
      transactions={data.kpi.daily_transactions}
      momGrowth={data.kpi.mom_growth_pct}
    />
  );
}
