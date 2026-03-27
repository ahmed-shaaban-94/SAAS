"use client";

import { KPICard } from "./kpi-card";
import { LoadingCard } from "@/components/loading-card";
import { useSummary } from "@/hooks/use-summary";
import { formatCurrency, formatNumber } from "@/lib/formatters";

export function KPIGrid() {
  const { data, isLoading } = useSummary();

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4 lg:grid-cols-7">
        {Array.from({ length: 7 }).map((_, i) => (
          <LoadingCard key={i} lines={2} />
        ))}
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="grid grid-cols-2 gap-4 md:grid-cols-4 lg:grid-cols-7">
      <KPICard
        label="Today Net Sales"
        value={formatCurrency(data.today_net)}
      />
      <KPICard
        label="MTD Net Sales"
        value={formatCurrency(data.mtd_net)}
      />
      <KPICard
        label="YTD Net Sales"
        value={formatCurrency(data.ytd_net)}
      />
      <KPICard
        label="MoM Growth"
        value={data.mom_growth_pct !== null ? `${data.mom_growth_pct.toFixed(1)}%` : "N/A"}
        trend={data.mom_growth_pct}
        trendLabel="vs last month"
      />
      <KPICard
        label="YoY Growth"
        value={data.yoy_growth_pct !== null ? `${data.yoy_growth_pct.toFixed(1)}%` : "N/A"}
        trend={data.yoy_growth_pct}
        trendLabel="vs last year"
      />
      <KPICard
        label="Daily Transactions"
        value={formatNumber(data.daily_transactions)}
      />
      <KPICard
        label="Daily Customers"
        value={formatNumber(data.daily_customers)}
      />
    </div>
  );
}
