"use client";

import { memo, useMemo } from "react";
import { useDashboardData } from "@/contexts/dashboard-data-context";
import { KPICard } from "./kpi-card";
import { LoadingCard } from "@/components/loading-card";
import { formatCurrency } from "@/lib/formatters";
import {
  TrendingUp,
  TrendingDown,
  BarChart3,
  Calendar,
  ArrowUpRight,
  ArrowDownRight,
} from "lucide-react";

/**
 * 6 KPI summary cards for the Trends section, derived from daily + monthly trend data.
 * Shows: Daily Total, Monthly Total, Daily Growth, Monthly Growth, Daily Peak, Daily Low.
 */
export const TrendKPICards = memo(function TrendKPICards() {
  const { data: dashboardData, isLoading } = useDashboardData();

  const daily = dashboardData?.daily_trend;
  const monthly = dashboardData?.monthly_trend;

  const cards = useMemo(
    () => [
      {
        label: "Daily Total",
        value: daily ? formatCurrency(daily.total) : "N/A",
        icon: BarChart3,
        tooltip: "Sum of daily net sales for the selected period",
      },
      {
        label: "Monthly Total",
        value: monthly ? formatCurrency(monthly.total) : "N/A",
        icon: Calendar,
        tooltip: "Sum of monthly net sales for the selected period",
      },
      {
        label: "Daily Growth",
        value: daily?.growth_pct != null ? `${daily.growth_pct > 0 ? "+" : ""}${daily.growth_pct.toFixed(1)}%` : "N/A",
        trend: daily?.growth_pct ?? null,
        icon: daily?.growth_pct != null && daily.growth_pct >= 0 ? TrendingUp : TrendingDown,
        tooltip: "Selected period total vs equivalent previous period",
      },
      {
        label: "Monthly Growth",
        value: monthly?.growth_pct != null ? `${monthly.growth_pct > 0 ? "+" : ""}${monthly.growth_pct.toFixed(1)}%` : "N/A",
        trend: monthly?.growth_pct ?? null,
        icon: monthly?.growth_pct != null && monthly.growth_pct >= 0 ? TrendingUp : TrendingDown,
        tooltip: "Selected period total vs equivalent previous period",
      },
      {
        label: "Peak Day",
        value: daily ? formatCurrency(daily.maximum) : "N/A",
        icon: ArrowUpRight,
        tooltip: "Highest single-day net sales in the selected period",
      },
      {
        label: "Lowest Day",
        value: daily ? formatCurrency(daily.minimum) : "N/A",
        icon: ArrowDownRight,
        tooltip: "Lowest single-day net sales in the selected period",
      },
    ],
    [daily, monthly],
  );

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
        {Array.from({ length: 6 }).map((_, i) => (
          <LoadingCard key={i} lines={2} />
        ))}
      </div>
    );
  }

  if (!daily && !monthly) return null;

  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
      {cards.map((card, i) => (
        <KPICard
          key={card.label}
          label={card.label}
          value={card.value}
          icon={card.icon}
          tooltip={card.tooltip}
          trend={card.trend}
          className={`stagger-${i + 1} animate-fade-in opacity-0`}
        />
      ))}
    </div>
  );
});
