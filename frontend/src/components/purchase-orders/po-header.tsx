"use client";

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

interface POHeaderProps {
  po: PurchaseOrder;
}

export function POHeader({ po }: POHeaderProps) {
  return (
    <div className="rounded-xl border border-border bg-card p-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="grid grid-cols-2 gap-x-8 gap-y-3 text-sm sm:grid-cols-3 lg:grid-cols-5">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-wider text-text-secondary">
              Supplier
            </p>
            <p className="mt-0.5 font-medium text-text-primary">{po.supplier_name}</p>
            <p className="text-xs text-text-secondary">{po.supplier_code}</p>
          </div>
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-wider text-text-secondary">
              Site
            </p>
            <p className="mt-0.5 font-medium text-text-primary">{po.site_name}</p>
            <p className="text-xs text-text-secondary">{po.site_code}</p>
          </div>
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-wider text-text-secondary">
              PO Date
            </p>
            <p className="mt-0.5 font-medium text-text-primary">
              {new Date(po.po_date).toLocaleDateString()}
            </p>
          </div>
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-wider text-text-secondary">
              Expected
            </p>
            <p className="mt-0.5 font-medium text-text-primary">
              {po.expected_date ? new Date(po.expected_date).toLocaleDateString() : "—"}
            </p>
          </div>
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-wider text-text-secondary">
              Total Value
            </p>
            <p className="mt-0.5 font-medium text-text-primary">
              {formatCurrency(po.total_ordered_value)}
            </p>
            {po.total_received_value > 0 && (
              <p className="text-xs text-green-400">
                {formatCurrency(po.total_received_value)} received
              </p>
            )}
          </div>
        </div>

        <span
          className={cn(
            "rounded-full px-3 py-1.5 text-xs font-semibold capitalize",
            STATUS_CLASSES[po.status],
          )}
        >
          {po.status}
        </span>
      </div>
    </div>
  );
}
