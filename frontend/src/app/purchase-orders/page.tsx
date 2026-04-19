"use client";

/**
 * /purchase-orders — v2 cutover. List + create modal on the shared
 * DashboardShell. Detail drill-down [po_number]/ stays in (app) for now.
 */

import { useState } from "react";
import { Plus, ShoppingCart } from "lucide-react";

import { DashboardShell } from "@/components/dashboard-v2/shell";
import { AnalyticsSectionHeader } from "@/components/layout/analytics-section-header";
import { POListTable } from "@/components/purchase-orders/po-list-table";
import { POCreateForm } from "@/components/purchase-orders/po-create-form";
import { usePurchaseOrders } from "@/hooks/use-purchase-orders";
import { LoadingCard } from "@/components/loading-card";
import { ErrorRetry } from "@/components/error-retry";
import { formatCurrency } from "@/lib/formatters";
import { cn } from "@/lib/utils";

const STATUS_TABS = [
  { label: "All", value: undefined },
  { label: "Draft", value: "draft" },
  { label: "Submitted", value: "submitted" },
  { label: "Partial", value: "partial" },
  { label: "Received", value: "received" },
  { label: "Cancelled", value: "cancelled" },
] as const;

export default function PurchaseOrdersPage() {
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined);
  const [showCreate, setShowCreate] = useState(false);
  const { data, error, isLoading } = usePurchaseOrders(statusFilter);

  const totalValue = data.reduce((s, po) => s + po.total_ordered_value, 0);
  const pendingCount = data.filter((po) =>
    ["draft", "submitted", "partial"].includes(po.status),
  ).length;

  return (
    <DashboardShell
      activeHref="/purchase-orders"
      breadcrumbs={[
        { label: "DataPulse", href: "/dashboard" },
        { label: "Operations" },
        { label: "Purchase orders" },
      ]}
    >
      <div className="page">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h1 className="page-title">Purchase orders.</h1>
            <p className="page-sub">
              Manage supplier purchase orders and track deliveries.
            </p>
          </div>
          <button
            onClick={() => setShowCreate(true)}
            className="flex items-center gap-2 rounded-xl bg-accent px-4 py-2 text-sm font-semibold text-black hover:bg-accent/90"
          >
            <Plus className="h-4 w-4" />
            New PO
          </button>
        </div>

        <div className="grid grid-cols-3 gap-4">
          <div className="rounded-xl border border-border bg-card p-4">
            <p className="text-xs font-semibold uppercase tracking-wider text-text-secondary">
              Total POs
            </p>
            <p className="mt-1 text-2xl font-bold text-text-primary">{data.length}</p>
          </div>
          <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-4">
            <p className="text-xs font-semibold uppercase tracking-wider text-text-secondary">
              Pending
            </p>
            <p className="mt-1 text-2xl font-bold text-amber-400">{pendingCount}</p>
          </div>
          <div className="rounded-xl border border-border bg-card p-4">
            <p className="text-xs font-semibold uppercase tracking-wider text-text-secondary">
              Total Value
            </p>
            <p className="mt-1 text-xl font-bold text-text-primary">
              {formatCurrency(totalValue)}
            </p>
          </div>
        </div>

        <div>
          <AnalyticsSectionHeader
            title="Order List"
            icon={ShoppingCart}
            accentClassName="text-accent"
          />

          <div className="mb-4 flex flex-wrap gap-1">
            {STATUS_TABS.map((tab) => (
              <button
                key={tab.label}
                onClick={() => setStatusFilter(tab.value)}
                className={cn(
                  "rounded-full px-3 py-1.5 text-xs font-semibold transition-colors",
                  statusFilter === tab.value
                    ? "bg-accent text-black"
                    : "bg-muted text-text-secondary hover:text-text-primary",
                )}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {isLoading ? (
            <LoadingCard lines={8} className="h-64" />
          ) : error ? (
            <ErrorRetry
              title="Failed to load purchase orders"
              description="Please try again."
            />
          ) : (
            <POListTable orders={data} />
          )}
        </div>

        <POCreateForm
          open={showCreate}
          onClose={() => setShowCreate(false)}
          onCreated={() => setShowCreate(false)}
        />
      </div>
    </DashboardShell>
  );
}
