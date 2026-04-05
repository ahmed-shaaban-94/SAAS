"use client";

import { KPICard } from "./kpi-card";
import { LoadingCard } from "@/components/loading-card";
import { useDashboardData } from "@/contexts/dashboard-data-context";
import { useFilters } from "@/contexts/filter-context";
import { formatCurrency, formatNumber } from "@/lib/formatters";
import { format, parseISO } from "date-fns";
import {
  CalendarDays,
  TrendingUp,
  Target,
  Zap,
  ShoppingCart,
  Receipt,
} from "lucide-react";

const TOOLTIPS = {
  periodGross: "Total gross sales for the selected date range (before discounts and tax)",
  mtdGross: "Month-to-date cumulative gross sales from the 1st of the current month",
  ytdGross: "Year-to-date cumulative gross sales from January 1st",
  momGrowth: "Growth compared to the equivalent previous period",
  netTxn: "Net transactions: total invoices minus returns for the selected period",
  avgBasket: "Average basket size per customer for the selected period",
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

export function KPIGrid() {
  const { data: dashboardData, isLoading } = useDashboardData();
  const { filters } = useFilters();
  const data = dashboardData?.kpi;
  const periodLabel = formatPeriodLabel(filters?.start_date, filters?.end_date);

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 gap-4 md:grid-cols-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <LoadingCard key={i} lines={2} className={`stagger-${i + 1}`} />
        ))}
      </div>
    );
  }

  if (!data) return null;

  const cards = [
    {
      label: "Period Gross Sales",
      value: formatCurrency(data.today_gross),
      numericValue: data.today_gross,
      isCurrency: true,
      icon: Zap,
      tooltip: TOOLTIPS.periodGross,
      sparkline: data.sparkline,
    },
    {
      label: "MTD Gross Sales",
      value: formatCurrency(data.mtd_gross),
      numericValue: data.mtd_gross,
      isCurrency: true,
      icon: CalendarDays,
      tooltip: TOOLTIPS.mtdGross,
    },
    {
      label: "YTD Gross Sales",
      value: formatCurrency(data.ytd_gross),
      numericValue: data.ytd_gross,
      isCurrency: true,
      icon: Target,
      tooltip: TOOLTIPS.ytdGross,
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
    },
    {
      label: "Net Transactions",
      value: formatNumber(data.daily_transactions),
      numericValue: data.daily_transactions,
      subtitle: data.daily_returns > 0
        ? `${formatNumber(data.daily_transactions + data.daily_returns)} sales - ${formatNumber(data.daily_returns)} returns`
        : undefined,
      icon: Receipt,
      tooltip: TOOLTIPS.netTxn,
    },
    {
      label: "Avg Basket Size",
      value: formatCurrency(data.avg_basket_size),
      numericValue: data.avg_basket_size,
      isCurrency: true,
      icon: ShoppingCart,
      tooltip: TOOLTIPS.avgBasket,
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
            className={`stagger-${i + 1} animate-fade-in opacity-0`}
          />
        ))}
      </div>
    </div>
  );
}
