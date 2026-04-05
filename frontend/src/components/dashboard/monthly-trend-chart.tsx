"use client";

import { memo, useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  Line,
  ComposedChart,
} from "recharts";
import { useDashboardData } from "@/contexts/dashboard-data-context";
import { useComparisonTrend } from "@/hooks/use-comparison-trend";
import { useFilters } from "@/contexts/filter-context";
import { LoadingCard } from "@/components/loading-card";
import { EmptyState } from "@/components/empty-state";
import { ErrorRetry } from "@/components/error-retry";
import { ChartCard } from "@/components/shared/chart-card";
import { formatCurrency, formatCompact } from "@/lib/formatters";
import { useChartTheme } from "@/hooks/use-chart-theme";
import { TrendingUp, TrendingDown, GitCompare } from "lucide-react";
import { cn } from "@/lib/utils";

function CustomTooltip(props: Record<string, unknown>) {
  const { active, payload, label } = props;
  const items = payload as Array<{ value: number }> | undefined;
  if (!active || !items?.length) return null;
  return (
    <div className="rounded-xl border border-border bg-card/95 px-4 py-3 shadow-xl backdrop-blur-sm">
      <p className="text-xs font-medium text-text-secondary">{String(label)}</p>
      <p className="mt-1 text-lg font-bold text-chart-blue">
        {formatCurrency(items[0].value)}
      </p>
    </div>
  );
}

export const MonthlyTrendChart = memo(function MonthlyTrendChart() {
  const { filters } = useFilters();
  const { data: dashboardData, error, isLoading } = useDashboardData();
  const data = dashboardData?.monthly_trend;
  const CHART_THEME = useChartTheme();
  const [compare, setCompare] = useState(false);

  const { previous: prevData } = useComparisonTrend(
    "/api/v1/analytics/trends/monthly",
    filters,
    compare,
  );

  if (isLoading) return <LoadingCard lines={8} className="h-80" />;
  if (error) return <ErrorRetry title="Failed to load monthly trend data" description="Failed to load data. Please try again." />;
  if (!data?.points?.length)
    return <EmptyState title="No monthly trend data" />;

  const chartData = data.points.map((p, i) => ({
    month: p.period,
    value: p.value,
    prev: prevData?.points[i]?.value ?? undefined,
  }));

  const maxValue = Math.max(...chartData.map(d => d.value));
  const isPositiveGrowth = data.growth_pct !== null && data.growth_pct >= 0;

  const growthBadge = data.growth_pct !== null ? (
    <div className={`flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-semibold ${
      isPositiveGrowth
        ? "bg-growth-green/10 text-growth-green"
        : "bg-growth-red/10 text-growth-red"
    }`}>
      {isPositiveGrowth ? <TrendingUp className="h-4 w-4" /> : <TrendingDown className="h-4 w-4" />}
      {data.growth_pct > 0 ? "+" : ""}{data.growth_pct.toFixed(1)}%
    </div>
  ) : undefined;

  const compareButton = (
    <button
      onClick={() => setCompare((v) => !v)}
      className={cn(
        "flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-medium transition-all",
        compare
          ? "bg-chart-blue/20 text-chart-blue"
          : "text-text-secondary hover:bg-chart-blue/10 hover:text-chart-blue"
      )}
    >
      <GitCompare className="h-3.5 w-3.5" />
      Compare
    </button>
  );

  return (
    <ChartCard
      title="Monthly Net Sales"
      subtitle={formatCurrency(data.total)}
      badge={growthBadge}
      actions={compareButton}
    >
      <ResponsiveContainer width="100%" height={280}>
        <ComposedChart data={chartData}>
          <defs>
            <linearGradient id="barGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={CHART_THEME.chartBlue} stopOpacity={1} />
              <stop offset="100%" stopColor={CHART_THEME.chartBlue} stopOpacity={0.6} />
            </linearGradient>
            <linearGradient id="barGradientDim" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={CHART_THEME.chartBlue} stopOpacity={0.7} />
              <stop offset="100%" stopColor={CHART_THEME.chartBlue} stopOpacity={0.3} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke={CHART_THEME.gridStroke} vertical={false} />
          <XAxis
            dataKey="month"
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
          <Tooltip content={<CustomTooltip />} cursor={{ fill: CHART_THEME.gridStroke, radius: 4 }} />
          <Bar
            dataKey="value"
            radius={[6, 6, 0, 0]}
            animationDuration={1200}
            animationEasing="ease-out"
          >
            {chartData.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={entry.value === maxValue ? "url(#barGradient)" : "url(#barGradientDim)"}
              />
            ))}
          </Bar>
          {compare && prevData && (
            <Line
              type="monotone"
              dataKey="prev"
              stroke={CHART_THEME.chartBlue}
              strokeWidth={2}
              strokeDasharray="5 5"
              strokeOpacity={0.5}
              dot={false}
            />
          )}
        </ComposedChart>
      </ResponsiveContainer>
    </ChartCard>
  );
});
