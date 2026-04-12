"use client";

import { memo } from "react";
import { formatCurrency } from "@/lib/formatters";
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
    <div className="viz-panel mb-6 rounded-[1.8rem] px-6 py-5">
      <div className="absolute inset-x-6 top-0 h-1 rounded-b-full bg-gradient-to-r from-chart-blue via-accent to-chart-purple" />
      <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-text-secondary">
        Today&apos;s snapshot
      </p>
      <p className="mt-3 text-lg font-semibold leading-8 text-text-primary sm:text-[1.65rem]">
        <span className="text-accent">{formatCurrency(revenue)}</span>
        {" "}across{" "}
        <span className="font-bold">{transactions?.toLocaleString() ?? "—"}</span>
        {" "}transactions
        {trendWord && momGrowth !== null && momGrowth !== undefined && (
          <span className={`ml-2 inline-flex items-center gap-1 rounded-full px-3 py-1 text-sm ${trendColor} viz-panel-soft`}>
            <TrendIcon className="h-4 w-4" />
            <span className="text-sm font-medium">
              {Math.abs(momGrowth).toFixed(1)}% vs prev period
            </span>
          </span>
        )}
      </p>
    </div>
  );
});
