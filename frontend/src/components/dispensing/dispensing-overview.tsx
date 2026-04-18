"use client";

import { useMemo } from "react";
import { useFilters } from "@/contexts/filter-context";
import { useDispenseRate } from "@/hooks/use-dispense-rate";
import { useStockoutRisk } from "@/hooks/use-stockout-risk";
import { useDaysOfStock } from "@/hooks/use-days-of-stock";
import { useReconciliation } from "@/hooks/use-reconciliation";
import { StatCard } from "@/components/shared/stat-card";
import { LoadingCard } from "@/components/loading-card";
import { ErrorRetry } from "@/components/error-retry";
import { formatNumber } from "@/lib/formatters";

export function DispensingOverview() {
  const { filters } = useFilters();
  const rate = useDispenseRate(filters);
  const risk = useStockoutRisk();
  const days = useDaysOfStock(filters);
  const recon = useReconciliation();

  const stats = useMemo(() => {
    const activeProducts = rate.data.length;
    const stockoutRisk = risk.data.length;
    const daysWithStock = days.data.filter((d) => d.days_of_stock !== null);
    const avgDays =
      daysWithStock.length > 0
        ? daysWithStock.reduce((s, d) => s + (d.days_of_stock ?? 0), 0) / daysWithStock.length
        : 0;
    const varianceCount = recon.data?.items_with_variance ?? 0;

    return [
      { label: "Active Products", value: formatNumber(activeProducts) },
      { label: "Stockout Risk Items", value: formatNumber(stockoutRisk) },
      { label: "Avg Days of Stock", value: avgDays.toFixed(1) },
      { label: "Recon Variances", value: formatNumber(varianceCount) },
    ];
  }, [rate.data, risk.data, days.data, recon.data]);

  if (rate.isLoading || risk.isLoading || days.isLoading || recon.isLoading) {
    return (
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <LoadingCard key={i} lines={2} className="h-28" />
        ))}
      </div>
    );
  }

  if (rate.error || risk.error || days.error || recon.error) {
    return (
      <ErrorRetry
        title="Failed to load dispensing KPIs"
        description="Dispensing summary metrics could not be loaded."
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
