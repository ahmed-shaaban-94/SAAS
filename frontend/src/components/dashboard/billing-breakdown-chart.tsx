"use client";

import { memo, useState } from "react";
import {
  PieChart,
  Pie,
  Cell,
  Legend,
  Tooltip,
  ResponsiveContainer,
  Sector,
} from "recharts";
import { useBillingBreakdown } from "@/hooks/use-billing-breakdown";
import { useFilters } from "@/contexts/filter-context";
import { LoadingCard } from "@/components/loading-card";
import { EmptyState } from "@/components/empty-state";
import { formatCurrency, formatNumber } from "@/lib/formatters";
import { CHART_COLORS } from "@/lib/constants";
import { useChartTheme } from "@/hooks/use-chart-theme";
import { ChartSpotlight, SpotlightTrigger } from "@/components/shared/chart-spotlight";

function CustomTooltip(props: Record<string, unknown>) {
  const { active, payload } = props;
  const items = payload as Array<{
    name: string;
    value: number;
    payload: { pct: number; count: number };
  }> | undefined;
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

/** Active shape renderer — enlarges the hovered slice with a glow */
function renderActiveShape(props: any) {
  const {
    cx,
    cy,
    innerRadius,
    outerRadius,
    startAngle,
    endAngle,
    fill,
  } = props;

  return (
    <g>
      <Sector
        cx={cx}
        cy={cy}
        innerRadius={innerRadius - 2}
        outerRadius={outerRadius + 8}
        startAngle={startAngle}
        endAngle={endAngle}
        fill={fill}
        style={{ filter: "drop-shadow(0 0 8px rgba(255,255,255,0.15))" }}
      />
      <Sector
        cx={cx}
        cy={cy}
        innerRadius={innerRadius - 2}
        outerRadius={innerRadius}
        startAngle={startAngle}
        endAngle={endAngle}
        fill={fill}
        opacity={0.4}
      />
    </g>
  );
}

/** Dynamic center label — shows hovered segment or total */
function CenterLabel({
  cx,
  cy,
  activeEntry,
  total,
  theme,
}: {
  cx: number;
  cy: number;
  activeEntry: { name: string; value: number; pct: number } | null;
  total: number;
  theme: ReturnType<typeof useChartTheme>;
}) {
  return (
    <g>
      <text
        x={cx}
        y={cy - 8}
        textAnchor="middle"
        fill={theme.tooltipColor}
        fontSize={activeEntry ? 13 : 11}
        fontWeight={600}
        className="transition-all"
      >
        {activeEntry ? activeEntry.name : "Total"}
      </text>
      <text
        x={cx}
        y={cy + 14}
        textAnchor="middle"
        fill={theme.accentColor}
        fontSize={16}
        fontWeight={700}
      >
        {formatCurrency(activeEntry ? activeEntry.value : total)}
      </text>
      {activeEntry && (
        <text
          x={cx}
          y={cy + 32}
          textAnchor="middle"
          fill={theme.tickFill}
          fontSize={10}
        >
          {activeEntry.pct.toFixed(1)}%
        </text>
      )}
    </g>
  );
}

function DonutInner({
  chartData,
  total,
  height,
  CHART_THEME,
}: {
  chartData: Array<{ name: string; value: number; pct: number; count: number }>;
  total: number;
  height: number;
  CHART_THEME: ReturnType<typeof useChartTheme>;
}) {
  const [activeIdx, setActiveIdx] = useState<number | undefined>(undefined);

  const activeEntry = activeIdx !== undefined ? chartData[activeIdx] : null;

  return (
    <ResponsiveContainer width="100%" height={height}>
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
          activeIndex={activeIdx}
          activeShape={renderActiveShape}
          onMouseEnter={(_, index) => setActiveIdx(index)}
          onMouseLeave={() => setActiveIdx(undefined)}
        >
          {chartData.map((_, index) => (
            <Cell
              key={`cell-${index}`}
              fill={CHART_COLORS[index % CHART_COLORS.length]}
              stroke="transparent"
              className="transition-opacity duration-200"
              opacity={activeIdx !== undefined && activeIdx !== index ? 0.4 : 1}
            />
          ))}
        </Pie>
        {/* Center label */}
        <CenterLabel
          cx={typeof window !== "undefined" ? 0 : 0}
          cy={0}
          activeEntry={activeEntry}
          total={total}
          theme={CHART_THEME}
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
        {/* Custom center text rendered via Pie label prop */}
        <text
          x="50%"
          y="46%"
          textAnchor="middle"
          fill={CHART_THEME.tooltipColor}
          fontSize={activeEntry ? 13 : 11}
          fontWeight={600}
        >
          {activeEntry ? activeEntry.name : "Total"}
        </text>
        <text
          x="50%"
          y="54%"
          textAnchor="middle"
          fill={CHART_THEME.accentColor}
          fontSize={16}
          fontWeight={700}
          dominantBaseline="hanging"
        >
          {formatCurrency(activeEntry ? activeEntry.value : total)}
        </text>
        {activeEntry && (
          <text
            x="50%"
            y="62%"
            textAnchor="middle"
            fill={CHART_THEME.tickFill}
            fontSize={10}
            dominantBaseline="hanging"
          >
            {activeEntry.pct.toFixed(1)}%
          </text>
        )}
      </PieChart>
    </ResponsiveContainer>
  );
}

export const BillingBreakdownChart = memo(function BillingBreakdownChart() {
  const { filters } = useFilters();
  const { data, isLoading } = useBillingBreakdown(filters);
  const CHART_THEME = useChartTheme();
  const [spotlight, setSpotlight] = useState(false);

  if (isLoading) return <LoadingCard lines={6} className="h-80" />;
  if (!data?.items?.length) return <EmptyState title="No billing data" />;

  const chartData = data.items.map((item) => ({
    name: item.billing_group,
    value: item.total_net_amount,
    pct: item.pct_of_total,
    count: item.transaction_count,
  }));

  const total = chartData.reduce((sum, d) => sum + d.value, 0);

  return (
    <>
      <div className="group rounded-xl border border-border bg-card p-5 transition-all duration-300 hover:border-accent/30 hover:shadow-lg hover:shadow-accent/5">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-sm font-semibold uppercase tracking-wider text-text-secondary">
            Billing Method Distribution
          </h3>
          <SpotlightTrigger onClick={() => setSpotlight(true)} />
        </div>
        <DonutInner
          chartData={chartData}
          total={total}
          height={280}
          CHART_THEME={CHART_THEME}
        />
      </div>

      <ChartSpotlight
        open={spotlight}
        onClose={() => setSpotlight(false)}
        title="Billing Method Distribution"
      >
        <DonutInner
          chartData={chartData}
          total={total}
          height={420}
          CHART_THEME={CHART_THEME}
        />
      </ChartSpotlight>
    </>
  );
});
