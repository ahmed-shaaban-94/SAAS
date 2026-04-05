import Link from "next/link";
import { cn } from "@/lib/utils";
import { formatCurrency } from "@/lib/formatters";
import type { RankingItem } from "@/types/api";
import { InlineSparkline } from "./inline-sparkline";

interface RankingTableLinkedProps {
  items: RankingItem[];
  entityLabel: string;
  hrefPrefix?: string;
  /** Optional sparkline data keyed by item.key */
  sparklines?: Record<number, Array<{ value: number }>>;
  className?: string;
}

export function RankingTableLinked({
  items,
  entityLabel,
  hrefPrefix,
  sparklines,
  className,
}: RankingTableLinkedProps) {
  const hasSparklines = sparklines && Object.keys(sparklines).length > 0;

  return (
    <div className={cn("overflow-x-auto", className)}>
      <table className="w-full min-w-[500px] text-left text-sm">
        <thead>
          <tr className="border-b border-border text-text-secondary">
            <th className="pb-3 pr-4 font-medium">#</th>
            <th className="pb-3 pr-4 font-medium">{entityLabel}</th>
            <th className="pb-3 pr-4 text-right font-medium">Revenue</th>
            {hasSparklines && (
              <th className="pb-3 pr-4 text-center font-medium">Trend</th>
            )}
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
                {hrefPrefix ? (
                  <Link
                    href={`${hrefPrefix}/${item.key}`}
                    className="hover:text-accent transition-colors"
                  >
                    {item.name}
                  </Link>
                ) : (
                  item.name
                )}
              </td>
              <td className="py-3 pr-4 text-right text-text-primary">
                {formatCurrency(item.value)}
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
