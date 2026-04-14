"use client";

import { useMemo } from "react";
import useSWR from "swr";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useFilters } from "@/contexts/filter-context";
import { EmptyState } from "@/components/empty-state";
import { ErrorRetry } from "@/components/error-retry";
import { LoadingCard } from "@/components/loading-card";
import { ChartCard } from "@/components/shared/chart-card";
import { fetchAPI, swrKey } from "@/lib/api-client";
import { useChartTheme } from "@/hooks/use-chart-theme";
import { formatNumber } from "@/lib/formatters";
import type { ExpiryAlert } from "@/types/expiry";

export function WriteOffSummaryChart() {
  const { filters } = useFilters();
  const key = swrKey("/api/v1/expiry/expired", filters);
  const { data, error, isLoading, mutate } = useSWR(key, () =>
    fetchAPI<ExpiryAlert[]>("/api/v1/expiry/expired", filters),
  );
  const chartTheme = useChartTheme();

  const chartData = useMemo(() => {
    const grouped = new Map<string, { period: string; quantity: number; batches: number }>();

    for (const item of data ?? []) {
      const period = item.expiry_date.slice(0, 7);
      const current = grouped.get(period) ?? { period, quantity: 0, batches: 0 };
      current.quantity += item.current_quantity;
      current.batches += 1;
      grouped.set(period, current);
    }

    return Array.from(grouped.values()).sort((left, right) => left.period.localeCompare(right.period));
  }, [data]);

  if (isLoading) return <LoadingCard lines={4} className="h-[24rem]" />;
  if (error) {
    return (
      <ErrorRetry
        title="Failed to load write-off summary"
        description="Expired quantity summary could not be loaded."
        onRetry={() => mutate()}
      />
    );
  }
  if (!chartData.length) {
    return (
      <EmptyState
        title="No write-off exposure"
        description="Expired quantity trends will appear here when stock expires."
      />
    );
  }

  return (
    <ChartCard
      title="Write-Off Exposure"
      subtitle={`${formatNumber(chartData.reduce((sum, item) => sum + item.quantity, 0))} expired units`}
    >
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={chartData} margin={{ top: 10, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid stroke={chartTheme.gridStroke} />
          <XAxis
            dataKey="period"
            tick={{ fill: chartTheme.tickFill, fontSize: chartTheme.tickFontSize }}
            tickLine={false}
            axisLine={{ stroke: chartTheme.axisStroke }}
          />
          <YAxis
            tick={{ fill: chartTheme.tickFill, fontSize: chartTheme.tickFontSize }}
            tickFormatter={(value: number) => formatNumber(value)}
            tickLine={false}
            axisLine={{ stroke: chartTheme.axisStroke }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: chartTheme.tooltipBg,
              border: `1px solid ${chartTheme.tooltipBorder}`,
              color: chartTheme.tooltipColor,
              borderRadius: "1rem",
            }}
            formatter={(value: number, name: string) => [formatNumber(value), name === "quantity" ? "Expired quantity" : "Expired batches"]}
          />
          <Bar dataKey="quantity" fill={chartTheme.chartAmber} radius={[8, 8, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}
