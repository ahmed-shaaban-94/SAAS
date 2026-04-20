"use client";

import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { TimeSeriesPoint } from "@/types/api";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export type KpiCardTone = "default" | "warning" | "danger";

export interface KpiCardProps {
  label: string;
  value: string;
  /** Percentage delta vs. previous period (omit to hide). */
  deltaPct?: number | null;
  /** Short secondary line, e.g. "MTD" or "4 batches". */
  sublabel?: string;
  sparkline?: TimeSeriesPoint[];
  tone?: KpiCardTone;
  icon?: LucideIcon;
  className?: string;
  /** Override the sparkline's aria-label for screen readers. */
  sparklineLabel?: string;
}

const TONE_CLASSES: Record<KpiCardTone, string> = {
  default: "",
  warning: "border-amber-500/25",
  danger: "border-red-500/25",
};

const SPARKLINE_STROKE: Record<KpiCardTone, string> = {
  default: "stroke-cyan-400",
  warning: "stroke-amber-400",
  danger: "stroke-red-400",
};

function DeltaBadge({ value }: { value: number }) {
  const isPositive = value > 0;
  const isZero = value === 0;
  const Icon = isZero ? Minus : isPositive ? TrendingUp : TrendingDown;
  const tone = isZero
    ? "text-text-secondary"
    : isPositive
      ? "text-cyan-300"
      : "text-red-300";
  const sign = isZero ? "" : isPositive ? "+" : "";
  return (
    <span
      className={cn(
        "inline-flex items-center gap-0.5 text-xs font-medium tabular-nums",
        tone,
      )}
    >
      <Icon aria-hidden="true" className="h-3 w-3" />
      <span>
        {sign}
        {value.toFixed(1)}%
      </span>
    </span>
  );
}

/**
 * Inline sparkline — tiny SVG polyline, no chart library.
 *
 * The viewBox is fixed 100×32 so the path stretches responsively inside
 * whatever container height the caller picks. Values are min-max
 * normalised so short series still fill the box.
 */
function Sparkline({
  points,
  stroke,
  ariaLabel,
}: {
  points: TimeSeriesPoint[];
  stroke: string;
  ariaLabel: string;
}) {
  if (!points.length) {
    return (
      <div
        aria-hidden="true"
        className="h-8 w-full rounded-sm bg-white/[0.025]"
      />
    );
  }
  const values = points.map((p) => Number(p.value));
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const stepX = points.length > 1 ? 100 / (points.length - 1) : 0;
  const path = values
    .map((v, i) => {
      const x = i * stepX;
      // Invert Y so higher values render closer to the top (y=0).
      const y = 32 - ((v - min) / span) * 32;
      return `${i === 0 ? "M" : "L"}${x.toFixed(2)},${y.toFixed(2)}`;
    })
    .join(" ");
  return (
    <svg
      role="img"
      aria-label={ariaLabel}
      viewBox="0 0 100 32"
      preserveAspectRatio="none"
      className="h-8 w-full"
    >
      <path
        d={path}
        fill="none"
        strokeWidth={1.5}
        strokeLinecap="round"
        strokeLinejoin="round"
        className={stroke}
      />
    </svg>
  );
}

/**
 * Single KPI tile for the dashboard KPI row (#503).
 *
 * Pure display — caller passes the formatted ``value`` string so this
 * component stays agnostic to currency / unit formatting rules.
 */
export function KpiCard({
  label,
  value,
  deltaPct,
  sublabel,
  sparkline,
  tone = "default",
  icon: Icon,
  className,
  sparklineLabel,
}: KpiCardProps) {
  return (
    <Card className={cn("flex flex-col", TONE_CLASSES[tone], className)}>
      <CardContent className="flex flex-col gap-3 p-4">
        <div className="flex items-start justify-between gap-2">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-text-secondary">
            {label}
          </span>
          {Icon && (
            <Icon
              aria-hidden="true"
              className="h-4 w-4 text-text-secondary"
            />
          )}
        </div>
        <div className="flex items-baseline justify-between gap-2">
          <span className="text-2xl font-semibold tabular-nums text-text-primary">
            {value}
          </span>
          {deltaPct != null && <DeltaBadge value={deltaPct} />}
        </div>
        {sublabel && (
          <span className="text-[11px] text-text-secondary">{sublabel}</span>
        )}
        <Sparkline
          points={sparkline ?? []}
          stroke={SPARKLINE_STROKE[tone]}
          ariaLabel={sparklineLabel ?? `${label} trend`}
        />
      </CardContent>
    </Card>
  );
}
