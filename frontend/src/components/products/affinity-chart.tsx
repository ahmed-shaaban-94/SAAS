"use client";

import { useProductAffinity } from "@/hooks/use-product-affinity";
import { LoadingCard } from "@/components/loading-card";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
} from "recharts";
import { useChartTheme } from "@/hooks/use-chart-theme";

interface Props {
  productKey: number;
}

export function AffinityChart({ productKey }: Props) {
  const { data, isLoading } = useProductAffinity(productKey);
  const theme = useChartTheme();

  if (isLoading) return <LoadingCard className="h-48" />;
  if (data.length === 0) return null;

  const chartData = data.slice(0, 8).map((p) => ({
    name: p.related_name.length > 20 ? p.related_name.slice(0, 20) + "..." : p.related_name,
    count: p.co_occurrence_count,
    confidence: p.confidence,
  }));

  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <h3 className="text-sm font-semibold text-text-primary mb-3">
        Frequently Bought Together
      </h3>
      <ResponsiveContainer width="100%" height={chartData.length * 36 + 20}>
        <BarChart data={chartData} layout="vertical" margin={{ left: 10, right: 20, top: 0, bottom: 0 }}>
          <XAxis type="number" tick={{ fontSize: 10, fill: theme.tickFill }} />
          <YAxis type="category" dataKey="name" width={140} tick={{ fontSize: 10, fill: theme.tickFill }} />
          <Tooltip
            contentStyle={{ backgroundColor: theme.tooltipBg, border: `1px solid ${theme.gridStroke}`, borderRadius: "8px", fontSize: "12px" }}
            formatter={(value: number) => [value, "Co-purchases"]}
          />
          <Bar dataKey="count" fill="#4F46E5" radius={[0, 4, 4, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
