"use client";

import { useMemo } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import type { RankingItem } from "@/types/api";
import { formatCurrency, truncate } from "@/lib/formatters";
import { CHART_COLORS, CHART_THEME } from "@/lib/constants";

interface RankingChartProps {
  items: RankingItem[];
  className?: string;
}

export function RankingChart({ items, className }: RankingChartProps) {
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
      <ResponsiveContainer width="100%" height={items.length * 40 + 20} role="img" aria-label="Ranking chart">
        <BarChart data={chartData} layout="vertical" margin={{ left: 0 }}>
          <XAxis
            type="number"
            tick={{ fill: CHART_THEME.tickFill, fontSize: CHART_THEME.tickFontSize }}
            tickLine={false}
            axisLine={{ stroke: CHART_THEME.axisStroke }}
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
          <Tooltip
            contentStyle={{
              backgroundColor: CHART_THEME.tooltipBg,
              border: `1px solid ${CHART_THEME.tooltipBorder}`,
              borderRadius: "8px",
              color: CHART_THEME.tooltipColor,
            }}
            formatter={(value: number) => [formatCurrency(value), "Revenue"]}
          />
          <Bar dataKey="value" radius={[0, 4, 4, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
