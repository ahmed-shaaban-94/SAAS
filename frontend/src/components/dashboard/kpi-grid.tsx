"use client";

import { useMemo } from "react";
import { KPICard } from "./kpi-card";
import { LoadingCard } from "@/components/loading-card";
import { useDashboardData } from "@/contexts/dashboard-data-context";
import { useFilters } from "@/contexts/filter-context";
import { useTargetSummary } from "@/hooks/use-targets";
import { formatCurrency, formatNumber, formatPercent } from "@/lib/formatters";
import { format, parseISO, startOfMonth, endOfMonth, isSameDay } from "date-fns";
import {
  CalendarDays,
  TrendingUp,
  Target,
  Zap,
  ShoppingCart,
  Receipt,
  Package,
  Divide,
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

/** Check if the selected filter range matches the current month exactly */
function isCurrentMonthSelected(startDate?: string, endDate?: string): boolean {
  if (!startDate || !endDate) return false;
  try {
    const start = parseISO(startDate);
    const end = parseISO(endDate);
    const now = new Date();
    const monthStart = startOfMonth(now);
    const monthEnd = endOfMonth(now);
    return isSameDay(start, monthStart) && (isSameDay(end, monthEnd) || isSameDay(end, now));
  } catch {
    return false;
  }
}

function getGrowthStatus(growthPct: number | null): string | undefined {
  if (growthPct === null || growthPct === undefined) return undefined;
  if (growthPct < -5) return "Needs attention";
  if (growthPct <= 2) return "Recovery in progress";
  return "Healthy momentum";
}

export function KPIGrid() {
  const { data: dashboardData, isLoading } = useDashboardData();
  const { filters } = useFilters();
  const { data: targetData } = useTargetSummary();
  const data = dashboardData?.kpi;
  const periodLabel = formatPeriodLabel(filters?.start_date, filters?.end_date);
  const currentMonthSelected = isCurrentMonthSelected(filters?.start_date, filters?.end_date);

  // Find current month target achievement
  const currentMonthTarget = useMemo(() => {
    if (!targetData?.monthly_targets?.length) return null;
    const now = new Date();
    const monthStr = format(now, "yyyy-MM");
    return targetData.monthly_targets.find((t) => t.period?.startsWith(monthStr)) ?? null;
  }, [targetData]);

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 gap-4 md:grid-cols-3">
        {Array.from({ length: 6 }).map((_, i) => (
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

  // Units metrics — daily_quantity is already net (returns are negative in DB)
  // daily_transactions is already net (total_transactions - total_returns) from backend
  const totalUnits = data.daily_quantity ?? 0;
  const unitsPerTxn = data.daily_transactions > 0 ? totalUnits / data.daily_transactions : 0;

  const cards: Array<{
    label: string;
    value: string;
    numericValue?: number;
    isCurrency?: boolean;
    isPercent?: boolean;
    isDecimal?: boolean;
    trend?: number | null;
    trendLabel?: string;
    icon: React.ComponentType<{ className?: string }>;
    tooltip: string;
    sparkline?: { period: string; value: number }[];
    subtitle?: string;
    comparisonLine?: string;
    hero?: boolean;
    className?: string;
  }> = [
    {
      label: "Selected Period Revenue",
      value: formatCurrency(data.today_gross),
      numericValue: data.today_gross,
      isCurrency: true,
      icon: Zap,
      tooltip: TOOLTIPS.periodRevenue,
      sparkline: data.sparkline,
      comparisonLine: data.mom_growth_pct !== null
        ? `${formatPercent(data.mom_growth_pct)} vs previous period`
        : undefined,
    },
    {
      label: "Total Units",
      value: formatNumber(Math.round(totalUnits)),
      numericValue: totalUnits,
      icon: Package,
      tooltip: TOOLTIPS.totalUnits,
    },
    {
      label: "Units per Transaction",
      value: unitsPerTxn.toFixed(2),
      numericValue: unitsPerTxn,
      isDecimal: true,
      icon: Divide,
      tooltip: TOOLTIPS.unitsPerTxn,
    },
    {
      label: "Growth",
      value: data.mom_growth_pct !== null ? `${data.mom_growth_pct.toFixed(1)}%` : "N/A",
      numericValue: data.mom_growth_pct ?? undefined,
      isPercent: true,
      trend: data.mom_growth_pct,
      trendLabel: "vs previous period",
      icon: TrendingUp,
      tooltip: TOOLTIPS.momGrowth,
      hero: true,
      comparisonLine: getGrowthStatus(data.mom_growth_pct),
      className: "col-span-2 md:col-span-1 order-first md:order-none",
    },
    {
      label: "Completed Transactions",
      value: formatNumber(data.daily_transactions),
      numericValue: data.daily_transactions,
      subtitle: data.daily_returns > 0
        ? `${formatNumber(data.daily_transactions + data.daily_returns)} sales - ${formatNumber(data.daily_returns)} returns`
        : undefined,
      icon: Receipt,
      tooltip: TOOLTIPS.completedTxn,
    },
    {
      label: "Average Order Value",
      value: formatCurrency(data.avg_basket_size),
      numericValue: data.avg_basket_size,
      isCurrency: true,
      icon: ShoppingCart,
      tooltip: TOOLTIPS.avgOrderValue,
    },
  ];

  return (
    <div className="space-y-3">
      {periodLabel && (
        <p className="text-xs font-medium text-text-secondary">
          <CalendarDays className="mr-1 inline-block h-3.5 w-3.5 align-text-bottom" />
          Showing: {periodLabel}
        </p>
      )}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-3">
        {cards.map((card, i) => (
          <KPICard
            key={card.label}
            {...card}
            className={`${card.className ?? ""} stagger-${i + 1} animate-fade-in opacity-0`.trim()}
          />
        ))}
      </div>
    </div>
  );
}
