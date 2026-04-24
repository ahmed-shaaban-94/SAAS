"use client";

import { memo, useMemo } from "react";
import { KPICard } from "./kpi-card";
import { LoadingCard } from "@/components/loading-card";
import { useDashboardData } from "@/contexts/dashboard-data-context";
import { useFilters } from "@/contexts/filter-context";
import { formatCurrency, formatNumber, formatPercent } from "@/lib/formatters";
import {
  buildMtdRevenueWhy,
  buildAvgBasketWhy,
} from "@/components/why-changed/why-changed-data";
import { format, parseISO } from "date-fns";
import {
  CalendarDays,
  TrendingUp,
  Zap,
  ShoppingCart,
  Receipt,
} from "lucide-react";

const TOOLTIPS = {
  periodRevenue: "Total gross sales for the selected date range (before discounts and tax)",
  mtdRevenue: "Month-to-date cumulative gross sales from the 1st of the current month",
  ytdRevenue: "Year-to-date cumulative gross sales from January 1st",
  revenueVsTarget: "Revenue achievement compared to the monthly budget target",
  momGrowth: "Growth compared to the equivalent previous period",
  completedTxn: "Completed transactions: total invoices minus returns for the selected period",
  avgOrderValue: "Average order value per customer for the selected period",
  totalUnits: "Sum of all units sold/returned for the selected period (returns are negative)",
  unitsPerTxn: "Average number of units per transaction for the selected period",
} as const;

function formatPeriodLabel(startDate?: string, endDate?: string): string | null {
  if (!startDate || !endDate) return null;
  try {
    const s = format(parseISO(startDate), "MMM d, yyyy");
    const e = format(parseISO(endDate), "MMM d, yyyy");
    return s === e ? s : `${s} - ${e}`;
  } catch {
    return null;
  }
}


function getGrowthStatus(growthPct: number | null): string | undefined {
  if (growthPct === null || growthPct === undefined) return undefined;
  if (growthPct < -5) return "Needs attention";
  if (growthPct <= 2) return "Recovery in progress";
  return "Healthy momentum";
}

export const KPIGrid = memo(function KPIGrid() {
  const { data: dashboardData, isLoading } = useDashboardData();
  const { filters } = useFilters();
  const data = dashboardData?.kpi;
  const periodLabel = formatPeriodLabel(filters?.start_date, filters?.end_date);

  const cards = useMemo(() => {
    if (!data) return [];
    return [
      {
        label: "Period Revenue",
        value: formatCurrency(data.period_gross),
        numericValue: data.period_gross,
        isCurrency: true,
        icon: Zap,
        tooltip: TOOLTIPS.periodRevenue,
        sparkline: data.sparkline,
        hero: true,
        comparisonLine: data.mom_growth_pct != null
          ? `${formatPercent(data.mom_growth_pct)} vs previous period`
          : undefined,
        whyChanged: buildMtdRevenueWhy(data.period_gross, data.mom_growth_pct),
      },
      {
        label: "Growth",
        value: data.mom_growth_pct != null ? `${data.mom_growth_pct.toFixed(1)}%` : "N/A",
        numericValue: data.mom_growth_pct ?? undefined,
        isPercent: true,
        trend: data.mom_growth_pct,
        trendLabel: "vs previous period",
        icon: TrendingUp,
        tooltip: TOOLTIPS.momGrowth,
        comparisonLine: getGrowthStatus(data.mom_growth_pct ?? null),
      },
      {
        label: "Transactions",
        value: formatNumber(data.period_transactions),
        numericValue: data.period_transactions,
        subtitle: data.daily_returns > 0
          ? `${formatNumber(data.period_transactions + data.daily_returns)} sales - ${formatNumber(data.daily_returns)} returns`
          : undefined,
        icon: Receipt,
        tooltip: TOOLTIPS.completedTxn,
      },
      {
        label: "Avg Order Value",
        value: formatCurrency(data.avg_basket_size),
        numericValue: data.avg_basket_size,
        isCurrency: true,
        icon: ShoppingCart,
        tooltip: TOOLTIPS.avgOrderValue,
        whyChanged: buildAvgBasketWhy(data.avg_basket_size),
      },
    ];
  }, [data]);

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <LoadingCard key={i} lines={3} className={`stagger-${i + 1}`} />
        ))}
      </div>
    );
  }

  if (!data) {
    return (
      <div className="rounded-xl border border-border bg-card p-6 text-center">
        <p className="text-sm text-text-secondary">
          KPI data unavailable. Check your API connection.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {periodLabel && (
        <p className="text-xs font-medium text-text-secondary">
          <CalendarDays className="mr-1 inline-block h-3.5 w-3.5 align-text-bottom" />
          Showing: {periodLabel}
        </p>
      )}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {cards.map((card, i) => (
          <KPICard
            key={card.label}
            {...card}
            aria-label={`${card.label}: ${card.value}`}
            className={`stagger-${i + 1} animate-fade-in opacity-0`}
          />
        ))}
      </div>
    </div>
  );
});
