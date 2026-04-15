"use client";

import { useState } from "react";
import { useFilters } from "@/contexts/filter-context";
import { EmptyState } from "@/components/empty-state";
import { ErrorRetry } from "@/components/error-retry";
import { LoadingCard } from "@/components/loading-card";
import { useNearExpiry } from "@/hooks/use-near-expiry";
import { formatDateLabel } from "@/lib/date-utils";
import { formatNumber } from "@/lib/formatters";
import { cn } from "@/lib/utils";

const tabs = [30, 60, 90] as const;

export function NearExpiryList() {
  const { filters } = useFilters();
  const [threshold, setThreshold] = useState<(typeof tabs)[number]>(30);
  const { data, error, isLoading, mutate } = useNearExpiry({
    ...filters,
    days_threshold: threshold,
    limit: 20,
  });

  return (
    <section className="viz-panel rounded-[1.75rem] p-5">
      <div className="mb-4 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-text-secondary">
            Near Expiry
          </p>
          <h3 className="mt-2 text-2xl font-bold tracking-tight text-text-primary">
            {formatNumber(data?.length ?? 0)} batches within {threshold} days
          </h3>
        </div>
        <div className="flex items-center gap-2">
          {tabs.map((tab) => (
            <button
              key={tab}
              onClick={() => setThreshold(tab)}
              className={cn(
                "rounded-full px-3 py-1.5 text-sm font-medium transition-colors",
                threshold === tab
                  ? "bg-accent text-page"
                  : "viz-panel-soft text-text-secondary hover:text-text-primary",
              )}
            >
              {tab}d
            </button>
          ))}
        </div>
      </div>

      {isLoading ? (
        <LoadingCard lines={6} className="h-[24rem]" />
      ) : error ? (
        <ErrorRetry
          title="Failed to load near-expiry batches"
          description="Near-expiry batches could not be loaded."
          onRetry={() => mutate()}
        />
      ) : !data?.length ? (
        <EmptyState
          title="No near-expiry batches"
          description={`No batches are expiring within ${threshold} days.`}
        />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead className="border-b border-border text-text-secondary">
              <tr>
                <th className="pb-3 pr-4 text-[11px] font-semibold uppercase tracking-[0.2em]">Drug</th>
                <th className="pb-3 pr-4 text-[11px] font-semibold uppercase tracking-[0.2em]">Batch</th>
                <th className="pb-3 pr-4 text-[11px] font-semibold uppercase tracking-[0.2em]">Site</th>
                <th className="pb-3 pr-4 text-right text-[11px] font-semibold uppercase tracking-[0.2em]">Qty</th>
                <th className="pb-3 pr-4 text-right text-[11px] font-semibold uppercase tracking-[0.2em]">Days</th>
                <th className="pb-3 text-right text-[11px] font-semibold uppercase tracking-[0.2em]">Expiry</th>
              </tr>
            </thead>
            <tbody>
              {data.map((item) => (
                <tr key={`${item.batch_number}-${item.site_code}`} className="border-b border-divider/70">
                  <td className="py-3 pr-4">
                    <p className="font-medium text-text-primary">{item.drug_name}</p>
                    <p className="text-xs text-text-secondary">{item.drug_code}</p>
                  </td>
                  <td className="py-3 pr-4 text-text-secondary">{item.batch_number}</td>
                  <td className="py-3 pr-4 text-text-secondary">{item.site_code}</td>
                  <td className="py-3 pr-4 text-right text-text-primary">{formatNumber(item.current_quantity)}</td>
                  <td className="py-3 pr-4 text-right text-text-primary">{formatNumber(item.days_to_expiry)}</td>
                  <td className="py-3 text-right text-text-secondary">{formatDateLabel(item.expiry_date)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
