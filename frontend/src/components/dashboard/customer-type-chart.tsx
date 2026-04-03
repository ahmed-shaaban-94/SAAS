"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { useCustomerTypeBreakdown } from "@/hooks/use-customer-type-breakdown";
import { useFilters } from "@/contexts/filter-context";
import { LoadingCard } from "@/components/loading-card";
import { EmptyState } from "@/components/empty-state";
import { formatCompact } from "@/lib/formatters";
import { useChartTheme } from "@/hooks/use-chart-theme";

const STACK_COLORS = {
  walkIn: "#4F46E5",
  insurance: "#2196F3",
  other: "#9E9E9E",
} as const;

function CustomTooltip(props: Record<string, unknown>) {
  const { active, payload, label } = props;
  const items = payload as Array<{ name: string; value: number; color: string }> | undefined;
  if (!active || !items?.length) return null;
  return (
    <div className="rounded-xl border border-border bg-card/95 px-4 py-3 shadow-xl backdrop-blur-sm">
      <p className="text-xs font-medium text-text-secondary">{String(label)}</p>
      {items.map((item) => (
        <div key={item.name} className="mt-1 flex items-center gap-2">
          <span
            className="inline-block h-2.5 w-2.5 rounded-full"
            style={{ backgroundColor: item.color }}
          />
          <span className="text-sm text-text-primary">
            {item.name}: {item.value.toLocaleString()}
          </span>
        </div>
      ))}
    </div>
  );
}

export function CustomerTypeChart() {
  const { filters } = useFilters();
  const { data, isLoading } = useCustomerTypeBreakdown(filters);
  const CHART_THEME = useChartTheme();

  if (isLoading) return <LoadingCard lines={6} className="h-80" />;
  if (!data || data.items.length === 0)
    return <EmptyState title="No customer type data" />;

  const chartData = data.items.map((item) => ({
    period: item.period,
    "Walk-in": item.walk_in_count,
    Insurance: item.insurance_count,
    Other: item.other_count,
  }));

  return (
    <div className="rounded-xl border border-border bg-card p-5">
      <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-text-secondary">
        Customer Type Distribution
      </h3>
      <ResponsiveContainer width="100%" height={280}>
        <BarChart data={chartData}>
          <CartesianGrid
            strokeDasharray="3 3"
            stroke={CHART_THEME.gridStroke}
            vertical={false}
          />
          <XAxis
            dataKey="period"
            tick={{ fill: CHART_THEME.tickFill, fontSize: 11 }}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            tick={{ fill: CHART_THEME.tickFill, fontSize: 11 }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v) => formatCompact(v)}
          />
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
          <Bar
            dataKey="Walk-in"
            stackId="type"
            fill={STACK_COLORS.walkIn}
            radius={[0, 0, 0, 0]}
          />
          <Bar
            dataKey="Insurance"
            stackId="type"
            fill={STACK_COLORS.insurance}
            radius={[0, 0, 0, 0]}
          />
          <Bar
            dataKey="Other"
            stackId="type"
            fill={STACK_COLORS.other}
            radius={[4, 4, 0, 0]}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
