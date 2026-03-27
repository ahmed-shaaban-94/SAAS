"use client";

import { useSites } from "@/hooks/use-sites";
import { useFilters } from "@/contexts/filter-context";
import { SummaryStats } from "@/components/shared/summary-stats";
import { SiteComparisonCards } from "@/components/sites/site-comparison-cards";
import { EmptyState } from "@/components/empty-state";
import { LoadingCard } from "@/components/loading-card";
import { formatCurrency, formatNumber } from "@/lib/formatters";

export function SiteOverview() {
  const { filters } = useFilters();
  const { data, error, isLoading } = useSites(filters);

  if (isLoading) {
    return (
      <div>
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          {Array.from({ length: 2 }).map((_, i) => (
            <LoadingCard key={i} lines={2} />
          ))}
        </div>
        <div className="mt-6 grid grid-cols-1 gap-6 md:grid-cols-2">
          <LoadingCard lines={6} className="h-64" />
          <LoadingCard lines={6} className="h-64" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <EmptyState
        title="Failed to load site data"
        description="An error occurred while fetching site performance data."
      />
    );
  }

  if (!data || data.items.length === 0) {
    return (
      <EmptyState
        title="No site data available"
        description="Try adjusting your filters or check back later."
      />
    );
  }

  const stats = [
    { label: "Total Revenue", value: formatCurrency(data.total) },
    { label: "Site Count", value: formatNumber(data.items.length) },
  ];

  return (
    <div>
      <SummaryStats stats={stats} className="mb-6" />
      <SiteComparisonCards items={data.items} total={data.total} />
    </div>
  );
}
