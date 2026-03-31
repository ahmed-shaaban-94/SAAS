"use client";

import { useState } from "react";
import { useTopMovers } from "@/hooks/use-top-movers";
import { useFilters } from "@/contexts/filter-context";
import { LoadingCard } from "@/components/loading-card";
import { EmptyState } from "@/components/empty-state";
import { formatCurrency } from "@/lib/formatters";
import { TrendingUp, TrendingDown } from "lucide-react";
import { cn } from "@/lib/utils";
import type { MoverItem } from "@/types/api";

const ENTITY_TABS = [
  { key: "product" as const, label: "Products" },
  { key: "customer" as const, label: "Customers" },
  { key: "staff" as const, label: "Staff" },
];

function MoverRow({ item }: { item: MoverItem }) {
  const isUp = item.direction === "up";
  return (
    <div className="flex items-center justify-between py-2">
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-text-primary">
          {item.name}
        </p>
        <p className="text-xs text-text-secondary">
          {formatCurrency(item.current_value)}
        </p>
      </div>
      <div
        className={cn(
          "flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold",
          isUp
            ? "bg-growth-green/10 text-growth-green"
            : "bg-growth-red/10 text-growth-red",
        )}
      >
        {isUp ? (
          <TrendingUp className="h-3 w-3" />
        ) : (
          <TrendingDown className="h-3 w-3" />
        )}
        {isUp ? "+" : ""}
        {item.change_pct.toFixed(1)}%
      </div>
    </div>
  );
}

export function TopMoversCard() {
  const [entityType, setEntityType] = useState<"product" | "customer" | "staff">("product");
  const { filters } = useFilters();
  const { data, isLoading } = useTopMovers(entityType, filters);

  if (isLoading) return <LoadingCard lines={8} className="h-96" />;

  return (
    <div className="rounded-xl border border-border bg-card p-5">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-text-secondary">
          Top Movers
        </h3>
        <div className="flex gap-1 rounded-lg bg-background p-1">
          {ENTITY_TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setEntityType(tab.key)}
              className={cn(
                "rounded-md px-3 py-1 text-xs font-medium transition-all",
                entityType === tab.key
                  ? "bg-accent/20 text-accent"
                  : "text-text-secondary hover:text-text-primary",
              )}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {!data || (data.gainers.length === 0 && data.losers.length === 0) ? (
        <EmptyState title="No movers data for this period" />
      ) : (
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
          {/* Gainers */}
          <div>
            <div className="mb-2 flex items-center gap-1.5">
              <TrendingUp className="h-4 w-4 text-growth-green" />
              <span className="text-xs font-semibold text-growth-green">
                Top Gainers
              </span>
            </div>
            <div className="divide-y divide-border">
              {data.gainers.map((item) => (
                <MoverRow key={item.key} item={item} />
              ))}
            </div>
          </div>

          {/* Losers */}
          <div>
            <div className="mb-2 flex items-center gap-1.5">
              <TrendingDown className="h-4 w-4 text-growth-red" />
              <span className="text-xs font-semibold text-growth-red">
                Top Losers
              </span>
            </div>
            <div className="divide-y divide-border">
              {data.losers.map((item) => (
                <MoverRow key={item.key} item={item} />
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
