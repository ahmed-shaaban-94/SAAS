"use client";

import { useDispenseRate } from "@/hooks/use-dispense-rate";
import { LoadingCard } from "@/components/loading-card";
import { EmptyState } from "@/components/empty-state";
import { formatNumber } from "@/lib/formatters";
import { TrendingUp } from "lucide-react";

export function DispenseRateCards() {
  const { data, isLoading } = useDispenseRate();

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        {Array.from({ length: 10 }).map((_, i) => (
          <LoadingCard key={i} lines={2} />
        ))}
      </div>
    );
  }

  if (!data.length) return <EmptyState title="No dispense rate data" />;

  const top10 = [...data]
    .sort((a, b) => b.avg_daily_dispense - a.avg_daily_dispense)
    .slice(0, 10);

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
      {top10.map((item, i) => (
        <div
          key={item.product_key}
          className="rounded-xl border border-border bg-card p-3 transition-colors hover:border-accent/50"
        >
          <div className="flex items-start justify-between gap-2">
            <p className="line-clamp-2 text-[11px] font-semibold text-text-secondary leading-tight">
              {item.drug_name}
            </p>
            <span className="flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full bg-accent/15 text-[10px] font-bold text-accent">
              {i + 1}
            </span>
          </div>
          <p className="mt-2 text-lg font-bold text-text-primary">
            {formatNumber(Math.round(item.avg_daily_dispense))}
            <span className="ml-1 text-xs font-normal text-text-secondary">/day</span>
          </p>
          <div className="mt-1 flex items-center gap-1 text-xs text-text-secondary">
            <TrendingUp className="h-3 w-3 text-green-400" />
            <span>{formatNumber(Math.round(item.avg_weekly_dispense))}/wk</span>
          </div>
          <p className="mt-0.5 truncate text-[10px] text-text-secondary">{item.drug_code}</p>
        </div>
      ))}
    </div>
  );
}
