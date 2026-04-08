"use client";

import { cn } from "@/lib/utils";
import { Flame } from "lucide-react";
import type { StreakResponse } from "@/hooks/use-gamification";

const STREAK_LABELS: Record<string, string> = {
  daily_target: "Daily Target",
  weekly_target: "Weekly Target",
  monthly_target: "Monthly Target",
  daily_sales: "Daily Sales",
  customer_growth: "Customer Growth",
};

interface StreakDisplayProps {
  streaks: StreakResponse[];
  className?: string;
}

export function StreakDisplay({ streaks, className }: StreakDisplayProps) {
  if (streaks.length === 0) {
    return (
      <div className={cn("rounded-xl border border-border bg-card p-4 text-center text-sm text-text-secondary", className)}>
        No active streaks yet. Start hitting your daily targets!
      </div>
    );
  }

  return (
    <div className={cn("grid gap-3 sm:grid-cols-2", className)}>
      {streaks.map((streak) => (
        <div
          key={streak.streak_type}
          className="flex items-center gap-3 rounded-xl border border-border bg-card p-4"
        >
          <div
            className={cn(
              "flex h-10 w-10 items-center justify-center rounded-full",
              streak.current_count >= 7 ? "bg-orange-500/15" : "bg-divider",
            )}
          >
            <Flame
              className={cn(
                "h-5 w-5",
                streak.current_count >= 30
                  ? "text-red-500"
                  : streak.current_count >= 7
                    ? "text-orange-400"
                    : "text-text-secondary",
              )}
            />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-text-primary">
              {STREAK_LABELS[streak.streak_type] || streak.streak_type}
            </p>
            <div className="flex items-center gap-3 text-xs text-text-secondary">
              <span>
                Current: <strong className="text-text-primary">{streak.current_count}</strong>
              </span>
              <span>
                Best: <strong className="text-text-primary">{streak.best_count}</strong>
              </span>
            </div>
          </div>
          {streak.current_count >= 7 && (
            <span className="text-lg font-bold text-orange-400">
              {streak.current_count}
            </span>
          )}
        </div>
      ))}
    </div>
  );
}
