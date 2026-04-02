"use client";

import { useSegmentSummary } from "@/hooks/use-segments";
import { formatNumber } from "@/lib/formatters";
import { LoadingCard } from "@/components/loading-card";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { useChartTheme } from "@/hooks/use-chart-theme";

const SEGMENT_ORDER = [
  "Champions",
  "Loyal Customers",
  "Potential Loyalist",
  "New Customers",
  "Promising",
  "Need Attention",
  "About To Sleep",
  "At Risk",
  "Cant Lose Them",
  "Hibernating",
  "Lost",
];

const COLORS: Record<string, string> = {
  Champions: "#00BFA5",
  "Loyal Customers": "#2196F3",
  "Potential Loyalist": "#8BC34A",
  "New Customers": "#FFB300",
  "Promising": "#FF9800",
  "Need Attention": "#FF5722",
  "About To Sleep": "#E91E63",
  "At Risk": "#F44336",
  "Cant Lose Them": "#9C27B0",
  Hibernating: "#607D8B",
  Lost: "#9E9E9E",
};

export function SegmentFunnel() {
  const { data, isLoading } = useSegmentSummary();
  const theme = useChartTheme();

  if (isLoading) return <LoadingCard className="h-64" />;
  if (!data || data.length === 0) return null;

  // Sort by SEGMENT_ORDER, then by count
  const sorted = [...data].sort((a, b) => {
    const ai = SEGMENT_ORDER.indexOf(a.segment);
    const bi = SEGMENT_ORDER.indexOf(b.segment);
    if (ai === -1 && bi === -1) return b.count - a.count;
    if (ai === -1) return 1;
    if (bi === -1) return -1;
    return ai - bi;
  });

  const chartData = sorted.map((s) => ({
    name: s.segment.length > 12 ? s.segment.substring(0, 12) + "..." : s.segment,
    fullName: s.segment,
    count: s.count,
    revenue: s.total_revenue,
    avg: s.avg_monetary,
  }));

  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <h3 className="text-sm font-semibold text-text-primary mb-3">Customer Value Distribution</h3>

      <ResponsiveContainer width="100%" height={250}>
        <BarChart data={chartData} layout="vertical" margin={{ left: 80, right: 10 }}>
          <XAxis
            type="number"
            tick={{ fontSize: 10, fill: theme.tickFill }}
            tickFormatter={(v: number) => formatNumber(v)}
          />
          <YAxis
            type="category"
            dataKey="name"
            tick={{ fontSize: 10, fill: theme.tickFill }}
            width={80}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: theme.tooltipBg,
              border: `1px solid ${theme.gridStroke}`,
              borderRadius: "8px",
              fontSize: "12px",
            }}
            formatter={(value: number) => [formatNumber(value), "Customers"]}
            labelFormatter={(label: string, payload: Array<{ payload?: { fullName?: string } }>) =>
              payload?.[0]?.payload?.fullName || label
            }
          />
          <Bar dataKey="count" radius={[0, 4, 4, 0]}>
            {chartData.map((entry, i) => (
              <Cell key={i} fill={COLORS[sorted[i]?.segment] || "#64748b"} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
