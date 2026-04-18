"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
  ResponsiveContainer,
} from "recharts";
import { ChartCard } from "@/components/shared/chart-card";
import { useChartTheme } from "@/hooks/use-chart-theme";
import { useDaysOfStock } from "@/hooks/use-days-of-stock";
import { LoadingCard } from "@/components/loading-card";
import { EmptyState } from "@/components/empty-state";
import { UploadDataAction } from "@/components/shared/empty-state-actions";
import { truncate } from "@/lib/formatters";

function riskColor(days: number | null): string {
  if (days === null || days <= 0) return "#EF4444"; // red — stockout
  if (days <= 7) return "#F97316";  // orange — critical
  if (days <= 30) return "#EAB308"; // yellow — at risk
  return "#22C55E"; // green — ok
}

export function DaysOfStockChart() {
  const { data, isLoading } = useDaysOfStock();
  const theme = useChartTheme();

  if (isLoading) return <LoadingCard className="h-80" />;
  if (!data.length) return <EmptyState title="No stock days data" action={<UploadDataAction />} />;

  const sorted = [...data]
    .sort((a, b) => (a.days_of_stock ?? -1) - (b.days_of_stock ?? -1))
    .slice(0, 20)
    .map((d) => ({
      name: truncate(d.drug_name, 20),
      days: d.days_of_stock ?? 0,
      raw: d,
    }));

  return (
    <ChartCard
      title="Days of Stock"
      subtitle="Most critical first"
    >
      <ResponsiveContainer width="100%" height={320}>
        <BarChart
          layout="vertical"
          data={sorted}
          margin={{ top: 5, right: 30, left: 10, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke={theme.gridStroke} horizontal={false} />
          <XAxis
            type="number"
            tick={{ fontSize: 10, fill: theme.tickFill }}
            tickFormatter={(v: number) => `${v}d`}
          />
          <YAxis
            type="category"
            dataKey="name"
            width={140}
            tick={{ fontSize: 10, fill: theme.tickFill }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: theme.tooltipBg,
              border: `1px solid ${theme.tooltipBorder}`,
              borderRadius: "8px",
              fontSize: "12px",
              color: theme.tooltipColor,
            }}
            formatter={(value: number) => [`${value} days`, "Days of Stock"]}
          />
          <Bar dataKey="days" radius={[0, 4, 4, 0]} maxBarSize={16}>
            {sorted.map((entry) => (
              <Cell key={entry.name} fill={riskColor(entry.raw.days_of_stock)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}
