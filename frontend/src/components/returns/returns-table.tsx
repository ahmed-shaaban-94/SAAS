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
      <table className="w-full text-left text-sm">
        <thead className="sticky top-0 bg-card">
          <tr className="border-b border-border text-text-secondary">
            <th className="pb-3 pr-4 font-medium">Drug Name</th>
            <th className="pb-3 pr-4 font-medium">Customer</th>
            <th className="pb-3 pr-4 text-right font-medium">Qty</th>
            <th className="pb-3 pr-4 text-right font-medium">Amount</th>
            <th className="pb-3 text-right font-medium">Count</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item, idx) => (
            <tr
              key={`${item.drug_name}-${item.customer_name}-${idx}`}
              className="border-b border-divider transition-colors hover:bg-divider/50"
            >
              <td className="py-3 pr-4 font-medium text-text-primary">
                {item.drug_name}
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
