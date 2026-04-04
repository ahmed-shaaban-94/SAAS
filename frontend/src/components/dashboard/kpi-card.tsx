"use client";

import { useId } from "react";
import { AreaChart, Area, ResponsiveContainer } from "recharts";
import { cn } from "@/lib/utils";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import { useCountUp } from "@/hooks/use-count-up";
import { MetricTooltip } from "@/components/shared/metric-tooltip";
import type { TimeSeriesPoint } from "@/types/api";

interface KPICardProps {
  label: string;
  value: string;
  numericValue?: number;
  isCurrency?: boolean;
  isPercent?: boolean;
  trend?: number | null;
  trendLabel?: string;
  subtitle?: string;
  icon?: React.ComponentType<{ className?: string }>;
  className?: string;
  accentGradient?: string;
  sparkline?: TimeSeriesPoint[];
  tooltip?: string;
}

function AnimatedValue({ value, numericValue, isCurrency, isPercent }: {
  value: string;
  numericValue?: number;
  isCurrency?: boolean;
  isPercent?: boolean;
}) {
  const animated = useCountUp({
    end: numericValue ?? 0,
    duration: 1400,
    decimals: isPercent ? 1 : 0,
    prefix: "",
    suffix: isCurrency ? " EGP" : isPercent ? "%" : "",
    separator: ",",
  });

  if (numericValue === undefined || numericValue === null) {
    return <>{value}</>;
  }

  return <>{animated}</>;
}

export function KPICard({ label, value, numericValue, isCurrency, isPercent, trend, trendLabel, subtitle, icon: Icon, className, accentGradient, sparkline, tooltip }: KPICardProps) {
  const sparkId = useId();
  const isPositive = trend !== null && trend !== undefined && trend > 0;
  const isNegative = trend !== null && trend !== undefined && trend < 0;

  const pillBg = isPositive
    ? "bg-growth-green/10 text-growth-green"
    : isNegative
      ? "bg-growth-red/10 text-growth-red"
      : "bg-text-secondary/10 text-text-secondary";

  const defaultGradient = isPositive
    ? "from-growth-green/20 to-transparent"
    : isNegative
      ? "from-growth-red/20 to-transparent"
      : "from-accent/20 to-transparent";

  const gradient = accentGradient || defaultGradient;

  const TrendIcon = isPositive ? TrendingUp : isNegative ? TrendingDown : Minus;

  return (
    <div
      className={cn(
        "group relative overflow-hidden rounded-xl border border-border p-4 sm:p-5",
        // Glass morphism
        "bg-card/80 backdrop-blur-sm",
        "transition-all duration-300 hover:scale-[1.03] hover:shadow-lg",
        "hover:border-accent/40 hover:shadow-accent/5",
        className,
      )}
    >
      {/* Gradient accent strip at top */}
      <div className={cn(
        "absolute inset-x-0 top-0 h-1 bg-gradient-to-r transition-all duration-300 group-hover:h-1.5",
        isPositive ? "from-growth-green to-growth-green/50" :
        isNegative ? "from-growth-red to-growth-red/50" :
        "from-accent to-accent/50"
      )} />

      {/* Background glow on hover */}
      <div className={cn(
        "absolute -right-4 -top-4 h-24 w-24 rounded-full bg-gradient-to-br opacity-0 blur-2xl transition-opacity duration-500 group-hover:opacity-100",
        gradient,
      )} />

      <div className="relative flex items-start justify-between">
        <div className="flex items-center gap-1.5">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-text-secondary">
            {label}
          </p>
          {tooltip && <MetricTooltip description={tooltip} />}
        </div>
        {Icon && (
          <div className="flex h-8 w-8 sm:h-9 sm:w-9 items-center justify-center rounded-lg bg-accent/10 transition-all duration-300 group-hover:bg-accent/20 group-hover:scale-110 group-hover:rotate-3">
            <Icon className="h-4 w-4 text-accent" />
          </div>
        )}
      </div>

      <p className="relative mt-2 text-lg sm:text-xl font-bold tracking-tight text-text-primary truncate" data-kpi-value>
        <AnimatedValue
          value={value}
          numericValue={numericValue}
          isCurrency={isCurrency}
          isPercent={isPercent}
        />
      </p>

      {subtitle && (
        <p className="relative mt-0.5 text-[10px] text-text-secondary truncate">{subtitle}</p>
      )}

      {trend !== undefined && (
        <div className="relative mt-2 flex items-center gap-1.5">
          <span
            className={cn(
              "inline-flex items-center gap-0.5 rounded-full px-2 py-0.5 text-[11px] font-semibold",
              "transition-all duration-300 group-hover:scale-105",
              pillBg,
            )}
          >
            <TrendIcon className="h-3 w-3" />
            {trend !== null ? `${isPositive ? "+" : ""}${trend.toFixed(1)}%` : "N/A"}
          </span>
          {trendLabel && (
            <span className="text-[10px] text-text-secondary hidden sm:inline">{trendLabel}</span>
          )}
        </div>
      )}

      {sparkline && sparkline.length > 1 && (
        <div className="relative mt-2 h-7">
          <ResponsiveContainer width="100%" height={28}>
            <AreaChart data={sparkline.map((p) => ({ v: p.value }))}>
              <defs>
                <linearGradient id={sparkId} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="currentColor" stopOpacity={0.3} />
                  <stop offset="100%" stopColor="currentColor" stopOpacity={0} />
                </linearGradient>
              </defs>
              <Area
                type="monotone"
                dataKey="v"
                stroke="currentColor"
                strokeWidth={1.5}
                fill={`url(#${sparkId})`}
                className="text-accent"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
