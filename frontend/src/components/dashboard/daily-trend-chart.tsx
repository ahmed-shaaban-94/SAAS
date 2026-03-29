"use client";

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { useDailyTrend } from "@/hooks/use-daily-trend";
import { useFilters } from "@/contexts/filter-context";
import { LoadingCard } from "@/components/loading-card";
import { EmptyState } from "@/components/empty-state";
import { formatCurrency, formatCompact } from "@/lib/formatters";
import { parseDateKey } from "@/lib/date-utils";
import { CHART_THEME } from "@/lib/constants";

export function DailyTrendChart() {
  const { filters } = useFilters();
  const { data, error, isLoading } = useDailyTrend(filters);

  if (isLoading) return <LoadingCard lines={8} className="h-80" />;
  if (error) return <div className="text-red-400 p-4">Failed to load daily trend data. Please try again.</div>;
  if (!data || data.points.length === 0)
    return <EmptyState title="No daily trend data" />;

  const chartData = data.points.map((p) => ({
    date: parseDateKey(p.period),
    value: p.value,
  }));

  return (
    <div className="rounded-lg border border-border bg-card p-5">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h3 className="text-sm font-medium text-text-secondary">
            Daily Net Sales
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
      <ResponsiveContainer width="100%" height={280}>
        <AreaChart data={chartData}>
          <defs>
            <linearGradient id="dailyGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={CHART_THEME.accentColor} stopOpacity={0.3} />
              <stop offset="95%" stopColor={CHART_THEME.accentColor} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke={CHART_THEME.gridStroke} />
          <XAxis
            dataKey="date"
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
          <Area
            type="monotone"
            dataKey="value"
            stroke={CHART_THEME.accentColor}
            strokeWidth={2}
            fill="url(#dailyGradient)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
