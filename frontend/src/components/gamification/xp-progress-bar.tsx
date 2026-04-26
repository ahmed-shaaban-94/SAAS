"use client";

import { cn } from "@/lib/utils";
import { formatNumber } from "@/lib/formatters";

interface XPProgressBarProps {
  totalXP: number;
  xpToNext: number;
  level: number;
  className?: string;
}

export function XPProgressBar({ totalXP, xpToNext, level, className }: XPProgressBarProps) {
  const xpInCurrentLevel = xpToNext > 0 ? totalXP % (totalXP + xpToNext) : totalXP;
  const xpNeededForLevel = xpToNext > 0 ? xpInCurrentLevel + xpToNext : 1;
  const pct = xpToNext > 0 ? Math.min((xpInCurrentLevel / xpNeededForLevel) * 100, 100) : 100;

  return (
    <div className={cn("space-y-1", className)}>
      <div className="flex items-center justify-between text-xs text-text-secondary">
        <span>Level {level}</span>
        <span>{xpToNext > 0 ? `${formatNumber(xpToNext)} XP to next` : "MAX"}</span>
      </div>
      <div className="h-2 w-full rounded-full bg-divider overflow-hidden">
        <div
          className="h-full rounded-full bg-gradient-to-r from-accent to-chart-blue transition-all duration-500"
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="text-right text-[10px] text-text-secondary">
        {formatNumber(totalXP)} XP total
      </div>
    </div>
  );
}
