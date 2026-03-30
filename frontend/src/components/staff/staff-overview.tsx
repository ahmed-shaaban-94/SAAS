"use client";

import { useTopStaff } from "@/hooks/use-top-staff";
import { useFilters } from "@/contexts/filter-context";
import { SummaryStats } from "@/components/shared/summary-stats";
import { RankingChart } from "@/components/shared/ranking-chart";
import { RankingTableLinked } from "@/components/shared/ranking-table-linked";
import DistributionChart from "@/components/shared/distribution-chart";
import CsvExportButton from "@/components/shared/csv-export-button";
import { EmptyState } from "@/components/empty-state";
import { ErrorRetry } from "@/components/error-retry";
import { LoadingCard } from "@/components/loading-card";
import { formatCurrency, formatNumber } from "@/lib/formatters";

export function StaffOverview() {
  const { filters } = useFilters();
  const { data, error, isLoading } = useTopStaff(filters);

  if (isLoading) {
    return (
      <div>
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <LoadingCard key={i} lines={2} />
          ))}
        </div>
        <div className="mt-6 grid gap-6 lg:grid-cols-2">
          <LoadingCard lines={10} className="h-96" />
          <LoadingCard lines={10} className="h-96" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <ErrorRetry
        title="Failed to load staff data"
        description="Failed to load data. Please try again."
      />
    );
  }

  if (!data || data.items.length === 0) {
    return (
      <EmptyState
        title="No staff data available"
        description="Try adjusting your filters or check back later."
      />
    );
  }

  const topPerformer = data.items[0];

  const stats = [
    { label: "Total Revenue", value: formatCurrency(data.total) },
    { label: "Staff Count", value: formatNumber(data.items.length) },
    { label: "Top Performer", value: topPerformer.name },
    { label: "Top Revenue", value: formatCurrency(topPerformer.value) },
  ];

  const chartData = data.items.slice(0, 8).map((item) => ({
    name: item.name.length > 20 ? item.name.slice(0, 20) + "..." : item.name,
    value: item.value,
  }));

  const exportData = data.items.map((item) => ({
    Rank: item.rank,
    "Staff Member": item.name,
    Revenue: item.value,
    "% of Total": item.pct_of_total,
  }));

  return (
    <div>
      <SummaryStats stats={stats} className="mb-6" />
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="rounded-lg border border-border bg-card p-6">
          <h3 className="mb-4 text-sm font-medium text-text-secondary">
            Top Staff by Revenue
          </h3>
          <RankingChart items={data.items} />
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
              Staff Rankings
            </h3>
            <CsvExportButton data={exportData} filename="staff" />
          </div>
          <RankingTableLinked items={data.items} entityLabel="Staff Member" hrefPrefix="/staff" />
        </div>
      </div>
    </div>
  );
}
