"use client";

import { useMemo } from "react";
import { useExpiryCalendar } from "@/hooks/use-expiry-calendar";
import type { ExpiryCalendarDay } from "@/types/expiry";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { SkeletonEnhanced } from "@/components/ui/skeleton-enhanced";
import { cn } from "@/lib/utils";

export interface ExpiryHeatmapProps {
  /** Override the hook — useful for Storybook / tests. */
  days?: ExpiryCalendarDay[];
  /** Number of calendar days to render (default 98 = 14 weeks × 7). */
  horizon?: number;
  /** Anchor date for the grid (defaults to today — first cell). */
  today?: Date;
  className?: string;
}

/**
 * GitHub-style calendar heatmap for expiry load (#502).
 *
 * 14 columns × 7 rows = 98 days of upcoming expiries. Bucket colour
 * scales with ``batch_count`` when ``alert_level === "safe"`` and
 * escalates to the level's fixed tone for anything flagged.
 */
const LEVEL_TONE: Record<string, string> = {
  expired: "bg-red-500/80",
  critical: "bg-red-500/60",
  warning: "bg-amber-500/55",
  caution: "bg-amber-500/30",
  safe: "bg-cyan-500/25",
};

function toISODate(d: Date): string {
  return d.toISOString().slice(0, 10);
}

function buildGrid(
  days: ExpiryCalendarDay[],
  horizon: number,
  anchor: Date,
): { date: string; day: ExpiryCalendarDay | null }[] {
  const byDate = new Map<string, ExpiryCalendarDay>();
  for (const d of days) {
    byDate.set(d.date.slice(0, 10), d);
  }
  const cells: { date: string; day: ExpiryCalendarDay | null }[] = [];
  for (let i = 0; i < horizon; i += 1) {
    const d = new Date(anchor);
    d.setDate(d.getDate() + i);
    const key = toISODate(d);
    cells.push({ date: key, day: byDate.get(key) ?? null });
  }
  return cells;
}

function cellTone(day: ExpiryCalendarDay | null): string {
  if (!day) return "bg-white/[0.025]";
  const level = day.alert_level.toLowerCase();
  return LEVEL_TONE[level] ?? LEVEL_TONE.safe;
}

export function ExpiryHeatmap({
  days,
  horizon = 98,
  today,
  className,
}: ExpiryHeatmapProps) {
  const hookResult = useExpiryCalendar();
  const data = days !== undefined ? days : hookResult.data;
  const isLoading = days === undefined && hookResult.isLoading;

  const anchor = useMemo(() => today ?? new Date(), [today]);
  const cells = useMemo(
    () => (data ? buildGrid(data, horizon, anchor) : []),
    [data, horizon, anchor],
  );

  // 14 columns × 7 rows — CSS grid handles placement.
  const COLS = Math.ceil(horizon / 7);

  return (
    <Card className={cn("flex flex-col", className)}>
      <CardHeader className="pb-3">
        <CardTitle>Expiry Heatmap</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 p-4 pt-0">
        {isLoading && (
          <div role="status" aria-label="Loading expiry heatmap">
            <SkeletonEnhanced className="h-20" lines={3} />
          </div>
        )}
        {!isLoading && data && data.length === 0 && (
          <p className="py-8 text-center text-sm text-text-secondary">
            No batches expiring in the next {horizon} days.
          </p>
        )}
        {!isLoading && data && data.length > 0 && (
          <>
            <div
              className="grid gap-0.5"
              role="img"
              aria-label={`Expiry heatmap — next ${horizon} days`}
              style={{
                gridTemplateColumns: `repeat(${COLS}, minmax(0, 1fr))`,
                gridTemplateRows: "repeat(7, minmax(0, 1fr))",
                gridAutoFlow: "column",
              }}
            >
              {cells.map((cell) => (
                <div
                  key={cell.date}
                  title={
                    cell.day
                      ? `${cell.date} — ${cell.day.batch_count} batch${
                          cell.day.batch_count === 1 ? "" : "es"
                        } (${cell.day.alert_level})`
                      : `${cell.date} — no expiries`
                  }
                  className={cn(
                    "aspect-square rounded-[3px] transition-colors",
                    cellTone(cell.day),
                  )}
                />
              ))}
            </div>
            <div className="flex items-center gap-3 text-[11px] text-text-secondary">
              <span>Less</span>
              <span className="inline-block h-3 w-3 rounded-[3px] bg-white/[0.025]" />
              <span className="inline-block h-3 w-3 rounded-[3px] bg-cyan-500/25" />
              <span className="inline-block h-3 w-3 rounded-[3px] bg-amber-500/30" />
              <span className="inline-block h-3 w-3 rounded-[3px] bg-amber-500/55" />
              <span className="inline-block h-3 w-3 rounded-[3px] bg-red-500/60" />
              <span className="inline-block h-3 w-3 rounded-[3px] bg-red-500/80" />
              <span>More</span>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
