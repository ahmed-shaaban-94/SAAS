"use client";

import { memo, useState } from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { useDashboardData } from "@/contexts/dashboard-data-context";
import { useComparisonTrend } from "@/hooks/use-comparison-trend";
import { useFilters } from "@/contexts/filter-context";
import { LoadingCard } from "@/components/loading-card";
import { EmptyState } from "@/components/empty-state";
import { ErrorRetry } from "@/components/error-retry";
import { ChartCard } from "@/components/shared/chart-card";
import { formatCurrency, formatCompact } from "@/lib/formatters";
import { parseDateKey } from "@/lib/date-utils";
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
      <p className="mt-1 text-lg font-bold text-accent">
        {formatCurrency(items[0].value)}
      </p>
    </div>
  );
}

export const DailyTrendChart = memo(function DailyTrendChart() {
  const { filters } = useFilters();
  const { data: dashboardData, error, isLoading } = useDashboardData();
  const data = dashboardData?.daily_trend;
  const CHART_THEME = useChartTheme();
  const [compare, setCompare] = useState(false);

  const { previous: prevData } = useComparisonTrend(
    "/api/v1/analytics/trends/daily",
    filters,
    compare,
  );

  if (isLoading) return <LoadingCard lines={8} className="h-80" />;
  if (error) return <ErrorRetry title="Failed to load daily trend data" description="Failed to load data. Please try again." />;
  if (!data?.points?.length)
    return <EmptyState title="No daily trend data" />;

  const chartData = data.points.map((p, i) => ({
    date: parseDateKey(p.period),
    value: p.value,
    prev: prevData?.points[i]?.value ?? undefined,
  }));

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
          ? "bg-accent/20 text-accent"
          : "text-text-secondary hover:bg-accent/10 hover:text-accent"
      )}
    >
      <GitCompare className="h-3.5 w-3.5" />
      Compare
    </button>
  );

  return (
    <ChartCard
      title="Daily Net Sales"
      subtitle={formatCurrency(data.total)}
      badge={growthBadge}
      actions={compareButton}
    >
      <ResponsiveContainer width="100%" height={280}>
        <AreaChart data={chartData}>
          <defs>
            <linearGradient id="dailyGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={CHART_THEME.accentColor} stopOpacity={0.4} />
              <stop offset="50%" stopColor={CHART_THEME.accentColor} stopOpacity={0.1} />
              <stop offset="100%" stopColor={CHART_THEME.accentColor} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke={CHART_THEME.gridStroke} vertical={false} />
          <XAxis
            dataKey="date"
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
          <Area
            type="monotone"
            dataKey="value"
            stroke={CHART_THEME.accentColor}
            strokeWidth={2.5}
            fill="url(#dailyGradient)"
            animationDuration={1200}
            animationEasing="ease-out"
          />
          {compare && prevData && (
            <Area
              type="monotone"
              dataKey="prev"
              stroke={CHART_THEME.accentColor}
              strokeWidth={1.5}
              strokeDasharray="5 5"
              strokeOpacity={0.4}
              fill="none"
              animationDuration={800}
            />
          )}
        </AreaChart>
      </ResponsiveContainer>
    </ChartCard>
  );
});
