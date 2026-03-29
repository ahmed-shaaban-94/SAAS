"use client";

import { useReturns } from "@/hooks/use-returns";
import { useFilters } from "@/contexts/filter-context";
import { SummaryStats } from "@/components/shared/summary-stats";
import { EmptyState } from "@/components/empty-state";
import { LoadingCard } from "@/components/loading-card";
import { ReturnsChart } from "@/components/returns/returns-chart";
import { ReturnsTable } from "@/components/returns/returns-table";
import CsvExportButton from "@/components/shared/csv-export-button";
import { formatCurrency, formatNumber } from "@/lib/formatters";
import { useMemo } from "react";

export function ReturnsOverview() {
  const { filters } = useFilters();
  const { data, error, isLoading } = useReturns(filters);

  const summaryStats = useMemo(() => {
    if (!data || data.length === 0) return [];

    const totalAmount = data.reduce((sum, r) => sum + r.return_amount, 0);
    const totalQuantity = data.reduce((sum, r) => sum + r.return_quantity, 0);
    const totalCount = data.reduce((sum, r) => sum + r.return_count, 0);
    const uniqueProducts = new Set(data.map((r) => r.drug_name)).size;

    return [
      { label: "Total Return Amount", value: formatCurrency(totalAmount) },
      { label: "Total Return Quantity", value: formatNumber(totalQuantity) },
      { label: "Total Return Count", value: formatNumber(totalCount) },
      { label: "Unique Products", value: formatNumber(uniqueProducts) },
    ];
  }, [data]);

  if (isLoading) {
    return (
      <div>
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <LoadingCard key={i} lines={2} />
          ))}
        </div>
        <div className="mt-6 grid gap-6 lg:grid-cols-2">
          <LoadingCard lines={8} className="h-96" />
          <LoadingCard lines={12} className="h-96" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-border bg-card p-6 text-center">
        <p className="text-text-secondary">
          Failed to load returns data. Please try again later.
        </p>
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <EmptyState
        title="No returns data"
        description="No return records found for the selected filters."
      />
    );
  }

  return (
    <div>
      <SummaryStats stats={summaryStats} className="mb-6" />
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-lg border border-border bg-card p-4">
          <h3 className="mb-4 text-sm font-medium text-text-secondary">
            Top Returns by Amount
          </h3>
          <ReturnsChart items={data} />
        </div>
        <div className="rounded-lg border border-border bg-card p-4">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-sm font-medium text-text-secondary">
              Return Details
            </h3>
            <CsvExportButton
              data={data.map((r) => ({
                Product: r.drug_name,
                Customer: r.customer_name,
                Quantity: r.return_quantity,
                Amount: r.return_amount,
                Count: r.return_count,
              }))}
              filename="returns"
            />
          </div>
          <ReturnsTable items={data} />
        </div>
      </div>
    </div>
  );
}
