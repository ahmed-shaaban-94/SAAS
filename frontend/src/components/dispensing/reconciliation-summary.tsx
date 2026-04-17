"use client";

import { useReconciliation } from "@/hooks/use-reconciliation";
import { LoadingCard } from "@/components/loading-card";
import { EmptyState } from "@/components/empty-state";
import { formatNumber, formatCurrency } from "@/lib/formatters";
import { cn } from "@/lib/utils";

export function ReconciliationSummary() {
  const { data, isLoading } = useReconciliation();

  if (isLoading) return <LoadingCard className="h-72" />;
  if (!data) return <EmptyState title="No reconciliation data" />;

  return (
    <div className="space-y-4">
      {/* Summary stats */}
      <div className="grid grid-cols-3 gap-4">
        <div className="rounded-xl border border-border bg-card p-4 text-center">
          <p className="text-2xl font-bold text-text-primary">{formatNumber(data.total_items)}</p>
          <p className="mt-1 text-xs text-text-secondary">Total Items</p>
        </div>
        <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 text-center">
          <p className="text-2xl font-bold text-amber-400">
            {formatNumber(data.items_with_variance)}
          </p>
          <p className="mt-1 text-xs text-text-secondary">Items with Variance</p>
        </div>
        <div
          className={cn(
            "rounded-xl border p-4 text-center",
            data.total_variance_value < 0
              ? "border-red-500/30 bg-red-500/10"
              : "border-border bg-card",
          )}
        >
          <p
            className={cn(
              "text-2xl font-bold",
              data.total_variance_value < 0 ? "text-red-400" : "text-text-primary",
            )}
          >
            {formatCurrency(Math.abs(data.total_variance_value))}
          </p>
          <p className="mt-1 text-xs text-text-secondary">
            {data.total_variance_value < 0 ? "Shrinkage" : "Surplus"} Value
          </p>
        </div>
      </div>

      {/* Variance table */}
      {data.entries.length > 0 && (
        <div className="overflow-x-auto rounded-xl border border-border">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-muted/40">
                <th className="px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-text-secondary">
                  Drug
                </th>
                <th className="px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-text-secondary">
                  Site
                </th>
                <th className="px-4 py-3 text-right text-[11px] font-semibold uppercase tracking-wider text-text-secondary">
                  Calculated
                </th>
                <th className="px-4 py-3 text-right text-[11px] font-semibold uppercase tracking-wider text-text-secondary">
                  Physical
                </th>
                <th className="px-4 py-3 text-right text-[11px] font-semibold uppercase tracking-wider text-text-secondary">
                  Variance
                </th>
                <th className="px-4 py-3 text-right text-[11px] font-semibold uppercase tracking-wider text-text-secondary">
                  Variance %
                </th>
                <th className="px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-text-secondary">
                  Last Count
                </th>
              </tr>
            </thead>
            <tbody>
              {data.entries
                .slice()
                .sort((a, b) => Math.abs(b.variance ?? 0) - Math.abs(a.variance ?? 0))
                .map((entry) => {
                  const hasVariance = entry.variance != null && entry.variance !== 0;
                  return (
                    <tr
                      key={`${entry.drug_code}-${entry.site_code}`}
                      className="border-b border-border/50 last:border-0 hover:bg-accent/5"
                    >
                      <td className="px-4 py-3">
                        <p className="font-medium text-text-primary">{entry.drug_name}</p>
                        <p className="text-xs text-text-secondary">{entry.drug_code}</p>
                      </td>
                      <td className="px-4 py-3 text-text-secondary">{entry.site_code}</td>
                      <td className="px-4 py-3 text-right">{formatNumber(entry.calculated_qty)}</td>
                      <td className="px-4 py-3 text-right">
                        {entry.physical_qty != null ? formatNumber(entry.physical_qty) : "—"}
                      </td>
                      <td
                        className={cn(
                          "px-4 py-3 text-right font-medium",
                          hasVariance && (entry.variance ?? 0) < 0
                            ? "text-red-400"
                            : hasVariance
                              ? "text-green-400"
                              : "text-text-secondary",
                        )}
                      >
                        {entry.variance != null
                          ? `${entry.variance > 0 ? "+" : ""}${formatNumber(entry.variance)}`
                          : "—"}
                      </td>
                      <td
                        className={cn(
                          "px-4 py-3 text-right text-xs",
                          hasVariance && (entry.variance_pct ?? 0) < 0
                            ? "text-red-400"
                            : hasVariance
                              ? "text-green-400"
                              : "text-text-secondary",
                        )}
                      >
                        {entry.variance_pct != null
                          ? `${entry.variance_pct > 0 ? "+" : ""}${entry.variance_pct.toFixed(1)}%`
                          : "—"}
                      </td>
                      <td className="px-4 py-3 text-xs text-text-secondary">
                        {entry.last_count_date
                          ? new Date(entry.last_count_date).toLocaleDateString()
                          : "Never"}
                      </td>
                    </tr>
                  );
                })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
