"use client";

import { memo } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { useCustomerTypeBreakdown } from "@/hooks/use-customer-type-breakdown";
import { useFilters } from "@/contexts/filter-context";
import { LoadingCard } from "@/components/loading-card";
import { EmptyState } from "@/components/empty-state";
import { ErrorRetry } from "@/components/error-retry";
import { formatCompact, formatNumber } from "@/lib/formatters";
import { useChartTheme } from "@/hooks/use-chart-theme";

// Theme-aware: dark mode uses brighter variants for contrast
const TYPE_COLORS_LIGHT = ["#4F46E5", "#2196F3", "#9E9E9E"] as const;
const TYPE_COLORS_DARK = ["#6366F1", "#60A5FA", "#D1D5DB"] as const;

function CustomTooltip(props: Record<string, unknown>) {
  const { active, payload } = props;
  const items = payload as
    | Array<{ payload: { name: string; value: number; pct: number } }>
    | undefined;
  if (!active || !items?.length) return null;
  const d = items[0].payload;
  return (
    <div className="rounded-xl border border-border bg-card/95 px-4 py-3 shadow-xl backdrop-blur-sm">
      <p className="text-xs font-medium text-text-secondary">{d.name}</p>
      <p className="mt-1 text-lg font-bold text-accent">
        {formatNumber(d.value)}
      </p>
      <p className="text-xs text-text-secondary">{d.pct.toFixed(1)}% of total</p>
    </div>
  );
}

export const CustomerTypeChart = memo(function CustomerTypeChart() {
  const { filters } = useFilters();
  const { data, isLoading, error } = useCustomerTypeBreakdown(filters);
  const CHART_THEME = useChartTheme();

  // Select theme-aware colors (chartBlue is dark-theme blue if dark)
  const TYPE_COLORS = CHART_THEME.chartBlue === "#6366F1" ? TYPE_COLORS_DARK : TYPE_COLORS_LIGHT;

  if (isLoading) return <LoadingCard lines={6} className="h-80" />;
  if (error) return <ErrorRetry title="Failed to load customer type data" />;
  if (!data?.items?.length)
    return <EmptyState title="No customer type data" />;

  // Aggregate across all periods into totals
  const totals = data.items.reduce(
    (acc, item) => ({
      walkIn: acc.walkIn + item.walk_in_count,
      insurance: acc.insurance + item.insurance_count,
      other: acc.other + item.other_count,
    }),
    { walkIn: 0, insurance: 0, other: 0 },
  );

  const grand = totals.walkIn + totals.insurance + totals.other;

  const chartData = [
    { name: "Walk-in (Cash)", value: totals.walkIn, pct: grand ? (totals.walkIn / grand) * 100 : 0 },
    { name: "Insurance", value: totals.insurance, pct: grand ? (totals.insurance / grand) * 100 : 0 },
    { name: "Other", value: totals.other, pct: grand ? (totals.other / grand) * 100 : 0 },
  ]
    .filter((d) => d.value > 0)
    .sort((a, b) => b.value - a.value);

  return (
    <div className="rounded-xl border border-border bg-card p-5 transition-all duration-300 hover:border-accent/30 hover:shadow-lg hover:shadow-accent/5">
      <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-text-secondary">
        Customer Type Distribution
      </h3>
      <ResponsiveContainer width="100%" height={Math.max(chartData.length * 56, 120)}>
        <BarChart data={chartData} layout="vertical" margin={{ left: 10, right: 100 }}>
          <XAxis
            type="number"
            tick={{ fill: CHART_THEME.tickFill, fontSize: 11 }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v) => formatCompact(v)}
          />
          <YAxis
            type="category"
            dataKey="name"
            tick={{ fill: CHART_THEME.tickFill, fontSize: 12 }}
            tickLine={false}
            axisLine={false}
            width={110}
          />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: "rgba(255,255,255,0.04)" }} />
          <Bar dataKey="value" radius={[0, 6, 6, 0]} barSize={28}>
            {chartData.map((_, index) => (
              <Cell
                key={`cell-${index}`}
                fill={TYPE_COLORS[index % TYPE_COLORS.length]}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      {/* Inline labels */}
      <div className="mt-2 flex flex-wrap gap-4 text-xs text-text-secondary">
        {chartData.map((d, i) => (
          <span key={d.name} className="flex items-center gap-1.5">
            <span
              className="inline-block h-2.5 w-2.5 rounded-full"
              style={{ backgroundColor: TYPE_COLORS[i % TYPE_COLORS.length] }}
            />
            {d.name}: {formatNumber(d.value)} ({d.pct.toFixed(1)}%)
          </span>
        ))}
      </div>
    </div>
  );
});
