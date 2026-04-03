"use client";

import { KPICard } from "./kpi-card";
import { LoadingCard } from "@/components/loading-card";
import { useDashboardData } from "@/contexts/dashboard-data-context";
import { formatCurrency, formatNumber } from "@/lib/formatters";
import {
  DollarSign,
  CalendarDays,
  TrendingUp,
  Users,
  Target,
  Zap,
  ShoppingCart,
  RotateCcw,
} from "lucide-react";

const TOOLTIPS = {
  todayNet: "Net sales amount for the selected target date after discounts and returns",
  mtdNet: "Month-to-date cumulative net sales from the 1st of the current month",
  ytdNet: "Year-to-date cumulative net sales from January 1st",
  momGrowth: "Month-over-month growth comparing current MTD to same date last month",
  yoyGrowth: "Year-over-year growth comparing current YTD to same date last year",
  dailyTxn: "Number of individual line-item transactions on the target date",
  dailyCust: "Count of unique customers who made purchases on the target date",
  avgBasket: "Average transaction value per invoice on the target date",
  dailyReturns: "Number of return transactions recorded on the target date",
  mtdTxn: "Month-to-date cumulative transaction count",
  ytdTxn: "Year-to-date cumulative transaction count",
} as const;

export function KPIGrid() {
  const { data: dashboardData, isLoading } = useDashboardData();
  const data = dashboardData?.kpi;

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-4">
          {Array.from({ length: 7 }).map((_, i) => (
            <LoadingCard key={i} lines={2} className={`stagger-${i + 1}`} />
          ))}
        </div>
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <LoadingCard key={`sec-${i}`} lines={2} className={`stagger-${i + 8}`} />
          ))}
        </div>
      </div>
    );
  }

  if (!data) return null;

  const revenueCards = [
    {
      label: "Today Net Sales",
      value: formatCurrency(data.today_net),
      numericValue: data.today_net,
      isCurrency: true,
      icon: Zap,
      tooltip: TOOLTIPS.todayNet,
      sparkline: data.sparkline,
    },
    {
      label: "MTD Net Sales",
      value: formatCurrency(data.mtd_net),
      numericValue: data.mtd_net,
      isCurrency: true,
      icon: CalendarDays,
      tooltip: TOOLTIPS.mtdNet,
    },
    {
      label: "YTD Net Sales",
      value: formatCurrency(data.ytd_net),
      numericValue: data.ytd_net,
      isCurrency: true,
      icon: Target,
      tooltip: TOOLTIPS.ytdNet,
    },
    {
      label: "MoM Growth",
      value: data.mom_growth_pct !== null ? `${data.mom_growth_pct.toFixed(1)}%` : "N/A",
      numericValue: data.mom_growth_pct ?? undefined,
      isPercent: true,
      trend: data.mom_growth_pct,
      trendLabel: "vs last month",
      icon: TrendingUp,
      tooltip: TOOLTIPS.momGrowth,
    },
  ];

  const activityCards = [
    {
      label: "Daily Transactions",
      value: formatNumber(data.daily_transactions),
      numericValue: data.daily_transactions,
      icon: DollarSign,
      tooltip: TOOLTIPS.dailyTxn,
    },
    {
      label: "Daily Customers",
      value: formatNumber(data.daily_customers),
      numericValue: data.daily_customers,
      icon: Users,
      tooltip: TOOLTIPS.dailyCust,
    },
    {
      label: "Avg Basket Size",
      value: formatCurrency(data.avg_basket_size),
      numericValue: data.avg_basket_size,
      isCurrency: true,
      icon: ShoppingCart,
      tooltip: TOOLTIPS.avgBasket,
    },
    {
      label: "Daily Returns",
      value: formatNumber(data.daily_returns),
      numericValue: data.daily_returns,
      icon: RotateCcw,
      tooltip: TOOLTIPS.dailyReturns,
    },
  ];

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {revenueCards.map((card, i) => (
          <KPICard
            key={card.label}
            {...card}
            className={`stagger-${i + 1} animate-fade-in opacity-0`}
          />
        ))}
      </div>
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {activityCards.map((card, i) => (
          <KPICard
            key={card.label}
            {...card}
            className={`stagger-${i + 5} animate-fade-in opacity-0`}
          />
        ))}
      </div>
    </div>
  );
}
