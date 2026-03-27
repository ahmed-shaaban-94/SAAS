import { cn } from "@/lib/utils";
import { formatCurrency, formatPercent } from "@/lib/formatters";
import type { RankingItem } from "@/types/api";

interface RankingTableProps {
  items: RankingItem[];
  entityLabel: string;
  className?: string;
}

export function RankingTable({ items, entityLabel, className }: RankingTableProps) {
  return (
    <div className={cn("overflow-x-auto", className)}>
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-border text-text-secondary">
            <th className="pb-3 pr-4 font-medium">#</th>
            <th className="pb-3 pr-4 font-medium">{entityLabel}</th>
            <th className="pb-3 pr-4 text-right font-medium">Revenue</th>
            <th className="pb-3 text-right font-medium">% of Total</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr
              key={item.key}
              className="border-b border-divider transition-colors hover:bg-divider/50"
            >
              <td className="py-3 pr-4 text-text-secondary">{item.rank}</td>
              <td className="py-3 pr-4 font-medium text-text-primary">
                {item.name}
              </td>
              <td className="py-3 pr-4 text-right text-text-primary">
                {formatCurrency(item.value)}
              </td>
              <td className="py-3 text-right">
                <div className="flex items-center justify-end gap-2">
                  <div className="h-1.5 w-16 overflow-hidden rounded-full bg-divider">
                    <div
                      className="h-full rounded-full bg-accent"
                      style={{ width: `${Math.min(item.pct_of_total, 100)}%` }}
                    />
                  </div>
                  <span className="w-12 text-right text-text-secondary">
                    {item.pct_of_total.toFixed(1)}%
                  </span>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
