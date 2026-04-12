"use client";

import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import { formatCurrency, formatNumber } from "@/lib/formatters";
import { cn } from "@/lib/utils";

interface ComparisonKPIProps {
  label: string;
  currentValue: number;
  previousValue: number;
  isCurrency?: boolean;
}

export function ComparisonKPI({ label, currentValue, previousValue, isCurrency }: ComparisonKPIProps) {
  const delta = previousValue !== 0
    ? ((currentValue - previousValue) / previousValue) * 100
    : null;
  const isPositive = delta !== null && delta > 0;
  const isNegative = delta !== null && delta < 0;
  const isNew = previousValue === 0 && currentValue > 0;
  const fmt = isCurrency ? formatCurrency : formatNumber;
  const TrendIcon = isPositive ? TrendingUp : isNegative ? TrendingDown : Minus;

  return (
    <div className="rounded-xl border border-border bg-card/80 p-4">
      <p className="text-[10px] font-semibold uppercase tracking-wider text-text-secondary">
        {label}
      </p>
      <div className="mt-1 flex items-baseline gap-2">
        <span className="text-lg font-bold text-text-primary">{fmt(currentValue)}</span>
        <span className="text-xs text-text-secondary">vs {fmt(previousValue)}</span>
      </div>
      <div className="mt-1.5 flex items-center gap-1">
        <TrendIcon
          className={cn(
            "h-3 w-3",
            isPositive ? "text-growth-green" : isNegative ? "text-growth-red" : "text-text-secondary",
          )}
        />
        <span
          className={cn(
            "text-xs font-semibold",
            isPositive ? "text-growth-green" : isNegative ? "text-growth-red" : "text-text-secondary",
          )}
        >
          {isNew ? "New" : delta !== null ? `${isPositive ? "+" : ""}${delta.toFixed(1)}%` : "N/A"}
        </span>
      </div>
    </div>
  );
}
