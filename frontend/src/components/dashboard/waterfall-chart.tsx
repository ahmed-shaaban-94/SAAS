"use client";

import { memo, useState, useMemo } from "react";
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
import { cn } from "@/lib/utils";
import type { ApiGet } from "@/lib/api-types";

type WaterfallAnalysis = ApiGet<"/api/v1/analytics/why-changed">;

const DIM_TABS = [
  { key: "product", label: "Products" },
  { key: "customer", label: "Customers" },
  { key: "staff", label: "Staff" },
  { key: "site", label: "Sites" },
] as const;

type DimensionKey = (typeof DIM_TABS)[number]["key"];

export interface WaterfallChartProps {
  data?: WaterfallAnalysis;
  periodLabel?: string;
}

export const WaterfallChart = memo(function WaterfallChart({ data, periodLabel }: WaterfallChartProps) {
  const theme = useChartTheme();
  const [activeDim, setActiveDim] = useState<DimensionKey>("product");

  // Group drivers by dimension
  const driversByDim = useMemo(() => {
    if (!data) return {};
    const grouped: Record<string, typeof data.drivers> = {};
    for (const d of data.drivers) {
      (grouped[d.dimension] ??= []).push(d);
    }
    return grouped;
  }, [data]);

  // Only show tabs that have data
  const availableTabs = useMemo(
    () => DIM_TABS.filter((t) => (driversByDim[t.key]?.length ?? 0) > 0),
    [driversByDim],
  );

  // If selected tab has no data, fall back to first available
  const effectiveDim =
    (driversByDim[activeDim]?.length ?? 0) > 0
      ? activeDim
      : availableTabs[0]?.key ?? "product";

  const chartData = useMemo(
    () =>
      (driversByDim[effectiveDim] ?? []).slice(0, 10).map((d) => {
        const rawName = d.entity_name;
        return {
          name: rawName.length > 22 ? rawName.slice(0, 20) + "..." : rawName,
          fullName: rawName,
          impact: d.impact,
          impactPct: d.impact_pct,
          dimension: d.dimension,
          direction: d.direction,
        };
      }),
    [driversByDim, effectiveDim],
  );

  // Compute explained percentage (for...of avoids adding uncovered arrow functions)
  let explainedPct: number | null = null;
  if (data && data.total_change !== 0) {
    let explained = 0;
    for (const d of data.drivers) {
      explained += Math.abs(d.impact);
    }
    const totalAbs = Math.abs(data.total_change);
    if (totalAbs > 0) {
      explainedPct = Math.round((explained / totalAbs) * 100);
    }
  }

  // Check if any driver has extreme impact_pct
  let hasExtremeImpact = false;
  if (data) {
    for (const d of data.drivers) {
      if (Math.abs(d.impact_pct) > 100) {
        hasExtremeImpact = true;
        break;
      }
    }
  }

  if (!data || !data.drivers.length) {
    return (
      <div className="rounded-lg border border-border bg-card p-6">
        <h3 className="text-lg font-semibold mb-2">Revenue Change Drivers</h3>
        <p className="text-text-secondary text-sm">
          No significant drivers found for this period.
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-border bg-card p-6">
      <div className="flex flex-col gap-3 mb-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h3 className="text-lg font-semibold">Revenue Change Drivers</h3>
          <p className="text-sm text-text-secondary">
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
          {periodLabel && (
            <p className="text-xs text-text-secondary mt-0.5">
              Comparing: {periodLabel} vs equivalent previous period
            </p>
          )}
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center rounded-lg border border-border bg-page/50 p-0.5">
            {availableTabs.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveDim(tab.key)}
                className={cn(
                  "rounded-md px-3 py-1 text-xs font-medium transition-all",
                  effectiveDim === tab.key
                    ? "bg-accent/20 text-accent shadow-sm"
                    : "text-text-secondary hover:text-accent hover:bg-accent/10",
                )}
              >
                {tab.label}
                <span className="ml-1 opacity-60">
                  ({driversByDim[tab.key]?.length ?? 0})
                </span>
              </button>
            ))}
          </div>
          <div className="flex gap-2 text-xs">
            <span className="flex items-center gap-1">
              <span className="w-2.5 h-2.5 rounded bg-emerald-500 inline-block" /> Up
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2.5 h-2.5 rounded bg-red-500 inline-block" /> Down
            </span>
          </div>
        </div>
      </div>

      <ResponsiveContainer width="100%" height={Math.max(280, chartData.length * 36)}>
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
            width={180}
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
            formatter={(value: number, _name: string, props: { payload?: { impactPct: number } }) => [
              `${formatCurrency(value)} (${formatPercent(props.payload?.impactPct ?? 0)})`,
              "Impact",
            ]}
            labelFormatter={(label) => {
              const item = chartData.find((d) => d.name === label);
              return item?.fullName || label;
            }}
          />
          <ReferenceLine x={0} stroke={theme.tickFill} strokeWidth={1} />
          <Bar dataKey="impact" radius={[0, 4, 4, 0]} animationDuration={600}>
            {chartData.map((entry, index) => (
              <Cell
                key={index}
                fill={entry.direction === "positive" ? "#10b981" : "#ef4444"}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      {/* Footer: explained coverage + extreme % note */}
      <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-text-secondary">
        {explainedPct !== null && explainedPct < 95 && (
          <span>
            Top drivers explain ~{explainedPct}% of the total change
          </span>
        )}
        {hasExtremeImpact && (
          <span title="When gains and losses partially offset each other, individual driver contributions can exceed 100% of the net change.">
            * Some drivers exceed 100% due to offsetting effects
          </span>
        )}
      </div>
    </div>
  );
});
