"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import type { ReturnAnalysis } from "@/types/api";
import { formatCurrency } from "@/lib/formatters";
import { CHART_COLORS } from "@/lib/constants";
import { cn } from "@/lib/utils";
import { useMemo } from "react";

interface ReturnsChartProps {
  items: ReturnAnalysis[];
  className?: string;
}

export function ReturnsChart({ items, className }: ReturnsChartProps) {
  const chartData = useMemo(() => {
    const sorted = [...items].sort(
      (a, b) => b.return_amount - a.return_amount,
    );
    return sorted.slice(0, 10).map((item, i) => ({
      name:
        item.drug_name.length > 20
          ? item.drug_name.slice(0, 20) + "..."
          : item.drug_name,
      value: item.return_amount,
      fill: CHART_COLORS[i % CHART_COLORS.length],
    }));
  }, [items]);

  return (
    <div className={cn("", className)}>
      <ResponsiveContainer width="100%" height={chartData.length * 40 + 20}>
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
