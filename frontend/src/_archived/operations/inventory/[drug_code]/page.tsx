"use client";

/**
 * /inventory/[drug_code] — single-drug inventory drill-down on the v2
 * shell. Migrated from `(app)/inventory/[drug_code]/page.tsx`. Inherits
 * V2Layout from /inventory's layout.
 */

import Link from "next/link";
import useSWR from "swr";
import { useMemo } from "react";
import { ArrowLeft, Boxes, Building2, PackageCheck, Clock } from "lucide-react";
import { useParams } from "next/navigation";

import { useFilters } from "@/contexts/filter-context";
import { fetchAPI, swrKey } from "@/lib/api-client";
import { formatDateLabel } from "@/lib/date-utils";
import { formatNumber } from "@/lib/formatters";
import { DashboardShell } from "@/components/dashboard-v2/shell";
import { KpiCard, type KpiColor, type KpiDir } from "@/components/dashboard/new";
import { EmptyState } from "@/components/empty-state";
import { ErrorRetry } from "@/components/error-retry";
import { FilterBar } from "@/components/filters/filter-bar";
import { LoadingCard } from "@/components/loading-card";
import { StockHistoryChart } from "@/components/inventory/stock-history-chart";
import { ReorderConfigForm } from "@/components/inventory/reorder-config-form";
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

  const kpis = useMemo(() => {
    return [
      {
        id: "stock",
        label: "Current Stock",
        value: formatNumber(totalQuantity),
        delta: { dir: "up" as KpiDir, text: "on-hand across sites" },
        sub: "sum of current_quantity",
        color: "accent" as KpiColor,
        sparkline: [] as number[],
        icon: Boxes,
      },
      {
        id: "sites",
        label: "Sites Covered",
        value: formatNumber(stockRows.length),
        delta: { dir: "up" as KpiDir, text: "branches stocking" },
        sub: "distinct branches with this SKU",
        color: "purple" as KpiColor,
        sparkline: [] as number[],
        icon: Building2,
      },
      {
        id: "dispensed",
        label: "Total Dispensed",
        value: formatNumber(totalDispensed),
        delta: { dir: "up" as KpiDir, text: "cumulative units" },
        sub: "all-time outflow",
        color: "amber" as KpiColor,
        sparkline: [] as number[],
        icon: PackageCheck,
      },
      {
        id: "last",
        label: "Last Movement",
        value: lastMovement ? formatDateLabel(lastMovement) : "No activity",
        delta: {
          dir: (lastMovement ? "up" : "down") as KpiDir,
          text: lastMovement ? "recent" : "stale",
        },
        sub: "most recent stock change",
        color: "red" as KpiColor,
        sparkline: [] as number[],
        icon: Clock,
      },
    ];
  }, [totalQuantity, stockRows.length, totalDispensed, lastMovement]);

  const isLoading = stock.isLoading || movements.isLoading || batches.isLoading;
  const hasError = stock.error || movements.error || batches.error;

  return (
    <DashboardShell
      activeHref="/inventory"
      breadcrumbs={[
        { label: "DataPulse", href: "/dashboard" },
        { label: "Operations" },
        { label: "Inventory", href: "/inventory" },
        { label: stockRows[0]?.drug_name ?? drugCode },
      ]}
    >
      <div className="page">
        {isLoading ? (
          <div className="space-y-6">
            <LoadingCard lines={2} />
            <div className="grid gap-4 md:grid-cols-4">
              {Array.from({ length: 4 }).map((_, index) => (
                <LoadingCard key={index} lines={2} />
              ))}
            </div>
            <LoadingCard lines={8} className="h-[24rem]" />
          </div>
        ) : hasError ? (
          <ErrorRetry
            title="Failed to load inventory product detail"
            description="The product inventory detail page could not be loaded."
            onRetry={() => {
              void stock.mutate();
              void movements.mutate();
              void batches.mutate();
            }}
          />
        ) : !stockRows.length ? (
          <EmptyState
            title="Product not found in inventory"
            description="No inventory records were found for this drug code."
          />
        ) : (
          <>
            {(() => {
              const product = stockRows[0];
              return (
                <div>
                  <h1 className="page-title">{product.drug_name}</h1>
                  <p className="page-sub">
                    {product.drug_code} · {product.drug_brand}
                  </p>
                </div>
              );
            })()}

            <FilterBar />

            <section
              className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4"
              aria-label="Inventory detail KPIs"
            >
              {kpis.map((k) => (
                <KpiCard
                  key={k.id}
                  label={k.label}
                  value={k.value}
                  delta={k.delta}
                  sub={k.sub}
                  color={k.color}
                  sparkline={k.sparkline}
                  icon={k.icon}
                />
              ))}
            </section>

            <div className="grid gap-6 xl:grid-cols-[1.6fr_1fr]">
              <StockHistoryChart drugCode={drugCode} filters={filters} />
              <ReorderConfigForm drugCode={drugCode} stockLevels={stockRows} />
            </div>

            <div className="grid gap-6 xl:grid-cols-2">
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

            <Link
              href="/inventory"
              className="inline-flex items-center gap-1 text-sm text-accent hover:underline"
            >
              <ArrowLeft className="h-4 w-4" />
              Back to inventory
            </Link>
          </>
        )}
      </div>
    </DashboardShell>
  );
}
