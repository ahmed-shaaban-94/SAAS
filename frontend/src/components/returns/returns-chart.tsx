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
import type { ReturnAnalysis } from "@/types/api";
import { formatCurrency, truncate } from "@/lib/formatters";
import { CHART_COLORS, CHART_THEME, CHART_MAX_ITEMS } from "@/lib/constants";

interface ReturnsChartProps {
  items: ReturnAnalysis[];
  className?: string;
}

export function ReturnsChart({ items, className }: ReturnsChartProps) {
  const chartData = useMemo(() => {
    const sorted = [...items].sort(
      (a, b) => b.return_amount - a.return_amount,
    );
    return sorted.slice(0, CHART_MAX_ITEMS).map((item, i) => ({
      name: truncate(item.drug_name),
      value: item.return_amount,
      fill: CHART_COLORS[i % CHART_COLORS.length],
    }));
  }, [items]);

  return (
    <div className={className}>
      <ResponsiveContainer width="100%" height={chartData.length * 40 + 20} role="img" aria-label="Returns chart">
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
            formatter={(value: number) => [
              formatCurrency(value),
              "Return Amount",
            ]}
          />
          <Bar dataKey="value" radius={[0, 4, 4, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
