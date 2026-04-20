"use client";

import { useMemo, useState } from "react";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useRevenueForecast } from "@/hooks/use-revenue-forecast";
import type { RevenueForecastPeriod } from "@/hooks/use-revenue-forecast";
import type { RevenueForecast } from "@/types/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { SkeletonEnhanced } from "@/components/ui/skeleton-enhanced";
import { cn } from "@/lib/utils";

export interface RevenueChartProps {
  /** Override the hook — useful for Storybook / tests. */
  data?: RevenueForecast;
  /** Initial period; defaults to 'month'. */
  period?: RevenueForecastPeriod;
  className?: string;
}

/**
 * Chart-row shape — a single date key that carries every overlay. Using
 * one merged series per date lets Recharts share the X-axis ticks
 * between the solid actual line and the dashed forecast line.
 */
interface ChartRow {
  date: string;
  actual?: number;
  forecast?: number;
  /** Lower band value (for the confidence band). */
  ciLow?: number;
  /** Band *height* from ciLow → ciHigh (Recharts' Area stacks it). */
  ciBand?: number;
}

const PERIOD_OPTIONS: RevenueForecastPeriod[] = [
  "day",
  "week",
  "month",
  "quarter",
  "ytd",
];

const PERIOD_LABEL: Record<RevenueForecastPeriod, string> = {
  day: "Day",
  week: "Week",
  month: "Month",
  quarter: "Quarter",
  ytd: "YTD",
};

function formatEgp(value: number): string {
  if (Math.abs(value) >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (Math.abs(value) >= 1_000) return `${Math.round(value / 1_000)}K`;
  return Math.round(value).toString();
}

function mergeSeries(data: RevenueForecast): ChartRow[] {
  const rows = new Map<string, ChartRow>();
  for (const p of data.actual) {
    rows.set(p.period, { date: p.period, actual: Number(p.value) });
  }
  for (const p of data.forecast) {
    const row: ChartRow = rows.get(p.date) ?? { date: p.date };
    row.forecast = Number(p.value);
    row.ciLow = Number(p.ci_low);
    row.ciBand = Number(p.ci_high) - Number(p.ci_low);
    rows.set(p.date, row);
  }
  return Array.from(rows.values()).sort((a, b) =>
    a.date.localeCompare(b.date),
  );
}

/**
 * Composite revenue chart for the new dashboard (#502 / #504).
 *
 * Overlays: actual (solid cyan + gradient fill), forecast (dashed
 * purple + confidence band via invisible baseline + stacked band
 * Area), target (horizontal dashed reference line), today (vertical
 * reference line). Single call to ``/analytics/revenue-forecast`` —
 * no hook orchestration.
 */
export function RevenueChart({
  data,
  period = "month",
  className,
}: RevenueChartProps) {
  const [selected, setSelected] = useState<RevenueForecastPeriod>(period);
  const hookResult = useRevenueForecast(selected);

  const resolved = data !== undefined ? data : hookResult.data;
  const isLoading = data === undefined && hookResult.isLoading;

  const rows = useMemo(
    () => (resolved ? mergeSeries(resolved) : []),
    [resolved],
  );

  return (
    <Card className={cn("flex flex-col", className)}>
      <CardHeader className="flex flex-row items-center justify-between gap-3 pb-3">
        <div className="flex-1">
          <CardTitle>Revenue</CardTitle>
          {resolved && (
            <div className="mt-1 flex items-baseline gap-3 text-sm">
              <span className="text-2xl font-semibold tabular-nums text-text-primary">
                EGP {formatEgp(Number(resolved.stats.this_period_egp))}
              </span>
              {resolved.stats.delta_pct != null && (
                <span
                  className={cn(
                    "text-xs font-medium tabular-nums",
                    resolved.stats.delta_pct >= 0
                      ? "text-cyan-300"
                      : "text-red-300",
                  )}
                >
                  {resolved.stats.delta_pct >= 0 ? "+" : ""}
                  {resolved.stats.delta_pct.toFixed(1)}%
                </span>
              )}
              {resolved.stats.confidence != null && (
                <span className="text-[11px] text-text-secondary">
                  · {resolved.stats.confidence}% confidence
                </span>
              )}
            </div>
          )}
        </div>
        {/* Only render the segmented control when the hook drives
            the period — an explicit ``data`` prop skips it. */}
        {data === undefined && (
          <div
            role="group"
            aria-label="Revenue period"
            className="flex shrink-0 items-center gap-1 rounded-lg border border-white/10 bg-white/[0.02] p-0.5 text-[11px]"
          >
            {PERIOD_OPTIONS.map((opt) => (
              <button
                key={opt}
                type="button"
                onClick={() => setSelected(opt)}
                aria-pressed={selected === opt}
                className={cn(
                  "rounded-md px-2 py-1 transition-colors",
                  selected === opt
                    ? "bg-cyan-400/20 text-cyan-200"
                    : "text-text-secondary hover:text-text-primary",
                )}
              >
                {PERIOD_LABEL[opt]}
              </button>
            ))}
          </div>
        )}
      </CardHeader>
      <CardContent className="p-4 pt-0">
        {isLoading && (
          <div role="status" aria-label="Loading revenue chart">
            <SkeletonEnhanced className="h-52" lines={3} />
          </div>
        )}
        {!isLoading && resolved && (
          <div
            className="h-52 w-full"
            role="img"
            aria-label="Revenue actual and forecast chart"
          >
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={rows} margin={{ top: 4, right: 8, bottom: 4, left: -16 }}>
                <defs>
                  <linearGradient id="revenueActualFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#00c7f2" stopOpacity={0.35} />
                    <stop offset="100%" stopColor="#00c7f2" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="rgba(255,255,255,0.04)"
                />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 10, fill: "rgba(255,255,255,0.45)" }}
                  tickFormatter={(v: string) => v.slice(5)}
                  axisLine={false}
                  tickLine={false}
                  minTickGap={20}
                />
                <YAxis
                  tick={{ fontSize: 10, fill: "rgba(255,255,255,0.45)" }}
                  tickFormatter={formatEgp}
                  axisLine={false}
                  tickLine={false}
                  width={40}
                />
                <Tooltip
                  cursor={{ stroke: "rgba(255,255,255,0.15)" }}
                  contentStyle={{
                    background: "rgba(12,14,20,0.92)",
                    border: "1px solid rgba(255,255,255,0.08)",
                    borderRadius: 8,
                    fontSize: 12,
                  }}
                  labelStyle={{ color: "rgba(255,255,255,0.9)" }}
                  formatter={(value: number) => [`EGP ${formatEgp(value)}`, ""]}
                />
                {/* Confidence band — transparent baseline + stacked band area. */}
                <Area
                  type="monotone"
                  dataKey="ciLow"
                  stackId="band"
                  stroke="transparent"
                  fill="transparent"
                  isAnimationActive={false}
                  connectNulls
                />
                <Area
                  type="monotone"
                  dataKey="ciBand"
                  stackId="band"
                  stroke="transparent"
                  fill="#a78bfa"
                  fillOpacity={0.18}
                  isAnimationActive={false}
                  connectNulls
                  name="Forecast band"
                />
                {/* Actual — solid cyan + gradient fill via Area. */}
                <Area
                  type="monotone"
                  dataKey="actual"
                  stroke="#00c7f2"
                  strokeWidth={2}
                  fill="url(#revenueActualFill)"
                  connectNulls={false}
                  isAnimationActive={false}
                  name="Actual"
                />
                {/* Forecast — dashed purple line. */}
                <Line
                  type="monotone"
                  dataKey="forecast"
                  stroke="#a78bfa"
                  strokeWidth={2}
                  strokeDasharray="4 4"
                  dot={false}
                  connectNulls
                  isAnimationActive={false}
                  name="Forecast"
                />
                {/* Target — horizontal dashed reference line. */}
                {resolved.target && (
                  <ReferenceLine
                    y={Number(resolved.target.value)}
                    stroke="#fbbf24"
                    strokeDasharray="6 4"
                    strokeWidth={1}
                    label={{
                      value: `Target · ${formatEgp(
                        Number(resolved.target.value),
                      )}`,
                      fill: "#fbbf24",
                      fontSize: 10,
                      position: "insideTopRight",
                    }}
                  />
                )}
                {/* Today — vertical reference line. */}
                <ReferenceLine
                  x={resolved.today}
                  stroke="rgba(255,255,255,0.35)"
                  strokeDasharray="3 3"
                  label={{
                    value: "Today",
                    fill: "rgba(255,255,255,0.55)",
                    fontSize: 10,
                    position: "top",
                  }}
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        )}
        {!isLoading && resolved && resolved.target && (
          <p className="mt-2 text-[11px] text-text-secondary">
            Target status:{" "}
            <span
              className={cn(
                "font-medium",
                resolved.target.status === "ahead" && "text-cyan-300",
                resolved.target.status === "on_track" && "text-text-primary",
                resolved.target.status === "behind" && "text-red-300",
                resolved.target.status === "unknown" && "text-text-secondary",
              )}
            >
              {resolved.target.status.replace("_", " ")}
            </span>
          </p>
        )}
      </CardContent>
    </Card>
  );
}
