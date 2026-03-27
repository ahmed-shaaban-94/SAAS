"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import type { RankingItem } from "@/types/api";
import { formatCurrency } from "@/lib/formatters";
import { CHART_COLORS } from "@/lib/constants";
import { cn } from "@/lib/utils";

interface RankingChartProps {
  items: RankingItem[];
  className?: string;
}

export function RankingChart({ items, className }: RankingChartProps) {
  const chartData = items.map((item, i) => ({
    name: item.name.length > 20 ? item.name.slice(0, 20) + "..." : item.name,
    value: item.value,
    fill: CHART_COLORS[i % CHART_COLORS.length],
  }));

  return (
    <div className={cn("", className)}>
      <ResponsiveContainer width="100%" height={items.length * 40 + 20}>
        <BarChart data={chartData} layout="vertical" margin={{ left: 0 }}>
          <XAxis
            type="number"
            tick={{ fill: "#A8B3BD", fontSize: 11 }}
            tickLine={false}
            axisLine={{ stroke: "#30363D" }}
            tickFormatter={(v) => formatCurrency(v)}
          />
          <YAxis
            type="category"
            dataKey="name"
            tick={{ fill: "#A8B3BD", fontSize: 11 }}
            tickLine={false}
            axisLine={false}
            width={150}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "#161B22",
              border: "1px solid #30363D",
              borderRadius: "8px",
              color: "#E6EDF3",
            }}
            formatter={(value: number) => [formatCurrency(value), "Revenue"]}
          />
          <Bar dataKey="value" radius={[0, 4, 4, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
