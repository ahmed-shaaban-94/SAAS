"use client";

import { useTopStaff } from "@/hooks/use-top-staff";
import { useFilters } from "@/contexts/filter-context";
import { SummaryStats } from "@/components/shared/summary-stats";
import { RankingChart } from "@/components/shared/ranking-chart";
import { RankingTable } from "@/components/shared/ranking-table";
import { EmptyState } from "@/components/empty-state";
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
    console.error("Failed to load staff data:", error.message);
    return (
      <EmptyState
        title="Failed to load staff data"
        description={error.message || "An error occurred while fetching staff performance data."}
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

  return (
    <div>
      <SummaryStats stats={stats} className="mb-6" />
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-lg border border-border bg-card p-6">
          <h3 className="mb-4 text-sm font-medium text-text-secondary">
            Top Staff by Revenue
          </h3>
          <RankingChart items={data.items} />
        </div>
        <div className="rounded-lg border border-border bg-card p-6">
          <h3 className="mb-4 text-sm font-medium text-text-secondary">
            Staff Rankings
          </h3>
          <RankingTable items={data.items} entityLabel="Staff Member" />
        </div>
      </div>
    </div>
  );
}
