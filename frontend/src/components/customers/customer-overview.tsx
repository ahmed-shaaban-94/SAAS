"use client";

import { useTopCustomers } from "@/hooks/use-top-customers";
import { useFilters } from "@/contexts/filter-context";
import { SummaryStats } from "@/components/shared/summary-stats";
import { RankingChart } from "@/components/shared/ranking-chart";
import { RankingTableLinked } from "@/components/shared/ranking-table-linked";
import DistributionChart from "@/components/shared/distribution-chart";
import CsvExportButton from "@/components/shared/csv-export-button";
import { EmptyState } from "@/components/empty-state";
import { UploadDataAction } from "@/components/shared/empty-state-actions";
import { ErrorRetry } from "@/components/error-retry";
import { LoadingCard } from "@/components/loading-card";
import { RankingTableSkeleton } from "@/components/ui/table-skeleton";
import { formatCurrency, formatNumber } from "@/lib/formatters";

interface CustomerOverviewProps {
  /** Hide the legacy 4-stat SummaryStats row when the migrated page
   *  renders its own KpiCard grid above. */
  hideSummary?: boolean;
}

export function CustomerOverview({ hideSummary = false }: CustomerOverviewProps = {}) {
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
          <div className="rounded-xl border border-border bg-card p-5">
            <RankingTableSkeleton rows={8} />
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <ErrorRetry
        title="Failed to load customer data"
        description="Failed to load data. Please try again."
      />
    );
  }

  if (!data?.items?.length) {
    return (
      <EmptyState
        title="No customer data available"
        description="Try adjusting your filters or upload sales data to see customer analytics."
        action={<UploadDataAction />}
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

  const chartData = data.items.slice(0, 8).map((item) => ({
    name: item.name.length > 20 ? item.name.slice(0, 20) + "..." : item.name,
    value: item.value,
  }));

  const exportData = data.items.map((item) => ({
    Rank: item.rank,
    Customer: item.name,
    Revenue: item.value,
    "% of Total": item.pct_of_total,
  }));

  return (
    <div>
      {!hideSummary && <SummaryStats stats={stats} />}
      <div className={hideSummary ? "grid gap-6 lg:grid-cols-3" : "mt-6 grid gap-6 lg:grid-cols-3"}>
        <div className="viz-panel rounded-[1.7rem] p-6">
          <h3 className="mb-4 text-[11px] font-semibold uppercase tracking-[0.2em] text-text-secondary">
            Top Customers by Revenue
          </h3>
          <RankingChart items={data.items.slice(0, 10)} />
        </div>
        <div className="viz-panel rounded-[1.7rem] p-6">
          <h3 className="mb-4 text-[11px] font-semibold uppercase tracking-[0.2em] text-text-secondary">
            Revenue Distribution
          </h3>
          <DistributionChart data={chartData} />
        </div>
        <div className="viz-panel rounded-[1.7rem] p-6">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-[11px] font-semibold uppercase tracking-[0.2em] text-text-secondary">
              Customer Rankings
            </h3>
            <CsvExportButton data={exportData} filename="customers" />
          </div>
          <RankingTableLinked items={data.items} entityLabel="Customer" hrefPrefix="/customers" />
        </div>
      </div>
    </div>
  );
}
