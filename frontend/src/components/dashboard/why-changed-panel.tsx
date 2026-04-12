"use client";

import { memo } from "react";
import { useWhyChanged } from "@/hooks/use-why-changed";
import { useFilters } from "@/contexts/filter-context";
import { WaterfallChart } from "@/components/dashboard/waterfall-chart";
import { LoadingCard } from "@/components/loading-card";
import { EmptyState } from "@/components/empty-state";
import { ErrorRetry } from "@/components/error-retry";

export const WhyChangedPanel = memo(function WhyChangedPanel() {
  const { filters } = useFilters();
  const { data, error, isLoading } = useWhyChanged(filters);

  if (isLoading) return <LoadingCard lines={4} className="h-64" />;
  if (error) return <ErrorRetry title="Failed to load revenue drivers" onRetry={() => {}} />;
  if (!data || !data.drivers?.length) {
    return (
      <EmptyState
        title="No revenue drivers available"
        description="Select a longer date range to see what drove revenue changes"
      />
    );
  }

  return <WaterfallChart data={data} periodLabel={filters?.start_date && filters?.end_date ? `${filters.start_date} to ${filters.end_date}` : undefined} />;
});
