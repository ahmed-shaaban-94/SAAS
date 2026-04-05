import { cn } from "@/lib/utils";
import { formatCurrency, formatCompact } from "@/lib/formatters";
import type { RankingItem } from "@/types/api";
import { Trophy, Medal, Award } from "lucide-react";
import { InlineSparkline } from "./inline-sparkline";

interface RankingTableProps {
  items: RankingItem[];
  entityLabel: string;
  /** Optional sparkline data keyed by item.key */
  sparklines?: Record<number, Array<{ value: number }>>;
  className?: string;
}

function RankBadge({ rank }: { rank: number }) {
  if (rank === 1) {
    return (
      <span className="flex h-7 w-7 items-center justify-center rounded-full bg-gradient-to-br from-chart-amber/30 to-chart-amber/10 shadow-sm shadow-chart-amber/10">
        <Trophy className="h-3.5 w-3.5 text-chart-amber" />
      </span>
    );
  }
  if (rank === 2) {
    return (
      <span className="flex h-7 w-7 items-center justify-center rounded-full bg-gradient-to-br from-text-secondary/20 to-text-secondary/5">
        <Medal className="h-3.5 w-3.5 text-text-secondary" />
      </span>
    );
  }
  if (rank === 3) {
    return (
      <span className="flex h-7 w-7 items-center justify-center rounded-full bg-gradient-to-br from-chart-amber/15 to-chart-amber/5">
        <Award className="h-3.5 w-3.5 text-chart-amber/70" />
      </span>
    );
  }
  return (
    <span className="flex h-7 w-7 items-center justify-center rounded-full bg-divider/50 text-[11px] font-semibold text-text-secondary">
      {rank}
    </span>
  );
}

export function RankingTable({ items, entityLabel, sparklines, className }: RankingTableProps) {
  const maxValue = items.length > 0 ? Math.max(...items.map((i) => i.value)) : 1;
  const hasSparklines = sparklines && Object.keys(sparklines).length > 0;

  return (
    <div className={cn("overflow-x-auto", className)}>
      <table className="w-full min-w-[500px] text-left text-[13px]" aria-label="Rankings data">
        <thead>
          <tr className="border-b border-border text-text-secondary">
            <th className="pb-2.5 pr-4 text-[11px] font-semibold uppercase tracking-wider">#</th>
            <th className="pb-2.5 pr-4 text-[11px] font-semibold uppercase tracking-wider">{entityLabel}</th>
            <th className="pb-2.5 pr-4 text-right text-[11px] font-semibold uppercase tracking-wider">Revenue</th>
            {hasSparklines && (
              <th className="pb-2.5 pr-4 text-center text-[11px] font-semibold uppercase tracking-wider">Trend</th>
            )}
            <th className="pb-2.5 text-right text-[11px] font-semibold uppercase tracking-wider">Share</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item, index) => {
            const barWidth = maxValue > 0 ? (item.value / maxValue) * 100 : 0;
            return (
              <tr
                key={item.key}
                className={cn(
                  "group/row border-b border-divider transition-all duration-200",
                  "hover:bg-accent/5",
                  index < 3 && "bg-accent/[0.02]",
                )}
              >
                <td className="py-3 pr-3">
                  <RankBadge rank={item.rank} />
                </td>
                <td className="py-3 pr-4 max-w-[220px]">
                  <div className="relative">
                    <span className={cn(
                      "relative z-10 block text-[13px] font-medium text-text-primary truncate",
                      index === 0 && "text-accent font-semibold",
                    )} title={item.name}>
                      {item.name}
                    </span>
                    {/* Background bar proportional to value */}
                    <div
                      className="absolute inset-y-0 left-0 -mx-2 rounded bg-accent/[0.04] transition-all duration-500 group-hover/row:bg-accent/[0.08]"
                      style={{ width: `${barWidth + 4}%` }}
                    />
                  </div>
                </td>
                <td className="py-3 pr-4 text-right whitespace-nowrap">
                  <span className="text-[13px] font-semibold text-text-primary" data-kpi-value>
                    {formatCurrency(item.value)}
                  </span>
                  <span className="ml-1 text-[10px] text-text-secondary hidden sm:inline">
                    ({formatCompact(item.value)})
                  </span>
                </td>
                {hasSparklines && (
                  <td className="py-3 pr-4 text-center">
                    <InlineSparkline data={sparklines[item.key]} />
                  </td>
                )}
                <td className="py-3 text-right">
                  <div className="flex items-center justify-end gap-2">
                    <div className="h-1.5 w-16 overflow-hidden rounded-full bg-divider">
                      <div
                        className={cn(
                          "h-full rounded-full transition-all duration-700",
                          index === 0
                            ? "bg-gradient-to-r from-accent to-chart-blue"
                            : index < 3
                              ? "bg-gradient-to-r from-accent to-accent/60"
                              : "bg-accent/50",
                        )}
                        style={{ width: `${Math.min(item.pct_of_total, 100)}%` }}
                      />
                    </div>
                    <span className="w-10 text-right text-[11px] font-semibold text-text-secondary tabular-nums">
                      {item.pct_of_total.toFixed(1)}%
                    </span>
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
