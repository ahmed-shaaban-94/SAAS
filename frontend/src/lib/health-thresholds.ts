/**
 * Color-coded health indicator logic.
 *
 * Maps metric values to green/yellow/red based on configurable thresholds.
 */

export type HealthLevel = "good" | "warning" | "critical";

interface ThresholdConfig {
  /** Above this = good (green) */
  goodAbove: number;
  /** Below this = critical (red). Between = warning (yellow) */
  criticalBelow: number;
  /** If true, lower is better (e.g. return rate) */
  invertDirection?: boolean;
}

const METRIC_THRESHOLDS: Record<string, ThresholdConfig> = {
  // Growth metrics — positive growth is good
  revenue_growth: { goodAbove: 5, criticalBelow: -5 },
  transaction_growth: { goodAbove: 3, criticalBelow: -3 },
  customer_growth: { goodAbove: 2, criticalBelow: -5 },

  // Rate metrics — lower is better
  return_rate: { goodAbove: 3, criticalBelow: 8, invertDirection: true },
  churn_rate: { goodAbove: 5, criticalBelow: 15, invertDirection: true },

  // Absolute metrics
  margin_pct: { goodAbove: 30, criticalBelow: 15 },
  avg_order_value: { goodAbove: 100, criticalBelow: 50 },
};

/** Default thresholds for generic percentage trends */
const DEFAULT_THRESHOLD: ThresholdConfig = {
  goodAbove: 0,
  criticalBelow: -10,
};

export function getHealthLevel(
  metric: string,
  value: number | null | undefined,
): HealthLevel {
  if (value === null || value === undefined) return "warning";

  const config = METRIC_THRESHOLDS[metric] ?? DEFAULT_THRESHOLD;

  if (config.invertDirection) {
    // Lower is better: below goodAbove = good, above criticalBelow = critical
    if (value <= config.goodAbove) return "good";
    if (value >= config.criticalBelow) return "critical";
    return "warning";
  }

  // Higher is better
  if (value >= config.goodAbove) return "good";
  if (value <= config.criticalBelow) return "critical";
  return "warning";
}

export function getHealthColor(level: HealthLevel): string {
  switch (level) {
    case "good":
      return "var(--growth-green)";
    case "warning":
      return "var(--chart-amber)";
    case "critical":
      return "var(--growth-red)";
  }
}

/** Tailwind class for the health dot */
export function getHealthDotClass(level: HealthLevel): string {
  switch (level) {
    case "good":
      return "bg-growth-green";
    case "warning":
      return "bg-chart-amber";
    case "critical":
      return "bg-growth-red";
  }
}
