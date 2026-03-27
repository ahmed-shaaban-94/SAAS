import { cn } from "@/lib/utils";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";

interface KPICardProps {
  label: string;
  value: string;
  trend?: number | null;
  trendLabel?: string;
  className?: string;
}

export function KPICard({ label, value, trend, trendLabel, className }: KPICardProps) {
  const trendColor =
    trend === null || trend === undefined
      ? "text-text-secondary"
      : trend > 0
        ? "text-growth-green"
        : trend < 0
          ? "text-growth-red"
          : "text-text-secondary";

  const TrendIcon =
    trend === null || trend === undefined
      ? Minus
      : trend > 0
        ? TrendingUp
        : trend < 0
          ? TrendingDown
          : Minus;

  return (
    <div
      className={cn(
        "rounded-lg border border-border bg-card p-5 transition-colors hover:border-accent/30",
        className,
      )}
    >
      <p className="text-sm font-medium text-text-secondary">{label}</p>
      <p className="mt-2 text-2xl font-bold text-text-primary">{value}</p>
      {trend !== undefined && (
        <div className={cn("mt-2 flex items-center gap-1 text-sm", trendColor)}>
          <TrendIcon className="h-4 w-4" />
          <span>
            {trend !== null ? `${trend > 0 ? "+" : ""}${trend.toFixed(1)}%` : "N/A"}
          </span>
          {trendLabel && (
            <span className="text-text-secondary"> {trendLabel}</span>
          )}
        </div>
      )}
    </div>
  );
}
