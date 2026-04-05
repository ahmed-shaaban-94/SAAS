"use client";

import { memo } from "react";
import { formatCurrency, formatPercent } from "@/lib/formatters";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";

interface DayHeroProps {
  revenue?: number;
  transactions?: number;
  momGrowth?: number | null;
}

export const DayHero = memo(function DayHero({ revenue, transactions, momGrowth }: DayHeroProps) {
  if (!revenue) return null;

  const trendWord = momGrowth !== null && momGrowth !== undefined
    ? momGrowth > 0 ? "up" : momGrowth < 0 ? "down" : "flat"
    : null;

  const TrendIcon = trendWord === "up" ? TrendingUp : trendWord === "down" ? TrendingDown : Minus;
  const trendColor = trendWord === "up" ? "text-growth-green" : trendWord === "down" ? "text-growth-red" : "text-text-secondary";

  return (
    <div className="mb-6 rounded-xl border border-border bg-card/50 backdrop-blur-sm px-6 py-4">
      <p className="text-sm text-text-secondary">
        Today&apos;s snapshot
      </p>
      <p className="mt-1 text-lg font-semibold text-text-primary">
        <span className="text-accent">{formatCurrency(revenue)}</span>
        {" "}across{" "}
        <span className="font-bold">{transactions?.toLocaleString() ?? "—"}</span>
        {" "}transactions
        {trendWord && momGrowth !== null && momGrowth !== undefined && (
          <span className={`ml-2 inline-flex items-center gap-1 ${trendColor}`}>
            <TrendIcon className="h-4 w-4" />
            <span className="text-sm font-medium">
              {formatPercent(Math.abs(momGrowth))} vs last month
            </span>
          </span>
        )}
      </p>
    </div>
  );
});
