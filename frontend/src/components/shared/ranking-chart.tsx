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

import { ChartTooltip } from "@/components/shared/chart-tooltip";

export function RankingChart({ items, className }: RankingChartProps) {
  const CHART_THEME = useChartTheme();
  const chartData = useMemo(
    () =>
      items.map((item, i) => ({
        name: truncate(item.name, 25),
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
            tick={{ fill: CHART_THEME.tickFill, fontSize: 10 }}
            tickLine={false}
            axisLine={false}
            width={170}
          />
          <Tooltip content={<ChartTooltip accentClass="text-text-primary" />} cursor={{ fill: CHART_THEME.gridStroke, radius: 4 }} />
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
