import { cn } from "@/lib/utils";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";

interface KPICardProps {
  label: string;
  value: string;
  trend?: number | null;
  trendLabel?: string;
  icon?: React.ComponentType<{ className?: string }>;
  className?: string;
}

export function KPICard({ label, value, trend, trendLabel, icon: Icon, className }: KPICardProps) {
  const isPositive = trend !== null && trend !== undefined && trend > 0;
  const isNegative = trend !== null && trend !== undefined && trend < 0;

  const trendColor = isPositive
    ? "text-growth-green"
    : isNegative
      ? "text-growth-red"
      : "text-text-secondary";

  const TrendIcon = isPositive ? TrendingUp : isNegative ? TrendingDown : Minus;

  const accentBorderColor = isPositive
    ? "border-t-growth-green"
    : isNegative
      ? "border-t-growth-red"
      : "border-t-accent";

  const pillBg = isPositive
    ? "bg-growth-green/10 text-growth-green"
    : isNegative
      ? "bg-growth-red/10 text-growth-red"
      : "bg-text-secondary/10 text-text-secondary";

  return (
    <div
      className={cn(
        "glow-card rounded-lg border border-border border-t-2 bg-card p-5",
        "transition-all duration-300 hover:scale-[1.02]",
        accentBorderColor,
        className,
      )}
    >
      <div className="flex items-start justify-between">
        <p className="text-xs font-semibold uppercase tracking-wide text-text-secondary">
          {label}
        </p>
        {Icon && (
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-accent/10">
            <Icon className="h-4 w-4 text-accent" />
          </div>
        )}
      </div>

      <p className="mt-3 text-3xl font-bold tracking-tight text-text-primary">{value}</p>

      {trend !== undefined && (
        <div className="mt-3 flex items-center gap-2">
          <span
            className={cn(
              "inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold",
              pillBg,
            )}
          >
            <TrendIcon className="h-3.5 w-3.5" />
            {trend !== null ? `${isPositive ? "+" : ""}${trend.toFixed(1)}%` : "N/A"}
          </span>
          {trendLabel && (
            <span className="text-xs text-text-secondary">{trendLabel}</span>
          )}
        </div>
      )}
    </div>
  );
}
