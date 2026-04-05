"use client";

import { useReturnsTrend } from "@/hooks/use-returns-trend";
import { formatCurrency, formatNumber } from "@/lib/formatters";
import { LoadingCard } from "@/components/loading-card";
import { EmptyState } from "@/components/empty-state";
import {
  ComposedChart, Bar, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer,
} from "recharts";
import { useChartTheme } from "@/hooks/use-chart-theme";
import { TrendingDown } from "lucide-react";

export function ReturnsTrendChart() {
  const { data, isLoading } = useReturnsTrend();
  const theme = useChartTheme();

  if (isLoading) return <LoadingCard className="h-72" />;
  if (!data?.points?.length) return <EmptyState title="No returns trend data" />;

  const chartData = data.points.map((p) => ({
    period: p.period,
    count: p.return_count,
    amount: p.return_amount,
    rate: p.return_rate,
  }));

  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <TrendingDown className="h-4 w-4 text-red-500" />
          <h3 className="text-sm font-semibold text-text-primary">Returns Trend</h3>
        </div>
        <div className="flex items-center gap-4 text-xs text-text-secondary">
          <span>Total: {formatNumber(data.total_returns)} returns</span>
          <span>Avg Rate: {data.avg_return_rate.toFixed(2)}%</span>
        </div>
      </div>

      <ResponsiveContainer width="100%" height={250}>
        <ComposedChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={theme.gridStroke} />
          <XAxis dataKey="period" tick={{ fontSize: 10, fill: theme.tickFill }} />
          <YAxis
            yAxisId="count"
            tick={{ fontSize: 10, fill: theme.tickFill }}
            tickFormatter={(v: number) => formatNumber(v)}
          />
          <YAxis
            yAxisId="rate"
            orientation="right"
            domain={[0, "auto"]}
            tick={{ fontSize: 10, fill: theme.tickFill }}
            tickFormatter={(v: number) => `${v}%`}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: theme.tooltipBg,
              border: `1px solid ${theme.tooltipBorder}`,
              borderRadius: "8px",
              fontSize: "12px",
              color: theme.tooltipColor,
            }}
            formatter={(value: number, name: string) => {
              if (name === "count") return [formatNumber(value), "Return Count"];
              if (name === "amount") return [formatCurrency(value), "Return Amount"];
              return [`${value.toFixed(2)}%`, "Return Rate"];
            }}
          />
          <Bar yAxisId="count" dataKey="count" fill="#EF4444" opacity={0.6} radius={[4, 4, 0, 0]} />
          <Line yAxisId="rate" dataKey="rate" type="monotone" stroke={theme.chartAmber} strokeWidth={2} dot={{ r: 3 }} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
