"use client";

import { memo, useEffect, useId, useRef } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { AreaChart, Area, ResponsiveContainer } from "recharts";
import { cn } from "@/lib/utils";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import { MetricTooltip } from "@/components/shared/metric-tooltip";
import { WhyChangedTrigger } from "@/components/why-changed/why-changed-trigger";
import type { WhyChangedData } from "@/components/why-changed/why-changed";
import type { TimeSeriesPoint } from "@/types/api";

interface KPICardProps {
  label: string;
  value: string;
  numericValue?: number;
  isCurrency?: boolean;
  isPercent?: boolean;
  isDecimal?: boolean;
  trend?: number | null;
  trendLabel?: string;
  subtitle?: string;
  comparisonLine?: string;
  hero?: boolean;
  icon?: React.ComponentType<{ className?: string }>;
  className?: string;
  accentGradient?: string;
  sparkline?: TimeSeriesPoint[];
  tooltip?: string;
  /** Optional Why-Changed decomposition — when present, the value becomes
   *  clickable and opens a waterfall modal showing the drivers. */
  whyChanged?: WhyChangedData;
  "aria-label"?: string;
}

function formatValue(n: number, decimals: number, suffix: string): string {
  const fixed = n.toFixed(decimals);
  const [intPart, decPart] = fixed.split(".");
  const formatted = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  return (decPart !== undefined ? `${formatted}.${decPart}` : formatted) + suffix;
}

const isDigitChar = (ch: string) => ch >= "0" && ch <= "9";

const AnimatedValue = memo(function AnimatedValue({ value, numericValue, isCurrency, isPercent, isDecimal }: {
  value: string;
  numericValue?: number;
  isCurrency?: boolean;
  isPercent?: boolean;
  isDecimal?: boolean;
}) {
  const reducedMotion = useReducedMotion();
  const decimals = isPercent ? 1 : isDecimal ? 2 : 0;
  const suffix = isCurrency ? " EGP" : isPercent ? "%" : "";
  const prevFormattedRef = useRef<string>("");

  const formatted =
    numericValue !== undefined && numericValue !== null
      ? formatValue(numericValue, decimals, suffix)
      : "";

  useEffect(() => {
    if (formatted) {
      prevFormattedRef.current = formatted;
    }
  });

  if (numericValue === undefined || numericValue === null) {
    return <>{value}</>;
  }

  if (reducedMotion) {
    return <>{formatted}</>;
  }

  const prev = prevFormattedRef.current;
  const chars = formatted.split("");

  return (
    <span style={{ display: "inline-flex", alignItems: "baseline", overflow: "visible" }}>
      {chars.map((char, i) => {
        const prevChar = prev[i];
        const changed = prevChar !== undefined && prevChar !== char;
        const isDigit = isDigitChar(char);

        return (
          <span
            key={i}
            style={{
              display: "inline-block",
              overflow: "hidden",
              lineHeight: "1.2em",
              verticalAlign: "bottom",
            }}
          >
            <AnimatePresence mode="wait" initial={false}>
              <motion.span
                key={char + String(i)}
                initial={changed && isDigit ? { y: 20, opacity: 0 } : { opacity: changed ? 0 : 1 }}
                animate={{ y: 0, opacity: 1 }}
                exit={isDigit ? { y: -20, opacity: 0 } : { opacity: 0 }}
                transition={{ type: "spring", stiffness: 300, damping: 25 }}
                style={{ display: "inline-block" }}
              >
                {char}
              </motion.span>
            </AnimatePresence>
          </span>
        );
      })}
    </span>
  );
});

export const KPICard = memo(function KPICard({ label, value, numericValue, isCurrency, isPercent, isDecimal, trend, trendLabel, subtitle, comparisonLine, hero, icon: Icon, className, accentGradient, sparkline, tooltip, whyChanged, "aria-label": ariaLabel }: KPICardProps) {
  const sparkId = useId();
  const isPositive = trend !== null && trend !== undefined && trend > 0;
  const isNegative = trend !== null && trend !== undefined && trend < 0;

  const trendOpacity = trend !== null && trend !== undefined
    ? Math.min(Math.abs(trend) * 3, 100) / 100
    : 0.1;

  const pillBg = isPositive
    ? "text-growth-green"
    : isNegative
      ? "text-growth-red"
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
      aria-label={ariaLabel}
      className={cn(
        "viz-panel viz-card-hover group relative overflow-hidden rounded-[1.6rem] border border-border/80 p-4 sm:p-5",
        hero && "border-accent/30 shadow-[0_20px_80px_rgba(0,199,242,0.16)]",
        className,
      )}
    >
      <div className={cn(
        "absolute inset-x-5 top-0 h-1 rounded-b-full bg-gradient-to-r transition-all duration-300 group-hover:h-1.5",
        isPositive ? "from-growth-green to-growth-green/50" :
        isNegative ? "from-growth-red to-growth-red/50" :
        "from-chart-blue via-accent to-chart-purple"
      )} />

      <div className={cn(
        "absolute -right-6 -top-6 h-28 w-28 rounded-full bg-gradient-to-br opacity-0 blur-2xl transition-opacity duration-500 group-hover:opacity-100",
        gradient,
      )} />

      <div className="relative flex items-start justify-between gap-3">
        <div className="flex items-center gap-1.5">
          <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-text-secondary/90">
            {label}
          </p>
          {tooltip && <MetricTooltip description={tooltip} />}
        </div>
        {Icon && (
          <div className="viz-panel-soft flex h-9 w-9 items-center justify-center rounded-xl transition-all duration-300 group-hover:bg-accent/12 sm:h-10 sm:w-10">
            <Icon className="h-4 w-4 text-accent" />
          </div>
        )}
      </div>

      <p className={cn(
        "relative mt-3 font-bold tracking-tight text-text-primary truncate",
        hero ? "text-[1.85rem] sm:text-[2.2rem]" : "text-xl sm:text-2xl",
      )} data-kpi-value>
        {whyChanged ? (
          <WhyChangedTrigger data={whyChanged} inline>
            <AnimatedValue
              value={value}
              numericValue={numericValue}
              isCurrency={isCurrency}
              isPercent={isPercent}
              isDecimal={isDecimal}
            />
          </WhyChangedTrigger>
        ) : (
          <AnimatedValue
            value={value}
            numericValue={numericValue}
            isCurrency={isCurrency}
            isPercent={isPercent}
            isDecimal={isDecimal}
          />
        )}
      </p>

      {subtitle && (
        <p className="relative mt-1 text-[11px] text-text-secondary truncate">{subtitle}</p>
      )}

      {comparisonLine && (
        <p className={cn(
          "relative mt-1.5 text-xs font-medium truncate",
          isPositive ? "text-growth-green/80" : isNegative ? "text-growth-red/80" : "text-text-secondary",
        )}>
          {comparisonLine}
        </p>
      )}

      {trend !== undefined && (
        <div className="relative mt-2 flex items-center gap-1.5">
          <span
            className={cn(
              "inline-flex items-center gap-0.5 rounded-full px-2.5 py-1 text-[11px] font-semibold",
              "transition-all duration-300 group-hover:scale-105",
              pillBg,
            )}
            style={isPositive || isNegative ? {
              backgroundColor: isPositive
                ? `rgba(var(--growth-green-rgb, 5, 150, 105), ${trendOpacity})`
                : `rgba(var(--growth-red-rgb, 220, 38, 38), ${trendOpacity})`,
            } : undefined}
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
        <div className="viz-panel-soft relative mt-3 rounded-2xl px-2 py-1.5">
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
                strokeWidth={1.9}
                fill={`url(#${sparkId})`}
                className="text-chart-blue"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
});
