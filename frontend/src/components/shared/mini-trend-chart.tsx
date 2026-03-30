"use client";

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import type { TimeSeriesPoint } from "@/types/api";
import { useChartTheme } from "@/hooks/use-chart-theme";
import { formatCompact } from "@/lib/formatters";

interface MiniTrendChartProps {
  data: TimeSeriesPoint[];
  title?: string;
  className?: string;
}

export function MiniTrendChart({
  data,
  title = "Monthly Trend",
  className,
}: MiniTrendChartProps) {
  const ct = useChartTheme();

  if (!data || data.length === 0) return null;

  return (
    <div className={className}>
      <h3 className="mb-3 text-sm font-medium text-text-secondary">{title}</h3>
      <div className="rounded-lg border border-border bg-card p-4">
        <ResponsiveContainer width="100%" height={160}>
          <AreaChart data={data}>
            <defs>
              <linearGradient id="miniGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={ct.accentColor} stopOpacity={0.3} />
                <stop offset="95%" stopColor={ct.accentColor} stopOpacity={0} />
              </linearGradient>
            </defs>
            <XAxis
              dataKey="period"
              tick={{ fill: ct.tickFill, fontSize: 10 }}
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              tick={{ fill: ct.tickFill, fontSize: 10 }}
              tickLine={false}
              axisLine={false}
              tickFormatter={(v) => formatCompact(v)}
              width={50}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: ct.tooltipBg,
                border: `1px solid ${ct.tooltipBorder}`,
                borderRadius: "8px",
                color: ct.tooltipColor,
                fontSize: 12,
              }}
              formatter={(value: number) => [formatCompact(value), "Net Amount"]}
            />
            <Area
              type="monotone"
              dataKey="value"
              stroke={ct.accentColor}
              strokeWidth={2}
              fill="url(#miniGrad)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
