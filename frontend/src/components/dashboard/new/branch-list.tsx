"use client";

import { Users } from "lucide-react";
import { useSites } from "@/hooks/use-sites";
import type { RankingItem } from "@/types/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { SkeletonEnhanced } from "@/components/ui/skeleton-enhanced";
import { cn } from "@/lib/utils";

export interface BranchListProps {
  /** Override the hook — useful for Storybook / tests. */
  items?: RankingItem[];
  className?: string;
}

function formatEgp(value: number): string {
  if (value >= 1_000_000) return `EGP ${(value / 1_000_000).toFixed(2)}M`;
  if (value >= 1_000) return `EGP ${Math.round(value / 1_000)}K`;
  return `EGP ${Math.round(value)}`;
}

/**
 * Branch ranking list for the new dashboard (#502 / #507).
 *
 * Each row shows the branch name, revenue, percent-of-total, and a
 * compact staff count (new backend field from #507). Bar width
 * visualises the share without pulling in a chart library.
 */
export function BranchList({ items, className }: BranchListProps) {
  const hookResult = useSites();
  const data = items !== undefined ? items : hookResult.data?.items;
  const isLoading = items === undefined && hookResult.isLoading;

  return (
    <Card className={cn("flex flex-col", className)}>
      <CardHeader className="pb-3">
        <CardTitle>Top Branches</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2 p-4 pt-0">
        {isLoading && (
          <div role="status" aria-label="Loading branches">
            <SkeletonEnhanced className="h-12" lines={4} />
          </div>
        )}
        {!isLoading && data && data.length === 0 && (
          <p className="py-8 text-center text-sm text-text-secondary">
            No branches found for the selected period.
          </p>
        )}
        {!isLoading &&
          data &&
          data.length > 0 &&
          data.map((row) => (
            <div key={row.key} className="space-y-1">
              <div className="flex items-baseline justify-between gap-2">
                <span className="flex items-center gap-1.5 text-sm font-medium text-text-primary">
                  <span className="tabular-nums text-text-secondary">
                    {row.rank}.
                  </span>
                  {row.name}
                </span>
                <span className="text-sm tabular-nums text-text-primary">
                  {formatEgp(Number(row.value))}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <div
                  className="h-1.5 flex-1 overflow-hidden rounded-full bg-white/[0.04]"
                  role="progressbar"
                  aria-valuenow={Math.round(Number(row.pct_of_total))}
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-label={`${row.name} share`}
                >
                  <div
                    className="h-full rounded-full bg-cyan-400/70"
                    style={{ width: `${Math.min(100, Number(row.pct_of_total))}%` }}
                  />
                </div>
                <span className="w-10 shrink-0 text-right text-[11px] tabular-nums text-text-secondary">
                  {Number(row.pct_of_total).toFixed(1)}%
                </span>
              </div>
              {row.staff_count != null && (
                <div className="flex items-center gap-1 text-[11px] text-text-secondary">
                  <Users aria-hidden="true" className="h-3 w-3" />
                  <span>
                    {row.staff_count} staff
                  </span>
                </div>
              )}
            </div>
          ))}
      </CardContent>
    </Card>
  );
}
