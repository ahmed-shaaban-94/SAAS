"use client";

import { useMemo } from "react";
import { useFilters } from "@/contexts/filter-context";
import { LoadingCard } from "@/components/loading-card";
import { ErrorRetry } from "@/components/error-retry";
import { StatCard } from "@/components/shared/stat-card";
import { useReorderAlerts } from "@/hooks/use-reorder-alerts";
import { useStockLevels } from "@/hooks/use-stock-levels";
import { useStockValuation } from "@/hooks/use-stock-valuation";
import { formatCurrency, formatNumber } from "@/lib/formatters";

export function InventoryOverview() {
  const { filters } = useFilters();
  const stockLevels = useStockLevels(filters);
  const reorderAlerts = useReorderAlerts(filters);
  const valuation = useStockValuation(filters);

  const stats = useMemo(() => {
    const totalStockValue = (valuation.data ?? []).reduce((sum, item) => sum + item.stock_value, 0);
    const stockoutCount = (reorderAlerts.data ?? []).filter((item) => item.current_quantity <= 0).length;

    return [
      { label: "Total Stock Value", value: formatCurrency(totalStockValue) },
      { label: "Items Below Reorder", value: formatNumber(reorderAlerts.data?.length ?? 0) },
      { label: "Stockout Count", value: formatNumber(stockoutCount) },
      { label: "Tracked Items", value: formatNumber(stockLevels.data?.length ?? 0) },
    ];
  }, [reorderAlerts.data, stockLevels.data, valuation.data]);

  if (stockLevels.isLoading || reorderAlerts.isLoading || valuation.isLoading) {
    return (
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }).map((_, index) => (
          <LoadingCard key={index} lines={2} className="h-28" />
        ))}
      </div>
    );
  }

  if (stockLevels.error || reorderAlerts.error || valuation.error) {
    return (
      <ErrorRetry
        title="Failed to load inventory KPIs"
        description="Inventory summary metrics could not be loaded."
        onRetry={() => {
          void stockLevels.mutate();
          void reorderAlerts.mutate();
          void valuation.mutate();
        }}
      />
    );
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      {stats.map((stat) => (
        <StatCard key={stat.label} label={stat.label} value={stat.value} />
      ))}
    </div>
  );
}
