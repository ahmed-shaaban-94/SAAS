"use client";

import { useMemo } from "react";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useFilters } from "@/contexts/filter-context";
import { EmptyState } from "@/components/empty-state";
import { ErrorRetry } from "@/components/error-retry";
import { LoadingCard } from "@/components/loading-card";
import { ChartCard } from "@/components/shared/chart-card";
import { useChartTheme } from "@/hooks/use-chart-theme";
import { useStockMovements } from "@/hooks/use-stock-movements";
import { formatNumber } from "@/lib/formatters";

const INBOUND_TYPES = ["receipt", "receive", "transfer_in", "adjustment_in", "restock", "return"];
const OUTBOUND_TYPES = ["dispense", "issue", "wastage", "write_off", "transfer_out", "adjustment_out"];

function movementSign(type: string) {
  const normalized = type.toLowerCase();
  if (INBOUND_TYPES.some((value) => normalized.includes(value))) return 1;
  if (OUTBOUND_TYPES.some((value) => normalized.includes(value))) return -1;
  return 1;
}

export function StockMovementChart() {
  const { filters } = useFilters();
  const { data, error, isLoading, mutate } = useStockMovements(filters);
  const chartTheme = useChartTheme();

  const chartData = useMemo(() => {
    const grouped = new Map<string, { movement_date: string; inflow: number; outflow: number; net: number }>();

    for (const movement of data ?? []) {
      const quantity = Math.abs(movement.quantity);
      const sign = movementSign(movement.movement_type);
      const current = grouped.get(movement.movement_date) ?? {
        movement_date: movement.movement_date,
        inflow: 0,
        outflow: 0,
        net: 0,
      };

      if (sign >= 0) current.inflow += quantity;
      else current.outflow += quantity;
      current.net += sign * quantity;
      grouped.set(movement.movement_date, current);
    }

    return Array.from(grouped.values()).sort((left, right) => left.movement_date.localeCompare(right.movement_date));
  }, [data]);

  if (isLoading) return <LoadingCard lines={4} className="h-[24rem]" />;
  if (error) {
    return (
      <ErrorRetry
        title="Failed to load stock movements"
        description="Movement trends could not be loaded."
        onRetry={() => mutate()}
      />
    );
  }
  if (!chartData.length) {
    return <EmptyState title="No stock movements" description="Movement activity will appear here once records are available." />;
  }

  return (
    <ChartCard
      title="Stock Movements"
      subtitle={`${formatNumber(data?.length ?? 0)} movement events`}
    >
      <ResponsiveContainer width="100%" height={300}>
        <AreaChart data={chartData} margin={{ top: 10, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid stroke={chartTheme.gridStroke} />
          <XAxis
            dataKey="movement_date"
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
            formatter={(value: number, name: string) => [formatNumber(value), name === "inflow" ? "Inbound" : name === "outflow" ? "Outbound" : "Net change"]}
          />
          <Area type="monotone" dataKey="inflow" stroke={chartTheme.chartBlue} fill={chartTheme.chartBlue} fillOpacity={0.18} />
          <Area type="monotone" dataKey="outflow" stroke={chartTheme.chartAmber} fill={chartTheme.chartAmber} fillOpacity={0.16} />
        </AreaChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}
