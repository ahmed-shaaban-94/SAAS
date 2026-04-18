"use client";

import { formatCurrency, formatNumber } from "@/lib/formatters";
import type { POLine } from "@/types/purchase-orders";

interface POLineItemsProps {
  lines: POLine[];
}

export function POLineItems({ lines }: POLineItemsProps) {
  if (lines.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-border/70 py-8 text-center text-sm text-muted-foreground">
        No line items found.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-border">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border bg-muted/40">
            <th className="px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-text-secondary">
              #
            </th>
            <th className="px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-text-secondary">
              Drug
            </th>
            <th className="px-4 py-3 text-right text-[11px] font-semibold uppercase tracking-wider text-text-secondary">
              Ordered
            </th>
            <th className="px-4 py-3 text-right text-[11px] font-semibold uppercase tracking-wider text-text-secondary">
              Unit Price
            </th>
            <th className="px-4 py-3 text-right text-[11px] font-semibold uppercase tracking-wider text-text-secondary">
              Received
            </th>
            <th className="px-4 py-3 text-right text-[11px] font-semibold uppercase tracking-wider text-text-secondary">
              Line Total
            </th>
            <th className="w-40 px-4 py-3 text-center text-[11px] font-semibold uppercase tracking-wider text-text-secondary">
              Fulfillment
            </th>
          </tr>
        </thead>
        <tbody>
          {lines.map((line) => (
            <tr
              key={line.line_number}
              className="border-b border-border/50 last:border-0 hover:bg-accent/5"
            >
              <td className="px-4 py-3 text-text-secondary">{line.line_number}</td>
              <td className="px-4 py-3">
                <p className="font-medium text-text-primary">{line.drug_name}</p>
                <p className="text-xs text-text-secondary">{line.drug_code}</p>
              </td>
              <td className="px-4 py-3 text-right">
                {formatNumber(line.ordered_quantity)}
              </td>
              <td className="px-4 py-3 text-right">
                {formatCurrency(line.unit_price)}
              </td>
              <td className="px-4 py-3 text-right">
                {formatNumber(line.received_quantity)}
              </td>
              <td className="px-4 py-3 text-right font-medium">
                {formatCurrency(line.line_total)}
              </td>
              <td className="px-4 py-3">
                <div className="flex items-center gap-2">
                  <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-muted">
                    <div
                      className="h-full rounded-full bg-green-500 transition-all"
                      style={{ width: `${Math.min(100, line.fulfillment_pct)}%` }}
                    />
                  </div>
                  <span className="w-10 text-right text-xs text-text-secondary">
                    {line.fulfillment_pct.toFixed(0)}%
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
