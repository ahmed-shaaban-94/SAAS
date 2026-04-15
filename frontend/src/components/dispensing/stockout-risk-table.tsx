"use client";

import { useStockoutRisk } from "@/hooks/use-stockout-risk";
import { LoadingCard } from "@/components/loading-card";
import { EmptyState } from "@/components/empty-state";
import { formatNumber } from "@/lib/formatters";
import { cn } from "@/lib/utils";
import type { StockoutRisk } from "@/types/dispensing";

const RISK_CONFIG: Record<
  StockoutRisk["risk_level"],
  { label: string; classes: string }
> = {
  stockout: { label: "Stockout", classes: "bg-red-500/15 text-red-400" },
  critical: { label: "Critical", classes: "bg-orange-500/15 text-orange-400" },
  at_risk: { label: "At Risk", classes: "bg-amber-500/15 text-amber-400" },
};

const RISK_ORDER: Record<StockoutRisk["risk_level"], number> = {
  stockout: 0,
  critical: 1,
  at_risk: 2,
};

export function StockoutRiskTable() {
  const { data, isLoading } = useStockoutRisk();

  if (isLoading) return <LoadingCard className="h-72" />;
  if (!data.length) {
    return (
      <EmptyState
        title="No stockout risks"
        description="All products have adequate stock levels."
      />
    );
  }

  const sorted = [...data].sort(
    (a, b) => RISK_ORDER[a.risk_level] - RISK_ORDER[b.risk_level],
  );

  return (
    <div className="overflow-x-auto rounded-xl border border-border">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border bg-muted/40">
            <th className="px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-text-secondary">
              Drug
            </th>
            <th className="px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-text-secondary">
              Site
            </th>
            <th className="px-4 py-3 text-right text-[11px] font-semibold uppercase tracking-wider text-text-secondary">
              Current Qty
            </th>
            <th className="px-4 py-3 text-right text-[11px] font-semibold uppercase tracking-wider text-text-secondary">
              Days Left
            </th>
            <th className="px-4 py-3 text-right text-[11px] font-semibold uppercase tracking-wider text-text-secondary">
              Suggested Reorder
            </th>
            <th className="px-4 py-3 text-center text-[11px] font-semibold uppercase tracking-wider text-text-secondary">
              Risk
            </th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((item) => {
            const config = RISK_CONFIG[item.risk_level];
            return (
              <tr
                key={`${item.product_key}-${item.site_code}`}
                className="border-b border-border/50 last:border-0 hover:bg-accent/5"
              >
                <td className="px-4 py-3">
                  <p className="font-medium text-text-primary">{item.drug_name}</p>
                  <p className="text-xs text-text-secondary">{item.drug_code}</p>
                </td>
                <td className="px-4 py-3 text-text-secondary">{item.site_code}</td>
                <td className="px-4 py-3 text-right">{formatNumber(item.current_quantity)}</td>
                <td className="px-4 py-3 text-right font-medium">
                  {item.days_of_stock != null ? `${item.days_of_stock.toFixed(1)}d` : "—"}
                </td>
                <td className="px-4 py-3 text-right text-text-secondary">
                  {formatNumber(item.suggested_reorder_qty)}
                </td>
                <td className="px-4 py-3 text-center">
                  <span
                    className={cn(
                      "rounded-full px-2.5 py-1 text-[11px] font-semibold",
                      config.classes,
                    )}
                  >
                    {config.label}
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
