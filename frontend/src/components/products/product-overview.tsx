"use client";

import { useTopProducts } from "@/hooks/use-top-products";
import { useFilters } from "@/contexts/filter-context";
import { SummaryStats } from "@/components/shared/summary-stats";
import { RankingChart } from "@/components/shared/ranking-chart";
import { RankingTableLinked } from "@/components/shared/ranking-table-linked";
import DistributionChart from "@/components/shared/distribution-chart";
import CsvExportButton from "@/components/shared/csv-export-button";
import { EmptyState } from "@/components/empty-state";
import { LoadingCard } from "@/components/loading-card";
import { formatCurrency, formatNumber } from "@/lib/formatters";

export function ProductOverview() {
  const { filters } = useFilters();
  const { data, error, isLoading } = useTopProducts(filters);

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
    console.error("Failed to load product data:", error.message);
    return (
      <EmptyState
        title="Failed to load product data"
        description={error.message || "An error occurred while fetching product analytics. Please try again."}
      />
    );
  }

  if (!data || data.items.length === 0) {
    return (
      <EmptyState
        title="No product data available"
        description="Try adjusting your filters or check back later."
      />
    );
  }

  const topProduct = data.items[0];

  const stats = [
    { label: "Total Revenue", value: formatCurrency(data.total) },
    { label: "Product Count", value: formatNumber(data.items.length) },
    { label: "Top Product", value: topProduct.name },
    { label: "Top Product Revenue", value: formatCurrency(topProduct.value) },
  ];

  const chartData = data.items.slice(0, 8).map((item) => ({
    name: item.name.length > 20 ? item.name.slice(0, 20) + "..." : item.name,
    value: item.value,
  }));

  const exportData = data.items.map((item) => ({
    Rank: item.rank,
    Product: item.name,
    Revenue: item.value,
    "% of Total": item.pct_of_total,
  }));

  return (
    <div>
      <SummaryStats stats={stats} />
      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <div className="rounded-lg border border-border bg-card p-6">
          <h3 className="mb-4 text-sm font-medium text-text-secondary">
            Top Products by Revenue
          </h3>
          <RankingChart items={data.items.slice(0, 10)} />
        </div>
        <div className="rounded-lg border border-border bg-card p-6">
          <h3 className="mb-4 text-sm font-medium text-text-secondary">
            Revenue Distribution
          </h3>
          <DistributionChart data={chartData} />
        </div>
        <div className="rounded-lg border border-border bg-card p-6">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-sm font-medium text-text-secondary">
              Product Rankings
            </h3>
            <CsvExportButton data={exportData} filename="products" />
          </div>
          <RankingTableLinked items={data.items} entityLabel="Product" hrefPrefix="/products" />
        </div>
      </div>
    </div>
  );
}
