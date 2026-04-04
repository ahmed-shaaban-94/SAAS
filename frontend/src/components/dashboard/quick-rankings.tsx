"use client";

import { useDashboardData } from "@/contexts/dashboard-data-context";
import { formatCurrency } from "@/lib/formatters";
import Link from "next/link";
import { ArrowRight, Package, Users, Trophy } from "lucide-react";
import { LoadingCard } from "@/components/loading-card";
import { cn } from "@/lib/utils";
import type { RankingItem } from "@/types/api";

const RANK_COLORS = [
  "from-chart-amber/20 to-chart-amber/5 text-chart-amber border-chart-amber/30",
  "from-text-secondary/15 to-text-secondary/5 text-text-secondary border-text-secondary/30",
  "from-chart-amber/10 to-chart-amber/5 text-chart-amber/70 border-chart-amber/20",
];

function RankingCard({
  title,
  href,
  items,
  isLoading,
  error,
  icon: Icon,
  accentColor,
}: {
  title: string;
  href: string;
  items: RankingItem[] | undefined;
  isLoading: boolean;
  error?: Error;
  icon: React.ComponentType<{ className?: string }>;
  accentColor: string;
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
    <div className="group rounded-xl border border-border bg-card transition-all duration-300 hover:border-accent/30 hover:shadow-lg hover:shadow-accent/5">
      <div className="flex items-center justify-between border-b border-border px-5 py-4">
        <div className="flex items-center gap-2.5">
          <div className={cn("flex h-8 w-8 items-center justify-center rounded-lg", accentColor)}>
            <Icon className="h-4 w-4" />
          </div>
          <h3 className="text-sm font-semibold text-text-primary">{title}</h3>
        </div>
        <Link
          href={href}
          className="flex items-center gap-1 rounded-full px-3 py-1 text-xs font-medium text-accent transition-all hover:bg-accent/10"
        >
          View All
          <ArrowRight className="h-3 w-3 transition-transform group-hover:translate-x-0.5" />
        </Link>
      </div>
      <ul className="divide-y divide-border/50">
        {top5.map((item, index) => (
          <li
            key={item.key}
            className="relative px-5 py-3.5 transition-colors hover:bg-accent/5"
          >
            <div className="flex items-center justify-between relative z-10">
              <div className="flex items-center gap-3 min-w-0">
                {index < 3 ? (
                  <span className={cn(
                    "flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-gradient-to-br border text-xs font-bold",
                    RANK_COLORS[index],
                  )}>
                    {index === 0 ? <Trophy className="h-3.5 w-3.5" aria-label="First place" /> : item.rank}
                  </span>
                ) : (
                  <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-divider/50 text-xs font-medium text-text-secondary">
                    {item.rank}
                  </span>
                )}
                <span className={cn(
                  "truncate text-sm",
                  index === 0 ? "font-semibold text-text-primary" : "font-medium text-text-primary/80",
                )}>
                  {item.name}
                </span>
              </div>
              <span className={cn(
                "shrink-0 text-sm tabular-nums",
                index === 0 ? "font-bold text-accent" : "font-medium text-text-primary/80",
              )}>
                {formatCurrency(item.value)}
              </span>
            </div>
            <div
              className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-divider/50"
              role="progressbar"
              aria-valuenow={Math.round(item.pct_of_total)}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label={`${item.name}: ${Math.round(item.pct_of_total)}% of total`}
            >
              <div
                className="h-full rounded-full bg-gradient-to-r from-accent to-accent/40 transition-all duration-700"
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
  const { data: dashboardData, error, isLoading } = useDashboardData();

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      <RankingCard
        title="Top 5 Products"
        href="/products"
        items={dashboardData?.top_products?.items}
        isLoading={isLoading}
        error={error}
        icon={Package}
        accentColor="bg-accent/10 text-accent"
      />
      <RankingCard
        title="Top 5 Customers"
        href="/customers"
        items={dashboardData?.top_customers?.items}
        isLoading={isLoading}
        error={error}
        icon={Users}
        accentColor="bg-chart-blue/10 text-chart-blue"
      />
    </div>
  );
}
