"use client";

import { memo, useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { useBillingBreakdown } from "@/hooks/use-billing-breakdown";
import { useFilters } from "@/contexts/filter-context";
import { LoadingCard } from "@/components/loading-card";
import { EmptyState } from "@/components/empty-state";
import { formatCurrency, formatCompact } from "@/lib/formatters";
import { CHART_COLORS } from "@/lib/constants";
import { useChartTheme } from "@/hooks/use-chart-theme";
import { ChartSpotlight, SpotlightTrigger } from "@/components/shared/chart-spotlight";

/** Custom legend showing colored dot + label for each billing group */
function BillingLegend({
  chartData,
}: {
  chartData: Array<{ name: string; value: number; pct: number; count: number }>;
}) {
  return (
    <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1.5 px-2">
      {chartData.map((d, i) => (
        <div key={d.name} className="flex items-center gap-1.5 text-xs text-text-secondary">
          <span
            className="inline-block h-2.5 w-2.5 rounded-full"
            style={{ backgroundColor: CHART_COLORS[i % CHART_COLORS.length] }}
          />
          <span>{d.name}</span>
          <span className="font-medium text-text-primary">{d.pct.toFixed(1)}%</span>
        </div>
      ))}
    </div>
  );
}

function CustomTooltip(props: Record<string, unknown>) {
  const { active, payload } = props;
  const items = payload as
    | Array<{
        name: string;
        value: number;
        payload: { name: string; value: number; pct: number; count: number };
      }>
    | undefined;
  if (!active || !items?.length) return null;
  const d = items[0].payload;
  return (
    <div className="rounded-xl border border-border bg-card/95 px-4 py-3 shadow-xl backdrop-blur-sm">
      <p className="text-xs font-medium text-text-secondary">{d.name}</p>
      <p className="mt-1 text-lg font-bold text-accent">
        {formatCurrency(d.value)}
      </p>
      <p className="text-xs text-text-secondary">
        {d.count.toLocaleString()} transactions ({d.pct.toFixed(1)}%)
      </p>
    </div>
  );
}

function HorizontalBarInner({
  chartData,
  height,
  CHART_THEME,
}: {
  chartData: Array<{ name: string; value: number; pct: number; count: number }>;
  height: number;
  CHART_THEME: ReturnType<typeof useChartTheme>;
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={chartData} layout="vertical" margin={{ left: 10, right: 80 }}>
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
          width={80}
        />
        <Tooltip content={<CustomTooltip />} cursor={{ fill: "rgba(255,255,255,0.04)" }} />
        <Bar dataKey="value" radius={[0, 6, 6, 0]} barSize={28} label={<BarLabel theme={CHART_THEME} />}>
          {chartData.map((_, index) => (
            <Cell
              key={`cell-${index}`}
              fill={CHART_COLORS[index % CHART_COLORS.length]}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

/** Custom label showing value + percentage at the end of each bar.
 *  Recharts injects x/y/width/height/value/index at render time. */
interface BarLabelProps {
  x?: number;
  y?: number;
  width?: number;
  height?: number;
  value?: number;
  index?: number;
  theme: { tickFill: string };
  content?: { props?: { data?: Array<{ pct?: number }> } };
}

function BarLabel(props: BarLabelProps) {
  const { x = 0, y = 0, width = 0, height: barHeight = 0, value = 0, index = 0, theme } = props;
  // Access the chart data from the parent — recharts passes the entry via props
  const entry = props.content?.props?.data?.[index];
  const pct = entry?.pct;

  return (
    <text
      x={x + width + 6}
      y={y + barHeight / 2}
      fill={theme.tickFill}
      fontSize={11}
      dominantBaseline="central"
    >
      {formatCompact(value)}{pct !== undefined ? ` (${pct.toFixed(1)}%)` : ""}
    </text>
  );
}

export const BillingBreakdownChart = memo(function BillingBreakdownChart() {
  const { filters } = useFilters();
  const { data, isLoading } = useBillingBreakdown(filters);
  const CHART_THEME = useChartTheme();
  const [spotlight, setSpotlight] = useState(false);

  if (isLoading) return <LoadingCard lines={6} className="h-80" />;
  if (!data?.items?.length) return <EmptyState title="No billing data" />;

  const chartData = data.items
    .map((item) => ({
      name: item.billing_group,
      value: item.total_net_amount,
      pct: item.pct_of_total,
      count: item.transaction_count,
    }))
    .sort((a, b) => b.value - a.value);

  const barHeight = Math.max(chartData.length * 48, 160);

  return (
    <>
      <div className="group rounded-xl border border-border bg-card p-5 transition-all duration-300 hover:border-accent/30 hover:shadow-lg hover:shadow-accent/5">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-sm font-semibold uppercase tracking-wider text-text-secondary">
            Billing Method Distribution
          </h3>
          <SpotlightTrigger onClick={() => setSpotlight(true)} />
        </div>
        <HorizontalBarInner
          chartData={chartData}
          height={barHeight}
          CHART_THEME={CHART_THEME}
        />
        <BillingLegend chartData={chartData} />
      </div>

      <ChartSpotlight
        open={spotlight}
        onClose={() => setSpotlight(false)}
        title="Billing Method Distribution"
      >
        <HorizontalBarInner
          chartData={chartData}
          height={barHeight + 80}
          CHART_THEME={CHART_THEME}
        />
      </ChartSpotlight>
    </>
  );
});
