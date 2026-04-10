"use client";

import { memo } from "react";
import { TrendingUp, TrendingDown, AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";
import { useTopMovers } from "@/hooks/use-top-movers";
import { useActiveAnomalies } from "@/hooks/use-anomalies";
import { useFilters } from "@/contexts/filter-context";
import { formatPercent } from "@/lib/formatters";

interface InsightChipsProps {
  variant?: "default" | "print";
  className?: string;
}

interface Chip {
  type: "risk" | "opportunity" | "watch";
  label: string;
  icon: React.ComponentType<{ className?: string }>;
}

export const InsightChips = memo(function InsightChips({
  variant = "default",
  className,
}: InsightChipsProps) {
  const { filters } = useFilters();
  const { data: movers } = useTopMovers("product", filters);
  const { data: anomalies } = useActiveAnomalies(3);

  const chips: Chip[] = [];

  // Top gainer
  if (movers?.gainers?.[0]) {
    const g = movers.gainers[0];
    chips.push({
      type: "opportunity",
      label: `Top opportunity: ${g.name} ${formatPercent(g.change_pct)}`,
      icon: TrendingUp,
    });
  }

  // Top loser
  if (movers?.losers?.[0]) {
    const l = movers.losers[0];
    chips.push({
      type: "risk",
      label: `Top risk: ${l.name} ${formatPercent(l.change_pct)}`,
      icon: TrendingDown,
    });
  }

  // Anomalies
  if (anomalies?.length) {
    for (const a of anomalies.slice(0, 2)) {
      chips.push({
        type: "watch",
        label: `${a.metric} ${a.direction === "spike" ? "spike" : "drop"} detected`,
        icon: AlertTriangle,
      });
    }
  }

  if (chips.length === 0) return null;

  const isPrint = variant === "print";

  const colorMap = {
    risk: "bg-growth-red/10 text-growth-red border-growth-red/20",
    opportunity: "bg-growth-green/10 text-growth-green border-growth-green/20",
    watch: "bg-yellow-500/10 text-yellow-600 dark:text-yellow-400 border-yellow-500/20",
  } as const;

  return (
    <div className={cn("flex flex-wrap gap-2", className)}>
      {chips.map((chip, i) => {
        const Icon = chip.icon;
        return (
          <span
            key={chip.label}
            className={cn(
              "inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium",
              colorMap[chip.type],
              !isPrint && "transition-transform hover:scale-105",
            )}
          >
            <Icon className="h-3 w-3 shrink-0" />
            <span className="truncate max-w-[200px] sm:max-w-none">{chip.label}</span>
          </span>
        );
      })}
    </div>
  );
});
