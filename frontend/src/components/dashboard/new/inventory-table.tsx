"use client";

import { useReorderWatchlist } from "@/hooks/use-reorder-watchlist";
import type { ReorderWatchlistItem } from "@/types/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { SkeletonEnhanced } from "@/components/ui/skeleton-enhanced";
import { cn } from "@/lib/utils";

export interface InventoryTableProps {
  /** Override the hook — useful for Storybook / tests. */
  items?: ReorderWatchlistItem[];
  limit?: number;
  className?: string;
}

const STATUS_BADGE: Record<ReorderWatchlistItem["status"], string> = {
  critical: "bg-red-500/15 text-red-200 border-red-500/30",
  low: "bg-amber-500/15 text-amber-200 border-amber-500/30",
  healthy: "bg-cyan-500/15 text-cyan-200 border-cyan-500/30",
};

function formatDays(value: number | null): string {
  if (value == null) return "—";
  if (value < 1) return "<1d";
  return `${Math.round(value)}d`;
}

function formatVelocity(value: number): string {
  if (value === 0) return "0/day";
  if (value < 1) return `${value.toFixed(1)}/day`;
  return `${Math.round(value)}/day`;
}

/**
 * Inventory reorder-watchlist table for the new dashboard (#502 / #507).
 *
 * Columns: Name · SKU · On hand · Days of stock · Velocity · Status.
 * Consumes the enriched ``/inventory/alerts/reorder`` shape directly
 * via ``useReorderWatchlist`` (no adapter mapping).
 */
export function InventoryTable({
  items,
  limit,
  className,
}: InventoryTableProps) {
  const hookResult = useReorderWatchlist(
    limit ? ({ limit } as Record<string, number>) : undefined,
  );
  const data = items !== undefined ? items : hookResult.data;
  const isLoading = items === undefined && hookResult.isLoading;

  return (
    <Card className={cn("flex flex-col", className)}>
      <CardHeader className="pb-3">
        <CardTitle>Reorder Watchlist</CardTitle>
      </CardHeader>
      <CardContent className="p-0 pt-0">
        {isLoading && (
          <div className="p-4" role="status" aria-label="Loading reorder watchlist">
            <SkeletonEnhanced className="h-10" lines={4} />
          </div>
        )}
        {!isLoading && data && data.length === 0 && (
          <p className="p-6 text-center text-sm text-text-secondary">
            No items below reorder point — stock levels look healthy.
          </p>
        )}
        {!isLoading && data && data.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-white/5 text-[10px] uppercase tracking-wider text-text-secondary">
                  <th className="px-4 py-2 text-left font-semibold">Name</th>
                  <th className="px-4 py-2 text-left font-semibold">SKU</th>
                  <th className="px-4 py-2 text-right font-semibold">On&nbsp;hand</th>
                  <th className="px-4 py-2 text-right font-semibold">Days</th>
                  <th className="px-4 py-2 text-right font-semibold">Velocity</th>
                  <th className="px-4 py-2 text-right font-semibold">Status</th>
                </tr>
              </thead>
              <tbody>
                {data.map((row) => (
                  <tr
                    key={`${row.product_key}-${row.site_key}`}
                    className="border-b border-white/[0.03] last:border-b-0 hover:bg-white/[0.02]"
                  >
                    <td className="px-4 py-2 font-medium text-text-primary">
                      {row.drug_name}
                    </td>
                    <td className="px-4 py-2 font-mono text-[11px] text-text-secondary">
                      {row.drug_code}
                    </td>
                    <td className="px-4 py-2 text-right tabular-nums text-text-primary">
                      {Math.round(Number(row.current_quantity))}
                    </td>
                    <td className="px-4 py-2 text-right tabular-nums text-text-secondary">
                      {formatDays(
                        row.days_of_stock == null
                          ? null
                          : Number(row.days_of_stock),
                      )}
                    </td>
                    <td className="px-4 py-2 text-right tabular-nums text-text-secondary">
                      {formatVelocity(Number(row.daily_velocity))}
                    </td>
                    <td className="px-4 py-2 text-right">
                      <span
                        className={cn(
                          "inline-block rounded-full border px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide",
                          STATUS_BADGE[row.status] ?? STATUS_BADGE.low,
                        )}
                      >
                        {row.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
