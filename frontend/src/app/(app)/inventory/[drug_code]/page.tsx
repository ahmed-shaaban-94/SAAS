"use client";

import Link from "next/link";
import useSWR from "swr";
import { ArrowLeft } from "lucide-react";
import { useParams } from "next/navigation";
import { useFilters } from "@/contexts/filter-context";
import { fetchAPI, swrKey } from "@/lib/api-client";
import { formatDateLabel } from "@/lib/date-utils";
import { formatNumber } from "@/lib/formatters";
import { EmptyState } from "@/components/empty-state";
import { ErrorRetry } from "@/components/error-retry";
import { FilterBar } from "@/components/filters/filter-bar";
import { LoadingCard } from "@/components/loading-card";
import { StockHistoryChart } from "@/components/inventory/stock-history-chart";
import { ReorderConfigForm } from "@/components/inventory/reorder-config-form";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { Header } from "@/components/layout/header";
import { PageTransition } from "@/components/layout/page-transition";
import { StatCard } from "@/components/shared/stat-card";
import { useProductMovements } from "@/hooks/use-product-movements";
import { useProductStock } from "@/hooks/use-product-stock";
import type { BatchInfo } from "@/types/expiry";

export default function ProductInventoryDetailPage() {
  const params = useParams<{ drug_code: string }>();
  const drugCode = params.drug_code;
  const { filters } = useFilters();
  const stock = useProductStock(drugCode, filters);
  const movements = useProductMovements(drugCode, filters);
  const batchesKey = swrKey(`/api/v1/expiry/batches/${drugCode}`, filters);
  const batches = useSWR(
    drugCode ? batchesKey : null,
    () => fetchAPI<BatchInfo[]>(`/api/v1/expiry/batches/${drugCode}`, filters),
  );

  const stockRows = stock.data ?? [];
  const totalQuantity = stockRows.reduce((sum, item) => sum + item.current_quantity, 0);
  const totalDispensed = stockRows.reduce((sum, item) => sum + item.total_dispensed, 0);
  const lastMovement = stockRows
    .map((item) => item.last_movement_date)
    .filter((item): item is string => Boolean(item))
    .sort()
    .at(-1);
  const latestMovements = [...(movements.data ?? [])]
    .sort((left, right) => right.movement_date.localeCompare(left.movement_date))
    .slice(0, 8);

  if (stock.isLoading || movements.isLoading || batches.isLoading) {
    return (
      <PageTransition>
        <div className="space-y-6">
          <LoadingCard lines={2} />
          <div className="grid gap-4 md:grid-cols-4">
            {Array.from({ length: 4 }).map((_, index) => (
              <LoadingCard key={index} lines={2} />
            ))}
          </div>
          <LoadingCard lines={8} className="h-[24rem]" />
        </div>
      </PageTransition>
    );
  }

  if (stock.error || movements.error || batches.error) {
    return (
      <PageTransition>
        <ErrorRetry
          title="Failed to load inventory product detail"
          description="The product inventory detail page could not be loaded."
          onRetry={() => {
            void stock.mutate();
            void movements.mutate();
            void batches.mutate();
          }}
        />
      </PageTransition>
    );
  }

  if (!stockRows.length) {
    return (
      <PageTransition>
        <EmptyState
          title="Product not found in inventory"
          description="No inventory records were found for this drug code."
        />
      </PageTransition>
    );
  }

  const product = stockRows[0];

  return (
    <PageTransition>
      <Breadcrumbs />
      <Header
        title={`${product.drug_name} Inventory`}
        description={`${product.drug_code} • ${product.drug_brand}`}
      />
      <FilterBar />

      <div className="mb-6 flex items-center gap-2">
        <Link href="/inventory" className="inline-flex items-center gap-1 text-sm text-accent hover:underline">
          <ArrowLeft className="h-4 w-4" />
          Back to inventory
        </Link>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Current Stock" value={formatNumber(totalQuantity)} />
        <StatCard label="Sites Covered" value={formatNumber(stockRows.length)} />
        <StatCard label="Total Dispensed" value={formatNumber(totalDispensed)} />
        <StatCard label="Last Movement" value={lastMovement ? formatDateLabel(lastMovement) : "No activity"} />
      </div>

      <div className="mt-6 grid gap-6 xl:grid-cols-[1.6fr_1fr]">
        <StockHistoryChart drugCode={drugCode} filters={filters} />
        <ReorderConfigForm drugCode={drugCode} stockLevels={stockRows} />
      </div>

      <div className="mt-6 grid gap-6 xl:grid-cols-2">
        <section className="viz-panel rounded-[1.75rem] p-5">
          <div className="mb-4">
            <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-text-secondary">
              Movement Timeline
            </p>
            <h3 className="mt-2 text-2xl font-bold tracking-tight text-text-primary">
              {formatNumber(latestMovements.length)} recent movements
            </h3>
          </div>

          {!latestMovements.length ? (
            <EmptyState
              title="No recent movements"
              description="Movement activity for this product will appear here."
            />
          ) : (
            <div className="space-y-3">
              {latestMovements.map((movement) => (
                <div
                  key={movement.movement_key}
                  className="rounded-[1.25rem] border border-border/70 px-4 py-3"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-medium text-text-primary">{movement.movement_type}</p>
                      <p className="text-sm text-text-secondary">
                        {movement.site_code}
                        {movement.batch_number ? ` • Batch ${movement.batch_number}` : ""}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="font-semibold text-text-primary">{formatNumber(movement.quantity)}</p>
                      <p className="text-sm text-text-secondary">{formatDateLabel(movement.movement_date)}</p>
                    </div>
                  </div>
                  {movement.reference && (
                    <p className="mt-2 text-sm text-text-secondary">Reference: {movement.reference}</p>
                  )}
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="viz-panel rounded-[1.75rem] p-5">
          <div className="mb-4">
            <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-text-secondary">
              Batch Inventory
            </p>
            <h3 className="mt-2 text-2xl font-bold tracking-tight text-text-primary">
              {formatNumber(batches.data?.length ?? 0)} active batches
            </h3>
          </div>

          {!batches.data?.length ? (
            <EmptyState
              title="No active batches"
              description="Batch-level inventory for this product will appear here."
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[520px] text-left text-sm">
                <thead className="border-b border-border text-text-secondary">
                  <tr>
                    <th className="pb-3 pr-4 text-[11px] font-semibold uppercase tracking-[0.2em]">Batch</th>
                    <th className="pb-3 pr-4 text-[11px] font-semibold uppercase tracking-[0.2em]">Site</th>
                    <th className="pb-3 pr-4 text-right text-[11px] font-semibold uppercase tracking-[0.2em]">Qty</th>
                    <th className="pb-3 pr-4 text-right text-[11px] font-semibold uppercase tracking-[0.2em]">Days</th>
                    <th className="pb-3 text-right text-[11px] font-semibold uppercase tracking-[0.2em]">Expiry</th>
                  </tr>
                </thead>
                <tbody>
                  {batches.data.map((batch) => (
                    <tr key={`${batch.batch_number}-${batch.site_code}`} className="border-b border-divider/70">
                      <td className="py-3 pr-4 font-medium text-text-primary">{batch.batch_number}</td>
                      <td className="py-3 pr-4 text-text-secondary">{batch.site_code}</td>
                      <td className="py-3 pr-4 text-right text-text-primary">{formatNumber(batch.current_quantity)}</td>
                      <td className="py-3 pr-4 text-right text-text-primary">{formatNumber(batch.days_to_expiry)}</td>
                      <td className="py-3 text-right text-text-secondary">{formatDateLabel(batch.expiry_date)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>
    </PageTransition>
  );
}
