"use client";

import { useABCAnalysis } from "@/hooks/use-abc-analysis";
import { formatCurrency, formatCompact } from "@/lib/formatters";
import { LoadingCard } from "@/components/loading-card";
import { EmptyState } from "@/components/empty-state";
import {
  ComposedChart, Bar, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine,
} from "recharts";
import { useChartTheme } from "@/hooks/use-chart-theme";

export function ParetoChart() {
  const { data, isLoading } = useABCAnalysis("product");
  const theme = useChartTheme();

  if (isLoading) return <LoadingCard className="h-80" />;
  if (!data || data.items.length === 0) return <EmptyState title="No product data available" />;

  // Take top 20 for readability
  const chartData = data.items.slice(0, 20).map((item) => ({
    name: item.name.length > 15 ? item.name.substring(0, 15) + "..." : item.name,
    fullName: item.name,
    revenue: item.value,
    cumulative: item.cumulative_pct,
    class: item.abc_class,
  }));

  const getBarColor = (cls: string) => {
    if (cls === "A") return "#4F46E5";
    if (cls === "B") return "#FFB300";
    return "#64748b";
  };

  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-semibold text-text-primary">Pareto Analysis (80/20)</h3>
          <p className="text-xs text-text-secondary mt-0.5">
            {data.class_a_count} products ({data.class_a_pct.toFixed(1)}% revenue) = Class A
          </p>
        </div>
        <div className="flex items-center gap-3 text-[10px]">
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-[#4F46E5]" />A</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-[#FFB300]" />B</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-[#64748b]" />C</span>
        </div>
      </div>

      <ResponsiveContainer width="100%" height={300}>
        <ComposedChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 60 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={theme.gridStroke} />
          <XAxis
            dataKey="name"
            angle={-45}
            textAnchor="end"
            tick={{ fontSize: 10, fill: theme.tickFill }}
            interval={0}
          />
          <YAxis
            yAxisId="revenue"
            tick={{ fontSize: 10, fill: theme.tickFill }}
            tickFormatter={(v: number) => formatCompact(v)}
          />
          <YAxis
            yAxisId="cumulative"
            orientation="right"
            domain={[0, 100]}
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
              if (name === "revenue") return [formatCurrency(value), "Revenue"];
              return [`${value.toFixed(1)}%`, "Cumulative %"];
            }}
            labelFormatter={(_label: string, payload: any[]) => {
              return payload?.[0]?.payload?.fullName || _label;
            }}
          />
          <ReferenceLine
            yAxisId="cumulative"
            y={80}
            stroke="#EF4444"
            strokeDasharray="5 5"
            label={{ value: "80%", position: "right", fill: "#EF4444", fontSize: 10 }}
          />
          <Bar
            yAxisId="revenue"
            dataKey="revenue"
            radius={[4, 4, 0, 0]}
            fill="#4F46E5"
            shape={(props: any) => {
              const { x, y, width, height, payload } = props;
              return (
                <rect
                  x={x}
                  y={y}
                  width={width}
                  height={height}
                  rx={4}
                  fill={getBarColor(payload.class)}
                />
              );
            }}
          />
          <Line
            yAxisId="cumulative"
            dataKey="cumulative"
            type="monotone"
            stroke="#E91E63"
            strokeWidth={2}
            dot={{ r: 3, fill: "#E91E63" }}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
