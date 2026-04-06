"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  ReferenceLine,
} from "recharts";
import { useChartTheme } from "@/hooks/use-chart-theme";
import { formatCurrency, formatPercent } from "@/lib/formatters";
import type { WaterfallAnalysis } from "@/types/api";

interface WaterfallChartProps {
  data: WaterfallAnalysis;
}

export function WaterfallChart({ data }: WaterfallChartProps) {
  const theme = useChartTheme();

  if (!data.drivers.length) {
    return (
      <div className="rounded-lg border border-border bg-card p-6">
        <h3 className="text-lg font-semibold mb-2">Revenue Change Drivers</h3>
        <p className="text-muted-foreground text-sm">
          No significant drivers found for this period.
        </p>
      </div>
    );
  }

  // Dimension labels for context (so users know if a row is a product, customer, staff, or site)
  const DIM_LABELS: Record<string, string> = {
    product: "Product",
    customer: "Customer",
    staff: "Staff",
    site: "Site",
  };

  const chartData = data.drivers.slice(0, 10).map((d) => {
    const tag = DIM_LABELS[d.dimension] || d.dimension;
    const rawName = d.entity_name;
    const label = `[${tag}] ${rawName.length > 16 ? rawName.slice(0, 14) + "..." : rawName}`;
    return {
      name: label,
      fullName: `${rawName} (${tag})`,
      impact: d.impact,
      impactPct: d.impact_pct,
      dimension: d.dimension,
      direction: d.direction,
    };
  });

  return (
    <div className="rounded-lg border border-border bg-card p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold">Revenue Change Drivers</h3>
          <p className="text-sm text-muted-foreground">
            Total change: {formatCurrency(data.total_change)}
            {data.total_change_pct != null && (
              <span
                className={
                  data.total_change >= 0 ? "text-emerald-500 ml-2" : "text-red-500 ml-2"
                }
              >
                ({formatPercent(data.total_change_pct)})
              </span>
            )}
          </p>
        </div>
        <div className="flex flex-wrap gap-3 text-xs">
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 rounded bg-emerald-500 inline-block" /> Positive
          </span>
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 rounded bg-red-500 inline-block" /> Negative
          </span>
          <span className="text-text-secondary ml-2">
            Labels show [Product], [Customer], [Staff], or [Site]
          </span>
        </div>
      </div>

      <ResponsiveContainer width="100%" height={Math.max(300, chartData.length * 40)}>
        <BarChart data={chartData} layout="vertical" margin={{ left: 20, right: 30 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={theme.gridStroke} />
          <XAxis
            type="number"
            tickFormatter={(v: number) => formatCurrency(v)}
            stroke={theme.tickFill}
            fontSize={11}
          />
          <YAxis
            type="category"
            dataKey="name"
            width={200}
            stroke={theme.tickFill}
            fontSize={11}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: theme.tooltipBg,
              border: "1px solid " + theme.gridStroke,
              borderRadius: 8,
              fontSize: 12,
            }}
            formatter={(value: number, _name: string, props: any) => [
              `${formatCurrency(value)} (${formatPercent(props.payload.impactPct)})`,
              props.payload.dimension,
            ]}
            labelFormatter={(label) => {
              const item = chartData.find((d) => d.name === label);
              return item?.fullName || label;
            }}
          />
          <ReferenceLine x={0} stroke={theme.tickFill} strokeWidth={1} />
          <Bar dataKey="impact" radius={[0, 4, 4, 0]}>
            {chartData.map((entry, index) => (
              <Cell
                key={index}
                fill={entry.direction === "positive" ? "#10b981" : "#ef4444"}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
