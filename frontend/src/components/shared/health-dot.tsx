"use client";

import { cn } from "@/lib/utils";
import {
  getHealthLevel,
  getHealthDotClass,
  type HealthLevel,
} from "@/lib/health-thresholds";

interface HealthDotProps {
  /** Named metric (e.g. "revenue_growth") or direct level */
  metric?: string;
  value?: number | null;
  /** Provide directly if you already computed the level */
  level?: HealthLevel;
  className?: string;
  /** Show tooltip text */
  tooltip?: string;
}

/**
 * Small colored dot indicating health status (green/yellow/red).
 */
export function HealthDot({ metric, value, level: directLevel, className, tooltip }: HealthDotProps) {
  const level = directLevel ?? getHealthLevel(metric ?? "default", value);
  const dotClass = getHealthDotClass(level);

  return (
    <span
      className={cn("inline-block h-2 w-2 rounded-full shrink-0", dotClass, className)}
      title={tooltip ?? level}
      aria-label={`Health: ${level}`}
    />
  );
}
