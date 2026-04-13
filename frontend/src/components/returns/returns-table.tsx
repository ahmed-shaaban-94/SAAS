"use client";

import type { ReturnAnalysis } from "@/types/api";
import { formatCurrency, formatNumber } from "@/lib/formatters";
import { cn } from "@/lib/utils";

interface ReturnsTableProps {
  items: ReturnAnalysis[];
  className?: string;
}

export function ReturnsTable({ items, className }: ReturnsTableProps) {
  return (
    <div className={cn("max-h-[28rem] overflow-auto", className)}>
      <table className="w-full min-w-[540px] text-left text-sm" aria-label="Returns data">
        <thead className="sticky top-0 bg-card/95 backdrop-blur">
          <tr className="border-b border-border text-text-secondary">
            <th className="pb-3 pr-4 text-[11px] font-semibold uppercase tracking-[0.2em]">Brand</th>
            <th className="pb-3 pr-4 text-[11px] font-semibold uppercase tracking-[0.2em]">Customer</th>
            <th className="pb-3 pr-4 text-right text-[11px] font-semibold uppercase tracking-[0.2em]">Qty</th>
            <th className="pb-3 pr-4 text-right text-[11px] font-semibold uppercase tracking-[0.2em]">Amount</th>
            <th className="pb-3 text-right text-[11px] font-semibold uppercase tracking-[0.2em]">Count</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item, idx) => (
            <tr
              key={`${item.drug_brand}-${item.customer_name}-${idx}`}
              className="border-b border-divider/70 transition-colors hover:bg-white/5"
            >
              <td className="py-3 pr-4 font-medium text-text-primary">
                {item.drug_brand}
              </td>
              <td className="py-3 pr-4 text-text-secondary">
                {item.customer_name}
              </td>
              <td className="py-3 pr-4 text-right text-text-primary">
                {formatNumber(item.return_quantity)}
              </td>
              <td className="py-3 pr-4 text-right text-text-primary">
                {formatCurrency(item.return_amount)}
              </td>
              <td className="py-3 text-right text-text-primary">
                {formatNumber(item.return_count)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
