"use client";

import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
} from "recharts";
import { useChartTheme } from "@/hooks/use-chart-theme";
import { formatCurrency } from "@/lib/formatters";
import { ChartCard } from "@/components/shared/chart-card";

interface ComparisonChartProps {
  currentData: Array<{ period: string; value: number }>;
  previousData: Array<{ period: string; value: number }>;
  currentLabel: string;
  previousLabel: string;
}

export function ComparisonChart({
  currentData,
  previousData,
  currentLabel,
  previousLabel,
}: ComparisonChartProps) {
  const theme = useChartTheme();

  // Align by index (day 1, day 2, etc.) so different-length periods overlay correctly
  const maxLen = Math.max(currentData.length, previousData.length);
  const merged = Array.from({ length: maxLen }, (_, i) => ({
    day: i + 1,
    current: currentData[i]?.value ?? null,
    previous: previousData[i]?.value ?? null,
  }));

  return (
    <ChartCard title="Revenue Trend Comparison" subtitle="">
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={merged}>
            <CartesianGrid strokeDasharray="3 3" stroke={theme.gridStroke} />
            <XAxis
              dataKey="day"
              tick={{ fill: theme.tickFill, fontSize: 11 }}
              tickLine={false}
              axisLine={{ stroke: theme.axisStroke }}
            />
            <YAxis
              tick={{ fill: theme.tickFill, fontSize: 11 }}
              tickLine={false}
              axisLine={false}
              tickFormatter={(v) => `${(v / 1000).toFixed(0)}K`}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: theme.tooltipBg,
                border: `1px solid ${theme.tooltipBorder}`,
                borderRadius: "8px",
                color: theme.tooltipColor,
              }}
              formatter={(value: number, name: string) => [
                formatCurrency(value),
                name === "current" ? currentLabel : previousLabel,
              ]}
              labelFormatter={(label) => `Day ${label}`}
            />
            <Legend
              formatter={(value) =>
                value === "current" ? currentLabel : previousLabel
              }
            />
            <Line
              type="monotone"
              dataKey="current"
              stroke={theme.accentColor}
              strokeWidth={2}
              dot={false}
              name="current"
              connectNulls
            />
            <Line
              type="monotone"
              dataKey="previous"
              stroke={theme.chartBlue}
              strokeWidth={2}
              strokeDasharray="5 5"
              dot={false}
              name="previous"
              connectNulls
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </ChartCard>
  );
}
