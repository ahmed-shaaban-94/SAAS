"use client";

import { memo, useState, useCallback, useMemo } from "react";
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
  AreaChart,
  Area,
  LineChart,
  ReferenceDot,
} from "recharts";
import { useDashboardData } from "@/contexts/dashboard-data-context";
import { useComparisonTrend } from "@/hooks/use-comparison-trend";
import { useFilters } from "@/contexts/filter-context";
import { useCrosshair } from "@/contexts/crosshair-context";
import { LoadingCard } from "@/components/loading-card";
import { EmptyState } from "@/components/empty-state";
import { ErrorRetry } from "@/components/error-retry";
import { ChartCard } from "@/components/shared/chart-card";
import { ChartSpotlight, SpotlightTrigger } from "@/components/shared/chart-spotlight";
import { formatCurrency, formatCompact } from "@/lib/formatters";
import { useChartTheme } from "@/hooks/use-chart-theme";
import { TrendingUp, TrendingDown, GitCompare, BarChart3, AreaChartIcon, LineChartIcon } from "lucide-react";
import { cn } from "@/lib/utils";

const CHART_ID = "monthly-trend";

type ChartVariant = "bar" | "area" | "line";

const VARIANT_ICONS: Record<ChartVariant, React.ComponentType<{ className?: string }>> = {
  bar: BarChart3,
  area: AreaChartIcon,
  line: LineChartIcon,
};

function CustomTooltip(props: Record<string, unknown>) {
  const { active, payload, label } = props;
  const items = payload as Array<{ value: number; dataKey: string }> | undefined;
  if (!active || !items?.length) return null;
  const current = items.find((i) => i.dataKey === "value");
  const prev = items.find((i) => i.dataKey === "prev");
  return (
    <div className="rounded-xl border border-border bg-card/95 px-4 py-3 shadow-xl backdrop-blur-sm">
      <p className="text-xs font-medium text-text-secondary">{String(label)}</p>
      <p className="mt-1 text-lg font-bold text-chart-blue">
        {formatCurrency(current?.value ?? 0)}
      </p>
      {prev && prev.value !== undefined && (
        <p className="text-xs text-text-secondary">
          Previous: {formatCurrency(prev.value)}
        </p>
      )}
    </div>
  );
}

function ChartTypeSwitcher({
  value,
  onChange,
}: {
  value: ChartVariant;
  onChange: (v: ChartVariant) => void;
}) {
  return (
    <div className="flex items-center rounded-lg border border-border bg-page/50 p-0.5">
      {(["bar", "area", "line"] as ChartVariant[]).map((v) => {
        const Icon = VARIANT_ICONS[v];
        return (
          <button
            key={v}
            onClick={() => onChange(v)}
            className={cn(
              "flex h-6 w-6 items-center justify-center rounded-md transition-all",
              value === v
                ? "bg-chart-blue/20 text-chart-blue shadow-sm"
                : "text-text-secondary hover:text-chart-blue hover:bg-chart-blue/10",
            )}
            aria-label={`Switch to ${v} chart`}
            title={v.charAt(0).toUpperCase() + v.slice(1)}
          >
            <Icon className="h-3 w-3" />
          </button>
        );
      })}
    </div>
  );
}

function findPeakValley(data: { value: number }[]) {
  if (data.length < 3) return { peakIdx: -1, valleyIdx: -1 };
  let peakIdx = 0;
  let valleyIdx = 0;
  for (let i = 1; i < data.length; i++) {
    if (data[i].value > data[peakIdx].value) peakIdx = i;
    if (data[i].value < data[valleyIdx].value) valleyIdx = i;
  }
  if (peakIdx === valleyIdx) return { peakIdx: -1, valleyIdx: -1 };
  return { peakIdx, valleyIdx };
}

interface MonthlyChartInnerProps {
  chartData: Array<{ month: string; value: number; prev?: number }>;
  variant: ChartVariant;
  compare: boolean;
  hasPrev: boolean;
  height: number;
  peakIdx: number;
  valleyIdx: number;
  chartTheme: ReturnType<typeof useChartTheme>;
  onMouseMove?: (index: number | null) => void;
}

function MonthlyChartInner({
  chartData,
  variant,
  compare,
  hasPrev,
  height,
  peakIdx,
  valleyIdx,
  chartTheme: CHART_THEME,
  onMouseMove,
}: MonthlyChartInnerProps) {
  const maxValue = Math.max(...chartData.map((d) => d.value));

  const handleMouseMove = useCallback(
    (state: any) => {
      if (state?.activeTooltipIndex !== undefined && onMouseMove) {
        onMouseMove(state.activeTooltipIndex);
      }
    },
    [onMouseMove],
  );

  const handleMouseLeave = useCallback(() => {
    onMouseMove?.(null);
  }, [onMouseMove]);

  const commonXAxis = (
    <XAxis
      dataKey="month"
      tick={{ fill: CHART_THEME.tickFill, fontSize: 11 }}
      tickLine={false}
      axisLine={false}
    />
  );

  const commonYAxis = (
    <YAxis
      tick={{ fill: CHART_THEME.tickFill, fontSize: 11 }}
      tickLine={false}
      axisLine={false}
      tickFormatter={(v) => formatCompact(v)}
    />
  );

  const commonGrid = (
    <CartesianGrid strokeDasharray="3 3" stroke={CHART_THEME.gridStroke} vertical={false} />
  );

  const tooltip = (
    <Tooltip
      content={<CustomTooltip />}
      cursor={variant === "bar" ? { fill: CHART_THEME.gridStroke, radius: 4 } : undefined}
    />
  );

  const annotations = variant !== "bar" ? (
    <>
      {peakIdx >= 0 && (
        <ReferenceDot
          x={chartData[peakIdx]?.month}
          y={chartData[peakIdx]?.value}
          r={5}
          fill="#34D399"
          stroke="#fff"
          strokeWidth={2}
          label={{ value: "Peak", position: "top", fill: "#34D399", fontSize: 10, fontWeight: 600 }}
        />
      )}
      {valleyIdx >= 0 && (
        <ReferenceDot
          x={chartData[valleyIdx]?.month}
          y={chartData[valleyIdx]?.value}
          r={5}
          fill="#F87171"
          stroke="#fff"
          strokeWidth={2}
          label={{ value: "Low", position: "bottom", fill: "#F87171", fontSize: 10, fontWeight: 600 }}
        />
      )}
    </>
  ) : null;

  if (variant === "bar") {
    return (
      <ResponsiveContainer width="100%" height={height}>
        <ComposedChart data={chartData} onMouseMove={handleMouseMove} onMouseLeave={handleMouseLeave}>
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
          {commonGrid}
          {commonXAxis}
          {commonYAxis}
          {tooltip}
          <Bar dataKey="value" radius={[6, 6, 0, 0]} animationDuration={1200} animationEasing="ease-out">
            {chartData.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={entry.value === maxValue ? "url(#barGradient)" : "url(#barGradientDim)"}
              />
            ))}
          </Bar>
          {compare && hasPrev && (
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
    );
  }

  if (variant === "area") {
    return (
      <ResponsiveContainer width="100%" height={height}>
        <AreaChart data={chartData} onMouseMove={handleMouseMove} onMouseLeave={handleMouseLeave}>
          <defs>
            <linearGradient id="monthlyAreaGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={CHART_THEME.chartBlue} stopOpacity={0.4} />
              <stop offset="50%" stopColor={CHART_THEME.chartBlue} stopOpacity={0.1} />
              <stop offset="100%" stopColor={CHART_THEME.chartBlue} stopOpacity={0} />
            </linearGradient>
          </defs>
          {commonGrid}
          {commonXAxis}
          {commonYAxis}
          {tooltip}
          <Area
            type="monotone"
            dataKey="value"
            stroke={CHART_THEME.chartBlue}
            strokeWidth={2.5}
            fill="url(#monthlyAreaGrad)"
            animationDuration={1200}
          />
          {compare && hasPrev && (
            <Area type="monotone" dataKey="prev" stroke={CHART_THEME.chartBlue} strokeWidth={1.5} strokeDasharray="5 5" strokeOpacity={0.4} fill="none" />
          )}
          {annotations}
        </AreaChart>
      </ResponsiveContainer>
    );
  }

  // line
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={chartData} onMouseMove={handleMouseMove} onMouseLeave={handleMouseLeave}>
        {commonGrid}
        {commonXAxis}
        {commonYAxis}
        {tooltip}
        <Line
          type="monotone"
          dataKey="value"
          stroke={CHART_THEME.chartBlue}
          strokeWidth={2.5}
          dot={false}
          activeDot={{ r: 5, strokeWidth: 2, fill: CHART_THEME.chartBlue }}
          animationDuration={1200}
        />
        {compare && hasPrev && (
          <Line type="monotone" dataKey="prev" stroke={CHART_THEME.chartBlue} strokeWidth={1.5} strokeDasharray="5 5" strokeOpacity={0.4} dot={false} />
        )}
        {annotations}
      </LineChart>
    </ResponsiveContainer>
  );
}

export const MonthlyTrendChart = memo(function MonthlyTrendChart() {
  const { filters } = useFilters();
  const { data: dashboardData, error, isLoading } = useDashboardData();
  const data = dashboardData?.monthly_trend;
  const CHART_THEME = useChartTheme();
  const [compare, setCompare] = useState(false);
  const [variant, setVariant] = useState<ChartVariant>("bar");
  const [spotlight, setSpotlight] = useState(false);
  const { setActive, clear } = useCrosshair();

  const { previous: prevData } = useComparisonTrend(
    "/api/v1/analytics/trends/monthly",
    filters,
    compare,
  );

  const chartData = useMemo(() => {
    if (!data?.points?.length) return [];
    return data.points.map((p, i) => ({
      month: p.period,
      value: p.value,
      prev: prevData?.points[i]?.value ?? undefined,
    }));
  }, [data, prevData]);

  const { peakIdx, valleyIdx } = useMemo(() => findPeakValley(chartData), [chartData]);

  const handleCrosshair = useCallback(
    (index: number | null) => {
      if (index !== null) setActive(index, CHART_ID);
      else clear();
    },
    [setActive, clear],
  );

  if (isLoading) return <LoadingCard lines={8} className="h-80" />;
  if (error) return <ErrorRetry title="Failed to load monthly trend data" description="Failed to load data. Please try again." />;
  if (!data?.points?.length) return <EmptyState title="No monthly trend data" />;

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

  const actions = (
    <div className="flex items-center gap-1.5">
      <ChartTypeSwitcher value={variant} onChange={setVariant} />
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
      <SpotlightTrigger onClick={() => setSpotlight(true)} />
    </div>
  );

  const chartProps: MonthlyChartInnerProps = {
    chartData,
    variant,
    compare,
    hasPrev: !!prevData,
    height: 280,
    peakIdx,
    valleyIdx,
    chartTheme: CHART_THEME,
    onMouseMove: handleCrosshair,
  };

  return (
    <>
      <ChartCard
        title="Monthly Net Sales"
        subtitle={formatCurrency(data.total)}
        badge={growthBadge}
        actions={actions}
      >
        <MonthlyChartInner {...chartProps} />
      </ChartCard>

      <ChartSpotlight
        open={spotlight}
        onClose={() => setSpotlight(false)}
        title="Monthly Net Sales"
        subtitle={formatCurrency(data.total)}
      >
        <MonthlyChartInner {...chartProps} height={480} />
      </ChartSpotlight>
    </>
  );
});
