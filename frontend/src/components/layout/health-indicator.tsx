"use client";

import { useHealth } from "@/hooks/use-health";
import { cn } from "@/lib/utils";

export function HealthIndicator() {
  const { data, error, isLoading } = useHealth();

  const isHealthy = data && !error;
  const statusText = isLoading
    ? "Checking..."
    : isHealthy
      ? "API Connected"
      : "API Offline";

  return (
    <div className="flex items-center gap-2">
      <span
        className={cn(
          "h-2 w-2 rounded-full",
          isLoading && "bg-chart-amber animate-pulse",
          !isLoading && isHealthy && "bg-accent",
          !isLoading && !isHealthy && "bg-growth-red",
        )}
      />
      <span className="text-xs text-text-secondary">{statusText}</span>
    </div>
  );
}
