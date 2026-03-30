"use client";

import { useMemo } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import type { RankingItem } from "@/types/api";
import { formatCurrency, truncate } from "@/lib/formatters";
import { CHART_COLORS } from "@/lib/constants";
import { useChartTheme } from "@/hooks/use-chart-theme";

interface RankingChartProps {
  items: RankingItem[];
  className?: string;
}

function CustomTooltip(props: Record<string, unknown>) {
  const { active, payload } = props;
  const items = payload as Array<{ value: number; payload: { name: string } }> | undefined;
  if (!active || !items?.length) return null;
  return (
    <div className="rounded-xl border border-border bg-card/95 px-4 py-3 shadow-xl backdrop-blur-sm">
      <p className="text-xs font-medium text-text-secondary">{items[0].payload.name}</p>
      <p className="mt-1 text-lg font-bold text-text-primary">
        {formatCurrency(items[0].value)}
      </p>
    </div>
  );
}

export function RankingChart({ items, className }: RankingChartProps) {
  const CHART_THEME = useChartTheme();
  const chartData = useMemo(
    () =>
      items.map((item, i) => ({
        name: truncate(item.name),
        value: item.value,
        fill: CHART_COLORS[i % CHART_COLORS.length],
      })),
    [items],
  );

  return (
    <div className={className}>
      <ResponsiveContainer width="100%" height={items.length * 44 + 20}>
        <BarChart data={chartData} layout="vertical" margin={{ left: 0 }}>
          <XAxis
            type="number"
            tick={{ fill: CHART_THEME.tickFill, fontSize: CHART_THEME.tickFontSize }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v) => formatCurrency(v)}
          />
          <YAxis
            type="category"
            dataKey="name"
            tick={{ fill: CHART_THEME.tickFill, fontSize: CHART_THEME.tickFontSize }}
            tickLine={false}
            axisLine={false}
            width={150}
          />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: CHART_THEME.gridStroke, radius: 4 }} />
          <Bar
            dataKey="value"
            radius={[0, 6, 6, 0]}
            animationDuration={1000}
            animationEasing="ease-out"
          >
            {chartData.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={CHART_COLORS[index % CHART_COLORS.length]}
                fillOpacity={1 - index * 0.06}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
