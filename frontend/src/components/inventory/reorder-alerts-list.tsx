"use client";

import Link from "next/link";
import { useMemo } from "react";
import { AlertTriangle, ArrowRight } from "lucide-react";
import { useFilters } from "@/contexts/filter-context";
import { EmptyState } from "@/components/empty-state";
import { ErrorRetry } from "@/components/error-retry";
import { LoadingCard } from "@/components/loading-card";
import { useReorderAlerts } from "@/hooks/use-reorder-alerts";
import { formatNumber } from "@/lib/formatters";
import { cn } from "@/lib/utils";

const severityClassName = {
  stockout: "border-growth-red/40 bg-growth-red/10 text-growth-red",
  critical: "border-chart-amber/40 bg-chart-amber/10 text-chart-amber",
  at_risk: "border-accent/30 bg-accent/10 text-accent",
} as const;

export function ReorderAlertsList() {
  const { filters } = useFilters();
  const { data, error, isLoading, mutate } = useReorderAlerts(filters);

  const items = useMemo(() => {
    return [...(data ?? [])]
      .sort((left, right) => {
        const rank = { stockout: 0, critical: 1, at_risk: 2 };
        return rank[left.risk_level] - rank[right.risk_level];
      })
      .slice(0, 6);
  }, [data]);

  if (isLoading) return <LoadingCard lines={4} className="h-[24rem]" />;
  if (error) {
    return (
      <ErrorRetry
        title="Failed to load reorder alerts"
        description="Reorder risk alerts could not be loaded."
        onRetry={() => mutate()}
      />
    );
  }
  if (!items.length) {
    return (
      <div className="viz-panel rounded-[1.75rem] p-5">
        <EmptyState
          title="No active reorder alerts"
          description="Products at reorder risk will appear here."
        />
      </div>
    );
  }

  return (
    <section className="viz-panel rounded-[1.75rem] p-5">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-text-secondary">
            Reorder Alerts
          </p>
          <h3 className="mt-2 text-2xl font-bold tracking-tight text-text-primary">
            {formatNumber(data?.length ?? 0)} active alerts
          </h3>
        </div>
        <AlertTriangle className="h-5 w-5 text-chart-amber" />
      </div>

      <div className="space-y-3">
        {items.map((item) => (
          <Link
            key={`${item.drug_code}-${item.site_code}`}
            href={`/inventory/${item.drug_code}`}
            className="block rounded-[1.35rem] border border-border/70 p-4 transition-colors hover:border-accent/40 hover:bg-accent/5"
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="font-semibold text-text-primary">{item.drug_name}</p>
                <p className="mt-1 text-sm text-text-secondary">
                  {item.drug_code} • {item.site_code}
                </p>
              </div>
              <span className={cn("rounded-full border px-2.5 py-1 text-xs font-semibold uppercase tracking-wide", severityClassName[item.risk_level])}>
                {item.risk_level.replace("_", " ")}
              </span>
            </div>
            <div className="mt-3 flex flex-wrap items-center gap-4 text-sm text-text-secondary">
              <span>On hand: {formatNumber(item.current_quantity)}</span>
              <span>Reorder point: {formatNumber(item.reorder_point)}</span>
              <span>Suggested order: {formatNumber(item.suggested_reorder_qty)}</span>
              <span className="inline-flex items-center gap-1 text-accent">
                View detail
                <ArrowRight className="h-3.5 w-3.5" />
              </span>
            </div>
          </Link>
        ))}
      </div>
    </section>
  );
}
