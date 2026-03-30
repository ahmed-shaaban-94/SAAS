"use client";

import { KPICard } from "./kpi-card";
import { LoadingCard } from "@/components/loading-card";
import { useSummary } from "@/hooks/use-summary";
import { useFilters } from "@/contexts/filter-context";
import { formatCurrency, formatNumber } from "@/lib/formatters";
import {
  DollarSign,
  CalendarDays,
  TrendingUp,
  BarChart3,
  Users,
  Target,
  Zap,
} from "lucide-react";

export function KPIGrid() {
  const { filters } = useFilters();
  const { data, isLoading } = useSummary(filters);

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4 lg:grid-cols-4 xl:grid-cols-7">
        {Array.from({ length: 7 }).map((_, i) => (
          <LoadingCard key={i} lines={2} className={`stagger-${i + 1}`} />
        ))}
      </div>
    );
  }

  if (!data) return null;

  const cards = [
    {
      label: "Today Net Sales",
      value: formatCurrency(data.today_net),
      numericValue: data.today_net,
      isCurrency: true,
      icon: Zap,
    },
    {
      label: "MTD Net Sales",
      value: formatCurrency(data.mtd_net),
      numericValue: data.mtd_net,
      isCurrency: true,
      icon: CalendarDays,
    },
    {
      label: "YTD Net Sales",
      value: formatCurrency(data.ytd_net),
      numericValue: data.ytd_net,
      isCurrency: true,
      icon: Target,
    },
    {
      label: "MoM Growth",
      value: data.mom_growth_pct !== null ? `${data.mom_growth_pct.toFixed(1)}%` : "N/A",
      numericValue: data.mom_growth_pct ?? undefined,
      isPercent: true,
      trend: data.mom_growth_pct,
      trendLabel: "vs last month",
      icon: TrendingUp,
    },
    {
      label: "YoY Growth",
      value: data.yoy_growth_pct !== null ? `${data.yoy_growth_pct.toFixed(1)}%` : "N/A",
      numericValue: data.yoy_growth_pct ?? undefined,
      isPercent: true,
      trend: data.yoy_growth_pct,
      trendLabel: "vs last year",
      icon: BarChart3,
    },
    {
      label: "Daily Transactions",
      value: formatNumber(data.daily_transactions),
      numericValue: data.daily_transactions,
      icon: DollarSign,
    },
    {
      label: "Daily Customers",
      value: formatNumber(data.daily_customers),
      numericValue: data.daily_customers,
      icon: Users,
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-4 md:grid-cols-4 lg:grid-cols-4 xl:grid-cols-7">
      {cards.map((card, i) => (
        <KPICard
          key={card.label}
          {...card}
          className={`stagger-${i + 1} animate-fade-in opacity-0`}
        />
      ))}
    </div>
  );
}
