"use client";

import { useTopProducts } from "@/hooks/use-top-products";
import { useTopCustomers } from "@/hooks/use-top-customers";
import { useFilters } from "@/contexts/filter-context";
import { formatCurrency } from "@/lib/formatters";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { LoadingCard } from "@/components/loading-card";
import type { RankingItem } from "@/types/api";

function RankingCard({
  title,
  href,
  items,
  isLoading,
  error,
}: {
  title: string;
  href: string;
  items: RankingItem[] | undefined;
  isLoading: boolean;
  error?: Error;
}) {
  if (isLoading) {
    return <LoadingCard lines={5} />;
  }

  if (error) {
    return (
      <div className="rounded-xl border border-border bg-card p-6 text-center">
        <p className="text-sm text-text-secondary">Failed to load {title.toLowerCase()}</p>
      </div>
    );
  }

  const top5 = items?.slice(0, 5) ?? [];

  return (
    <div className="rounded-xl border border-border bg-card">
      <div className="flex items-center justify-between border-b border-border px-5 py-4">
        <h3 className="text-sm font-semibold text-text-accent">{title}</h3>
        <Link
          href={href}
          className="flex items-center gap-1 text-xs font-medium text-accent hover:text-accent/80 transition-colors"
        >
          View All
          <ArrowRight className="h-3 w-3" />
        </Link>
      </div>
      <ul className="divide-y divide-border">
        {top5.map((item) => (
          <li
            key={item.key}
            className="relative px-5 py-3 hover:bg-divider/50 transition-colors"
          >
            <div className="flex items-center justify-between relative z-10">
              <div className="flex items-center gap-3 min-w-0">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-accent/10 text-xs font-semibold text-accent">
                  {item.rank}
                </span>
                <span className="truncate text-sm text-text-accent">
                  {item.name}
                </span>
              </div>
              <span className="shrink-0 text-sm font-medium text-text-accent">
                {formatCurrency(item.value)}
              </span>
            </div>
            <div className="mt-1.5 h-1 w-full overflow-hidden rounded-full bg-divider">
              <div
                className="h-full rounded-full bg-accent/30 transition-all"
                style={{ width: `${Math.min(item.pct_of_total, 100)}%` }}
              />
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function QuickRankings() {
  const { filters } = useFilters();
  const hookFilters = { ...filters, limit: 5 };

  const {
    data: products,
    error: productsError,
    isLoading: productsLoading,
  } = useTopProducts(hookFilters);

  const {
    data: customers,
    error: customersError,
    isLoading: customersLoading,
  } = useTopCustomers(hookFilters);

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      <RankingCard
        title="Top 5 Products"
        href="/products"
        items={products?.items}
        isLoading={productsLoading}
        error={productsError}
      />
      <RankingCard
        title="Top 5 Customers"
        href="/customers"
        items={customers?.items}
        isLoading={customersLoading}
        error={customersError}
      />
    </div>
  );
}
