"use client";

import { useMemo } from "react";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { EmptyState } from "@/components/empty-state";
import { ErrorRetry } from "@/components/error-retry";
import { LoadingCard } from "@/components/loading-card";
import { ChartCard } from "@/components/shared/chart-card";
import { useChartTheme } from "@/hooks/use-chart-theme";
import { useProductMovements } from "@/hooks/use-product-movements";
import { useProductStock } from "@/hooks/use-product-stock";
import { formatNumber } from "@/lib/formatters";
import type { FilterParams } from "@/types/filters";

const OUTBOUND_TYPES = ["dispense", "issue", "wastage", "write_off", "transfer_out", "adjustment_out"];

function movementSign(type: string) {
  const normalized = type.toLowerCase();
  return OUTBOUND_TYPES.some((value) => normalized.includes(value)) ? -1 : 1;
}

interface StockHistoryChartProps {
  drugCode: string;
  filters?: FilterParams;
}

export function StockHistoryChart({ drugCode, filters }: StockHistoryChartProps) {
  const movements = useProductMovements(drugCode, filters);
  const stock = useProductStock(drugCode, filters);
  const chartTheme = useChartTheme();

  const history = useMemo(() => {
    const currentTotal = (stock.data ?? []).reduce((sum, item) => sum + item.current_quantity, 0);
    const grouped = new Map<string, number>();

    for (const movement of movements.data ?? []) {
      const current = grouped.get(movement.movement_date) ?? 0;
      grouped.set(movement.movement_date, current + movementSign(movement.movement_type) * Math.abs(movement.quantity));
    }

    const ordered = Array.from(grouped.entries())
      .sort((left, right) => left[0].localeCompare(right[0]))
      .map(([movementDate, netChange]) => ({ movement_date: movementDate, net_change: netChange }));

    if (!ordered.length && currentTotal > 0) {
      return [{
        movement_date: new Date().toISOString().slice(0, 10),
        stock_level: currentTotal,
        net_change: 0,
      }];
    }

    const reverseBalances: Array<{ movement_date: string; stock_level: number; net_change: number }> = [];
    let runningBalance = currentTotal;

    for (let index = ordered.length - 1; index >= 0; index -= 1) {
      const point = ordered[index];
      reverseBalances.push({
        movement_date: point.movement_date,
        stock_level: runningBalance,
        net_change: point.net_change,
      });
      runningBalance -= point.net_change;
    }

    return reverseBalances.reverse();
  }, [movements.data, stock.data]);

  if (movements.isLoading || stock.isLoading) return <LoadingCard lines={5} className="h-[26rem]" />;
  if (movements.error || stock.error) {
    return (
      <ErrorRetry
        title="Failed to load stock history"
        description="Historical stock levels could not be calculated."
        onRetry={() => {
          void movements.mutate();
          void stock.mutate();
        }}
      />
    );
  }
  if (!history.length) {
    return (
      <EmptyState
        title="No stock history available"
        description="Stock history will appear here after inventory movements are recorded."
      />
    );
  }

  return (
    <ChartCard
      title="Stock History"
      subtitle={`${formatNumber(stock.data?.reduce((sum, item) => sum + item.current_quantity, 0) ?? 0)} units on hand`}
    >
      <ResponsiveContainer width="100%" height={300}>
        <AreaChart data={history} margin={{ top: 10, right: 16, left: 0, bottom: 0 }}>
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
            formatter={(value: number, name: string) => [formatNumber(value), name === "stock_level" ? "Estimated stock" : "Net change"]}
          />
          <Area type="monotone" dataKey="stock_level" stroke={chartTheme.chartBlue} fill={chartTheme.chartBlue} fillOpacity={0.18} />
        </AreaChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}
