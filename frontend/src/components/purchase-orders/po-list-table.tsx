"use client";

import Link from "next/link";
import { cn } from "@/lib/utils";
import { formatCurrency } from "@/lib/formatters";
import type { PurchaseOrder } from "@/types/purchase-orders";

const STATUS_CLASSES: Record<PurchaseOrder["status"], string> = {
  draft: "bg-gray-500/15 text-gray-400",
  submitted: "bg-blue-500/15 text-blue-400",
  partial: "bg-amber-500/15 text-amber-400",
  received: "bg-green-500/15 text-green-400",
  cancelled: "bg-red-500/15 text-red-400",
};

interface POListTableProps {
  orders: PurchaseOrder[];
}

export function POListTable({ orders }: POListTableProps) {
  if (orders.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-border/70 py-12 text-center text-sm text-muted-foreground">
        No purchase orders found.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-border">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border bg-muted/40">
            <th className="px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-text-secondary">
              PO Number
            </th>
            <th className="px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-text-secondary">
              Date
            </th>
            <th className="px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-text-secondary">
              Supplier
            </th>
            <th className="px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-text-secondary">
              Site
            </th>
            <th className="px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-text-secondary">
              Status
            </th>
            <th className="px-4 py-3 text-right text-[11px] font-semibold uppercase tracking-wider text-text-secondary">
              Value
            </th>
            <th className="px-4 py-3 text-center text-[11px] font-semibold uppercase tracking-wider text-text-secondary">
              Lines
            </th>
          </tr>
        </thead>
        <tbody>
          {orders.map((po) => (
            <tr
              key={po.po_number}
              className="border-b border-border/50 transition-colors last:border-0 hover:bg-accent/5"
            >
              <td className="px-4 py-3 font-medium">
                <Link
                  href={`/purchase-orders/${po.po_number}`}
                  className="text-accent hover:underline"
                >
                  {po.po_number}
                </Link>
              </td>
              <td className="px-4 py-3 text-text-secondary">
                {new Date(po.po_date).toLocaleDateString()}
              </td>
              <td className="px-4 py-3">{po.supplier_name}</td>
              <td className="px-4 py-3 text-text-secondary">{po.site_name}</td>
              <td className="px-4 py-3">
                <span
                  className={cn(
                    "rounded-full px-2.5 py-1 text-[11px] font-semibold capitalize",
                    STATUS_CLASSES[po.status],
                  )}
                >
                  {po.status}
                </span>
              </td>
              <td className="px-4 py-3 text-right font-medium">
                {formatCurrency(po.total_ordered_value)}
              </td>
              <td className="px-4 py-3 text-center text-text-secondary">
                {po.line_count}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
