"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { useMonthlyTrend } from "@/hooks/use-monthly-trend";
import { useFilters } from "@/contexts/filter-context";
import { LoadingCard } from "@/components/loading-card";
import { EmptyState } from "@/components/empty-state";
import { ErrorRetry } from "@/components/error-retry";
import { formatCurrency, formatCompact } from "@/lib/formatters";
import { CHART_COLORS, CHART_THEME } from "@/lib/constants";

export function MonthlyTrendChart() {
  const { filters } = useFilters();
  const { data, error, isLoading } = useMonthlyTrend(filters);

  if (isLoading) return <LoadingCard lines={8} className="h-80" />;
  if (error) return <ErrorRetry title="Failed to load monthly trend data" description="Failed to load data. Please try again." />;
  if (!data || data.points.length === 0)
    return <EmptyState title="No monthly trend data" />;

  const chartData = data.points.map((p) => ({
    month: p.period,
    value: p.value,
  }));

  return (
    <div className="rounded-lg border border-border bg-card p-5">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h3 className="text-sm font-medium text-text-secondary">
            Monthly Net Sales
          </h3>
          <p className="text-xl font-bold text-text-primary">
            {formatCurrency(data.total)}
          </p>
        </div>
        {data.growth_pct !== null && (
          <span
            className={`text-sm font-medium ${
              data.growth_pct >= 0 ? "text-growth-green" : "text-growth-red"
            }`}
          >
            {data.growth_pct > 0 ? "+" : ""}
            {data.growth_pct.toFixed(1)}%
          </span>
        )}
      </div>
      <ResponsiveContainer width="100%" height={280} role="img" aria-label="Monthly net sales trend chart">
        <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke={CHART_THEME.gridStroke} />
          <XAxis
            dataKey="month"
            tick={{ fill: CHART_THEME.tickFill, fontSize: 12 }}
            tickLine={false}
            axisLine={{ stroke: CHART_THEME.axisStroke }}
          />
          <YAxis
            tick={{ fill: CHART_THEME.tickFill, fontSize: 12 }}
            tickLine={false}
            axisLine={{ stroke: CHART_THEME.axisStroke }}
            tickFormatter={(v) => formatCompact(v)}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: CHART_THEME.tooltipBg,
              border: `1px solid ${CHART_THEME.tooltipBorder}`,
              borderRadius: "8px",
              color: CHART_THEME.tooltipColor,
            }}
            formatter={(value: number) => [formatCurrency(value), "Net Sales"]}
          />
          <Bar dataKey="value" fill={CHART_COLORS[1]} radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
