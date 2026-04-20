"use client";

import { Cell, Pie, PieChart, ResponsiveContainer } from "recharts";
import { useChannels } from "@/hooks/use-channels";
import type { ChannelShare, ChannelsBreakdown } from "@/types/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { SkeletonEnhanced } from "@/components/ui/skeleton-enhanced";
import { cn } from "@/lib/utils";

export interface ChannelDonutProps {
  /** Override the hook — useful for Storybook / tests. */
  breakdown?: ChannelsBreakdown;
  className?: string;
}

/**
 * Design-palette colours per channel. Keeping this here (rather than in
 * ``globals.css``) so the legend swatches and pie arcs stay in sync
 * without a second lookup.
 */
const CHANNEL_COLORS: Record<ChannelShare["channel"], string> = {
  retail: "#00c7f2", // cyan accent
  wholesale: "#a78bfa", // violet
  institution: "#fbbf24", // amber
  online: "#34d399", // emerald
};

function formatEgp(value: number): string {
  if (value >= 1_000_000) return `EGP ${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `EGP ${Math.round(value / 1_000)}K`;
  return `EGP ${Math.round(value)}`;
}

/**
 * Sales-channel revenue donut for the new dashboard (#502 / #505).
 *
 * Always renders four segments in fixed order; segments with
 * ``source === "unavailable"`` show a muted tone in the legend so
 * operators can see the gap without the donut misleading.
 */
export function ChannelDonut({ breakdown, className }: ChannelDonutProps) {
  const hookResult = useChannels();
  const data = breakdown !== undefined ? breakdown : hookResult.data;
  const isLoading = breakdown === undefined && hookResult.isLoading;

  // Recharts ignores zero-value slices for the arc — prefer a tiny
  // epsilon so the legend still shows all four labels. We still render
  // the number from the source array (zero) in the legend text.
  const chartData = data?.items.map((item) => ({
    name: item.label,
    value: Math.max(Number(item.value_egp), 0.0001),
    channel: item.channel,
  })) ?? [];

  const hasAnyValue =
    data?.items.some((i) => Number(i.value_egp) > 0) ?? false;

  return (
    <Card className={cn("flex flex-col", className)}>
      <CardHeader className="pb-3">
        <CardTitle>Sales Channels</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4 p-4 pt-0 sm:flex-row sm:items-center">
        {isLoading && (
          <div
            className="flex-1"
            role="status"
            aria-label="Loading sales channels"
          >
            <SkeletonEnhanced className="h-24" lines={2} />
          </div>
        )}
        {!isLoading && data && (
          <>
            <div
              className="relative h-40 w-40 shrink-0"
              role="img"
              aria-label="Sales channel distribution donut"
            >
              {hasAnyValue ? (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={chartData}
                      innerRadius="58%"
                      outerRadius="88%"
                      paddingAngle={2}
                      startAngle={90}
                      endAngle={-270}
                      dataKey="value"
                      isAnimationActive={false}
                    >
                      {chartData.map((entry) => (
                        <Cell
                          key={entry.channel}
                          fill={CHANNEL_COLORS[entry.channel as ChannelShare["channel"]] ?? "#9ca3af"}
                          stroke="transparent"
                        />
                      ))}
                    </Pie>
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <div className="absolute inset-0 flex items-center justify-center rounded-full border border-dashed border-white/10 text-[11px] text-text-secondary">
                  No revenue yet
                </div>
              )}
              <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-[10px] uppercase tracking-wider text-text-secondary">
                  Total
                </span>
                <span className="text-lg font-semibold tabular-nums text-text-primary">
                  {formatEgp(Number(data.total_egp))}
                </span>
              </div>
            </div>

            <ul className="flex flex-1 flex-col gap-2 text-xs">
              {data.items.map((item) => {
                const colour =
                  CHANNEL_COLORS[item.channel] ?? "#9ca3af";
                const isUnavailable = item.source === "unavailable";
                return (
                  <li
                    key={item.channel}
                    className={cn(
                      "flex items-center justify-between gap-3",
                      isUnavailable && "opacity-60",
                    )}
                  >
                    <span className="flex items-center gap-2">
                      <span
                        aria-hidden="true"
                        className="h-2.5 w-2.5 shrink-0 rounded-sm"
                        style={{ backgroundColor: colour }}
                      />
                      <span className="text-text-primary">{item.label}</span>
                      {isUnavailable && (
                        <span className="rounded-full bg-white/5 px-1.5 py-0.5 text-[9px] uppercase tracking-wider text-text-secondary">
                          no data
                        </span>
                      )}
                    </span>
                    <span className="flex items-baseline gap-2 tabular-nums">
                      <span className="text-text-secondary">
                        {Number(item.pct_of_total).toFixed(1)}%
                      </span>
                      <span className="w-16 text-right text-text-primary">
                        {formatEgp(Number(item.value_egp))}
                      </span>
                    </span>
                  </li>
                );
              })}
            </ul>
          </>
        )}
        {!isLoading && data && data.data_coverage === "partial" && (
          <p className="text-[11px] text-text-secondary sm:absolute sm:bottom-2 sm:right-4">
            Partial data — wholesale & online pending ingestion.
          </p>
        )}
      </CardContent>
    </Card>
  );
}
