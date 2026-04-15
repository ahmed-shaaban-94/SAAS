"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { ChartCard } from "@/components/shared/chart-card";
import { useChartTheme } from "@/hooks/use-chart-theme";
import { useSupplierPerformance } from "@/hooks/use-supplier-performance";
import { LoadingCard } from "@/components/loading-card";
import { EmptyState } from "@/components/empty-state";
import { truncate } from "@/lib/formatters";

export function SupplierPerformanceChart() {
  const { data, isLoading } = useSupplierPerformance();
  const theme = useChartTheme();

  if (isLoading) return <LoadingCard className="h-80" />;
  if (!data.length) return <EmptyState title="No supplier performance data" />;

  const chartData = data.map((s) => ({
    name: truncate(s.supplier_name, 18),
    leadDays: s.avg_lead_days ?? 0,
    fillRate: s.fill_rate != null ? +(s.fill_rate * 100).toFixed(1) : 0,
  }));

  return (
    <ChartCard title="Supplier Performance" subtitle={`${data.length} suppliers`}>
      <ResponsiveContainer width="100%" height={280}>
        <BarChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 40 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={theme.gridStroke} />
          <XAxis
            dataKey="name"
            tick={{ fontSize: 10, fill: theme.tickFill }}
            angle={-30}
            textAnchor="end"
            interval={0}
          />
          <YAxis
            yAxisId="lead"
            tick={{ fontSize: 10, fill: theme.tickFill }}
            tickFormatter={(v: number) => `${v}d`}
          />
          <YAxis
            yAxisId="fill"
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
              if (name === "leadDays") return [`${value} days`, "Avg Lead Time"];
              return [`${value}%`, "Fill Rate"];
            }}
          />
          <Legend
            wrapperStyle={{ fontSize: 11, paddingTop: 8, color: theme.tickFill }}
          />
          <Bar
            yAxisId="lead"
            dataKey="leadDays"
            name="leadDays"
            fill={theme.chartBlue}
            radius={[4, 4, 0, 0]}
            maxBarSize={32}
          />
          <Bar
            yAxisId="fill"
            dataKey="fillRate"
            name="fillRate"
            fill={theme.chartAmber}
            radius={[4, 4, 0, 0]}
            maxBarSize={32}
          />
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}
