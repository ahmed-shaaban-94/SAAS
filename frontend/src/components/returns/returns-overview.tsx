"use client";

import { useReturns } from "@/hooks/use-returns";
import { useFilters } from "@/contexts/filter-context";
import { SummaryStats } from "@/components/shared/summary-stats";
import { EmptyState } from "@/components/empty-state";
import { ErrorRetry } from "@/components/error-retry";
import { LoadingCard } from "@/components/loading-card";
import { TableSkeleton } from "@/components/ui/table-skeleton";
import { ReturnsChart } from "@/components/returns/returns-chart";
import { ReturnsTable } from "@/components/returns/returns-table";
import CsvExportButton from "@/components/shared/csv-export-button";
import { formatCurrency, formatNumber } from "@/lib/formatters";
import { useMemo } from "react";

const EXCLUDED_ORIGINS = new Set(["HVI", "Services", "Other"]);

function isNonProduct(r: { drug_brand: string; customer_name: string }): boolean {
  const brand = r.drug_brand.toUpperCase();
  const customer = r.customer_name.toUpperCase();
  return (
    brand === "UNCLAIMED MONEY" ||
    brand.startsWith("SPECIAL ORDER") ||
    customer === "UNCLAIMED MONEY" ||
    customer.startsWith("SPECIAL ORDER")
  );
}

export function ReturnsOverview() {
  const { filters } = useFilters();
  const { data, error, isLoading } = useReturns(filters);

  // Split data into product returns vs other
  const { productData, otherAmount, summaryStats } = useMemo(() => {
    if (!data || data.length === 0)
      return { productData: [], otherAmount: 0, summaryStats: [] };

    const product: typeof data = [];
    let otherAmt = 0;

    for (const r of data) {
      if (EXCLUDED_ORIGINS.has(r.origin) || isNonProduct(r)) {
        otherAmt += r.return_amount;
      } else {
        product.push(r);
      }
    }

    const productAmount = product.reduce((s, r) => s + r.return_amount, 0);
    const productQty = product.reduce((s, r) => s + r.return_quantity, 0);
    const totalAmount = productAmount + otherAmt;

    const stats = [
      { label: "Product Returns", value: formatCurrency(productAmount) },
      { label: "Other Returns", value: formatCurrency(otherAmt) },
      { label: "Total Returns", value: formatCurrency(totalAmount) },
      { label: "Return Quantity", value: formatNumber(productQty) },
    ];

    return { productData: product, otherAmount: otherAmt, summaryStats: stats };
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
          <div className="rounded-xl border border-border bg-card p-5 h-96">
            <TableSkeleton rows={8} cols={5} />
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <ErrorRetry
        title="Failed to load returns data"
        description="Failed to load data. Please try again."
      />
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
          <ReturnsChart items={productData} />
        </div>
        <div className="rounded-lg border border-border bg-card p-4">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-sm font-medium text-text-secondary">
              Return Details
            </h3>
            <CsvExportButton
              data={productData.map((r) => ({
                Product: r.drug_brand,
                Customer: r.customer_name,
                Quantity: r.return_quantity,
                Amount: r.return_amount,
                Count: r.return_count,
              }))}
              filename="returns"
            />
          </div>
          <ReturnsTable items={productData} />
        </div>
      </div>
    </div>
  );
}
