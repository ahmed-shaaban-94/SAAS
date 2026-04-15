"use client";

import useSWR from "swr";
import { useFilters } from "@/contexts/filter-context";
import { EmptyState } from "@/components/empty-state";
import { ErrorRetry } from "@/components/error-retry";
import { LoadingCard } from "@/components/loading-card";
import { QuarantineActions } from "@/components/expiry/quarantine-actions";
import { fetchAPI, swrKey } from "@/lib/api-client";
import { formatDateLabel } from "@/lib/date-utils";
import { formatNumber } from "@/lib/formatters";
import type { ExpiryAlert } from "@/types/expiry";

export function ExpiredStockTable() {
  const { filters } = useFilters();
  const key = swrKey("/api/v1/expiry/expired", filters);
  const { data, error, isLoading, mutate } = useSWR(key, () =>
    fetchAPI<ExpiryAlert[]>("/api/v1/expiry/expired", filters),
  );

  if (isLoading) return <LoadingCard lines={8} className="h-[26rem]" />;
  if (error) {
    return (
      <ErrorRetry
        title="Failed to load expired stock"
        description="Expired stock data could not be loaded."
        onRetry={() => mutate()}
      />
    );
  }
  if (!data?.length) {
    return (
      <EmptyState
        title="No expired stock"
        description="Expired stock will appear here when batches pass their expiry date."
      />
    );
  }

  return (
    <section className="viz-panel rounded-[1.75rem] p-5">
      <div className="mb-4">
        <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-text-secondary">
          Expired Stock
        </p>
        <h3 className="mt-2 text-2xl font-bold tracking-tight text-text-primary">
          {formatNumber(data.length)} expired batches
        </h3>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[760px] text-left text-sm">
          <thead className="border-b border-border text-text-secondary">
            <tr>
              <th className="pb-3 pr-4 text-[11px] font-semibold uppercase tracking-[0.2em]">Drug</th>
              <th className="pb-3 pr-4 text-[11px] font-semibold uppercase tracking-[0.2em]">Batch</th>
              <th className="pb-3 pr-4 text-[11px] font-semibold uppercase tracking-[0.2em]">Site</th>
              <th className="pb-3 pr-4 text-right text-[11px] font-semibold uppercase tracking-[0.2em]">Qty</th>
              <th className="pb-3 pr-4 text-right text-[11px] font-semibold uppercase tracking-[0.2em]">Expired</th>
              <th className="pb-3 text-right text-[11px] font-semibold uppercase tracking-[0.2em]">Actions</th>
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
                <td className="py-3 pr-4 text-right text-text-secondary">{formatDateLabel(item.expiry_date)}</td>
                <td className="py-3 text-right">
                  <QuarantineActions batch={item} onComplete={() => void mutate()} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
