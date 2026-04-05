"use client";

import { memo } from "react";
import {
  PieChart,
  Pie,
  Cell,
  Legend,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { useBillingBreakdown } from "@/hooks/use-billing-breakdown";
import { useFilters } from "@/contexts/filter-context";
import { LoadingCard } from "@/components/loading-card";
import { EmptyState } from "@/components/empty-state";
import { formatCurrency, formatNumber } from "@/lib/formatters";
import { CHART_COLORS } from "@/lib/constants";
import { useChartTheme } from "@/hooks/use-chart-theme";

function CustomTooltip(props: Record<string, unknown>) {
  const { active, payload } = props;
  const items = payload as Array<{ name: string; value: number; payload: { pct: number; count: number } }> | undefined;
  if (!active || !items?.length) return null;
  const item = items[0];
  return (
    <div className="rounded-xl border border-border bg-card/95 px-4 py-3 shadow-xl backdrop-blur-sm">
      <p className="text-xs font-medium text-text-secondary">{item.name}</p>
      <p className="mt-1 text-lg font-bold text-accent">
        {formatCurrency(item.value)}
      </p>
      <p className="text-xs text-text-secondary">
        {formatNumber(item.payload.count)} transactions ({item.payload.pct.toFixed(1)}%)
      </p>
    </div>
  );
}

export const BillingBreakdownChart = memo(function BillingBreakdownChart() {
  const { filters } = useFilters();
  const { data, isLoading } = useBillingBreakdown(filters);
  const CHART_THEME = useChartTheme();

  if (isLoading) return <LoadingCard lines={6} className="h-80" />;
  if (!data?.items?.length)
    return <EmptyState title="No billing data" />;

  const chartData = data.items.map((item) => ({
    name: item.billing_group,
    value: item.total_net_amount,
    pct: item.pct_of_total,
    count: item.transaction_count,
  }));

  return (
    <div className="rounded-xl border border-border bg-card p-5">
      <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-text-secondary">
        Billing Method Distribution
      </h3>
      <ResponsiveContainer width="100%" height={280}>
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            innerRadius={60}
            outerRadius={100}
            dataKey="value"
            nameKey="name"
            paddingAngle={2}
            animationDuration={800}
          >
            {chartData.map((_, index) => (
              <Cell
                key={`cell-${index}`}
                fill={CHART_COLORS[index % CHART_COLORS.length]}
                stroke="transparent"
              />
            ))}
          </Pie>
          <Tooltip content={<CustomTooltip />} />
          <Legend
            verticalAlign="bottom"
            iconType="circle"
            iconSize={8}
            formatter={(value: string) => (
              <span style={{ color: CHART_THEME.tickFill, fontSize: 12 }}>
                {value}
              </span>
            )}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
});
