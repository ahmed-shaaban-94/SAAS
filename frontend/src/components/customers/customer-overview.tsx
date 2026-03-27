"use client";

import { useTopCustomers } from "@/hooks/use-top-customers";
import { useFilters } from "@/contexts/filter-context";
import { SummaryStats } from "@/components/shared/summary-stats";
import { RankingChart } from "@/components/shared/ranking-chart";
import { RankingTable } from "@/components/shared/ranking-table";
import { EmptyState } from "@/components/empty-state";
import { LoadingCard } from "@/components/loading-card";
import { formatCurrency, formatNumber } from "@/lib/formatters";

export function CustomerOverview() {
  const { filters } = useFilters();
  const { data, error, isLoading } = useTopCustomers(filters);

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
          <LoadingCard lines={8} className="h-96" />
        </div>
      </div>
    );
  }

  if (error) {
    console.error("Failed to load customer data:", error.message);
    return (
      <EmptyState
        title="Failed to load customer data"
        description={error.message || "An error occurred while fetching customer analytics. Please try again."}
      />
    );
  }

  if (!data || data.items.length === 0) {
    return (
      <EmptyState
        title="No customer data available"
        description="Try adjusting your filters or check back later."
      />
    );
  }

  const topCustomer = data.items[0];

  const stats = [
    { label: "Total Revenue", value: formatCurrency(data.total) },
    { label: "Customer Count", value: formatNumber(data.items.length) },
    { label: "Top Customer", value: topCustomer.name },
    { label: "Top Customer Revenue", value: formatCurrency(topCustomer.value) },
  ];

  return (
    <div>
      <SummaryStats stats={stats} />
      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <div className="rounded-lg border border-border bg-card p-6">
          <h3 className="mb-4 text-sm font-medium text-text-secondary">
            Top Customers by Revenue
          </h3>
          <RankingChart items={data.items.slice(0, 10)} />
        </div>
        <div className="rounded-lg border border-border bg-card p-6">
          <h3 className="mb-4 text-sm font-medium text-text-secondary">
            Customer Rankings
          </h3>
          <RankingTable items={data.items} entityLabel="Customer" />
        </div>
      </div>
    </div>
  );
}
