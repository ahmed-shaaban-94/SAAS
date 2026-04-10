"use client";

import { memo, useState, useCallback, useMemo } from "react";
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  LineChart,
  Line,
  LabelList,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceDot,
  Cell,
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
import { parseDateKey } from "@/lib/date-utils";
import { useChartTheme } from "@/hooks/use-chart-theme";
import { TrendingUp, TrendingDown, GitCompare, AreaChartIcon, BarChart3, LineChartIcon } from "lucide-react";
import { cn } from "@/lib/utils";

const CHART_ID = "daily-trend";

type ChartVariant = "area" | "bar" | "line";

const VARIANT_ICONS: Record<ChartVariant, React.ComponentType<{ className?: string }>> = {
  area: AreaChartIcon,
  bar: BarChart3,
  line: LineChartIcon,
};

import { ChartTooltip } from "@/components/shared/chart-tooltip";
import { findPeakValley } from "@/lib/chart-utils";

function ChartTypeSwitcher({
  value,
  onChange,
}: {
  value: ChartVariant;
  onChange: (v: ChartVariant) => void;
}) {
  return (
    <div className="flex items-center rounded-lg border border-border bg-page/50 p-0.5" role="tablist" aria-label="Chart type">
      {(["area", "bar", "line"] as ChartVariant[]).map((v) => {
        const Icon = VARIANT_ICONS[v];
        return (
          <button
            key={v}
            onClick={() => onChange(v)}
            className={cn(
              "flex h-6 w-6 items-center justify-center rounded-md transition-all",
              value === v
                ? "bg-accent/20 text-accent shadow-sm"
                : "text-text-secondary hover:text-accent hover:bg-accent/10",
            )}
            role="tab"
            aria-selected={value === v}
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

interface TrendChartInnerProps {
  chartData: Array<{ date: string; value: number; prev?: number }>;
  variant: ChartVariant;
  compare: boolean;
  hasPrev: boolean;
  height: number;
  peakIdx: number;
  valleyIdx: number;
  chartTheme: ReturnType<typeof useChartTheme>;
  onMouseMove?: (index: number | null) => void;
  activeIndex?: number | null;
}

/** Renders the actual chart — shared between inline and spotlight view */
function TrendChartInner({
  chartData,
  variant,
  compare,
  hasPrev,
  height,
  peakIdx,
  valleyIdx,
  chartTheme: CHART_THEME,
  onMouseMove,
  activeIndex,
}: TrendChartInnerProps) {
  const handleMouseMove = useCallback(
    (state: { activeTooltipIndex?: number }) => {
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
      dataKey="date"
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

  const tooltip = <Tooltip content={<ChartTooltip accentClass="text-accent" showPrevious />} />;

  // Peak/Valley reference dots (only for area and line)
  const annotations = variant !== "bar" ? (
    <>
      {peakIdx >= 0 && (
        <ReferenceDot
          x={chartData[peakIdx]?.date}
          y={chartData[peakIdx]?.value}
          r={5}
          fill="#34D399"
          stroke="#fff"
          strokeWidth={2}
          label={{
            value: "Peak",
            position: "top",
            fill: "#34D399",
            fontSize: 10,
            fontWeight: 600,
          }}
        />
      )}
      {valleyIdx >= 0 && (
        <ReferenceDot
          x={chartData[valleyIdx]?.date}
          y={chartData[valleyIdx]?.value}
          r={5}
          fill="#F87171"
          stroke="#fff"
          strokeWidth={2}
          label={{
            value: "Low",
            position: "bottom",
            fill: "#F87171",
            fontSize: 10,
            fontWeight: 600,
          }}
        />
      )}
    </>
  ) : null;

  if (variant === "area") {
    return (
      <ResponsiveContainer width="100%" height={height}>
        <AreaChart
          data={chartData}
          onMouseMove={handleMouseMove}
          onMouseLeave={handleMouseLeave}
        >
          <defs>
            <linearGradient id="dailyGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={CHART_THEME.accentColor} stopOpacity={0.4} />
              <stop offset="50%" stopColor={CHART_THEME.accentColor} stopOpacity={0.1} />
              <stop offset="100%" stopColor={CHART_THEME.accentColor} stopOpacity={0} />
            </linearGradient>
          </defs>
          {commonGrid}
          {commonXAxis}
          {commonYAxis}
          {tooltip}
          <Area
            type="monotone"
            dataKey="value"
            stroke={CHART_THEME.accentColor}
            strokeWidth={2.5}
            fill="url(#dailyGradient)"
            animationDuration={1200}
            animationEasing="ease-out"
          />
          {compare && hasPrev && (
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
          {annotations}
        </AreaChart>
      </ResponsiveContainer>
    );
  }

  if (variant === "bar") {
    const maxValue = Math.max(...chartData.map((d) => d.value));
    return (
      <ResponsiveContainer width="100%" height={height}>
        <BarChart
          data={chartData}
          onMouseMove={handleMouseMove}
          onMouseLeave={handleMouseLeave}
        >
          <defs>
            <linearGradient id="dailyBarGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={CHART_THEME.accentColor} stopOpacity={1} />
              <stop offset="100%" stopColor={CHART_THEME.accentColor} stopOpacity={0.5} />
            </linearGradient>
            <linearGradient id="dailyBarDim" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={CHART_THEME.accentColor} stopOpacity={0.6} />
              <stop offset="100%" stopColor={CHART_THEME.accentColor} stopOpacity={0.25} />
            </linearGradient>
          </defs>
          {commonGrid}
          {commonXAxis}
          {commonYAxis}
          {tooltip}
          <Bar dataKey="value" radius={[4, 4, 0, 0]} animationDuration={1000}>
            {chartData.map((entry, i) => (
              <Cell
                key={entry.date}
                fill={entry.value === maxValue ? "url(#dailyBarGrad)" : "url(#dailyBarDim)"}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    );
  }

  // line
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart
        data={chartData}
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
      >
        {commonGrid}
        {commonXAxis}
        {commonYAxis}
        {tooltip}
        <Line
          type="monotone"
          dataKey="value"
          stroke={CHART_THEME.accentColor}
          strokeWidth={2.5}
          dot={false}
          activeDot={{ r: 5, strokeWidth: 2, fill: CHART_THEME.accentColor }}
          animationDuration={1200}
        />
        {compare && hasPrev && (
          <Line
            type="monotone"
            dataKey="prev"
            stroke={CHART_THEME.accentColor}
            strokeWidth={1.5}
            strokeDasharray="5 5"
            strokeOpacity={0.4}
            dot={false}
            animationDuration={800}
          />
        )}
        {annotations}
      </LineChart>
    </ResponsiveContainer>
  );
}

export const DailyTrendChart = memo(function DailyTrendChart() {
  const { filters } = useFilters();
  const { data: dashboardData, error, isLoading } = useDashboardData();
  const data = dashboardData?.daily_trend;
  const CHART_THEME = useChartTheme();
  const [compare, setCompare] = useState(false);
  const [variant, setVariant] = useState<ChartVariant>("area");
  const [spotlight, setSpotlight] = useState(false);
  const { setActive, clear } = useCrosshair();

  const { previous: prevData } = useComparisonTrend(
    "/api/v1/analytics/trends/daily",
    filters,
    compare,
  );

  const chartData = useMemo(() => {
    if (!data?.points?.length) return [];
    return data.points.map((p, i) => ({
      date: parseDateKey(p.period),
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
  if (error)
    return (
      <ErrorRetry
        title="Failed to load daily trend data"
        description="Failed to load data. Please try again."
      />
    );
  if (!data?.points?.length) return <EmptyState title="No daily trend data" />;

  const isPositiveGrowth = data.growth_pct !== null && data.growth_pct >= 0;

  const growthBadge =
    data.growth_pct !== null ? (
      <div
        className={`flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-semibold ${
          isPositiveGrowth
            ? "bg-growth-green/10 text-growth-green"
            : "bg-growth-red/10 text-growth-red"
        }`}
      >
        {isPositiveGrowth ? (
          <TrendingUp className="h-4 w-4" />
        ) : (
          <TrendingDown className="h-4 w-4" />
        )}
        {data.growth_pct > 0 ? "+" : ""}
        {data.growth_pct.toFixed(1)}%
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
            ? "bg-accent/20 text-accent"
            : "text-text-secondary hover:bg-accent/10 hover:text-accent",
        )}
      >
        <GitCompare className="h-3.5 w-3.5" />
        Compare
      </button>
      <SpotlightTrigger onClick={() => setSpotlight(true)} />
    </div>
  );

  const chartProps: TrendChartInnerProps = {
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
        title="Daily Net Sales"
        subtitle={formatCurrency(data.total)}
        badge={growthBadge}
        actions={actions}
      >
        <TrendChartInner {...chartProps} />
      </ChartCard>

      <ChartSpotlight
        open={spotlight}
        onClose={() => setSpotlight(false)}
        title="Daily Net Sales"
        subtitle={formatCurrency(data.total)}
      >
        <TrendChartInner {...chartProps} height={480} />
      </ChartSpotlight>
    </>
  );
});
