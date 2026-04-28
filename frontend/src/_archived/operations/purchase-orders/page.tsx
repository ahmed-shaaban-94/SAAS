"use client";

/**
 * /purchase-orders — PO list + create on the shared DashboardShell.
 *
 * Pharma Ops batch (Apr 2026): replaced the ad-hoc 3-tile stats block
 * with a proper 4-tile `KpiCard` grid (total POs, pending, value, fill
 * rate) matching the rest of the app. Detail drill-down
 * /purchase-orders/[po_number] stays in (app) for now.
 */

import { useMemo, useState } from "react";
import {
  Plus,
  ShoppingCart,
  ClipboardList,
  Clock,
  Banknote,
  CheckCircle2,
} from "lucide-react";

import { DashboardShell } from "@/components/dashboard-v2/shell";
import { AnalyticsSectionHeader } from "@/components/layout/analytics-section-header";
import { KpiCard, type KpiColor, type KpiDir } from "@/components/dashboard/new";
import { POListTable } from "@/components/purchase-orders/po-list-table";
import { POCreateForm } from "@/components/purchase-orders/po-create-form";
import { usePurchaseOrders } from "@/hooks/use-purchase-orders";
import { LoadingCard } from "@/components/loading-card";
import { ErrorRetry } from "@/components/error-retry";
import { formatCurrency, formatNumber } from "@/lib/formatters";
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

  const kpis = useMemo(() => {
    const totalValue = data.reduce((s, po) => s + po.total_ordered_value, 0);
    const totalReceived = data.reduce((s, po) => s + po.total_received_value, 0);
    const pendingCount = data.filter((po) =>
      ["draft", "submitted", "partial"].includes(po.status),
    ).length;
    const fillRate = totalValue > 0 ? (totalReceived / totalValue) * 100 : 0;

    return [
      {
        id: "total",
        label: "Total POs",
        value: formatNumber(data.length),
        delta: { dir: "up" as KpiDir, text: statusFilter ? `in ${statusFilter}` : "all statuses" },
        sub: "orders in current view",
        color: "accent" as KpiColor,
        sparkline: [] as number[],
        icon: ClipboardList,
      },
      {
        id: "pending",
        label: "Pending",
        value: formatNumber(pendingCount),
        delta: {
          dir: (pendingCount === 0 ? "up" : "down") as KpiDir,
          text: pendingCount === 0 ? "all received" : "awaiting delivery",
        },
        sub: "draft + submitted + partial",
        color: "amber" as KpiColor,
        sparkline: [] as number[],
        icon: Clock,
      },
      {
        id: "value",
        label: "Total Value",
        value: formatCurrency(totalValue),
        delta: { dir: "up" as KpiDir, text: `${formatCurrency(totalReceived)} received` },
        sub: "cumulative ordered value",
        color: "purple" as KpiColor,
        sparkline: [] as number[],
        icon: Banknote,
      },
      {
        id: "fill-rate",
        label: "Fill Rate",
        value: `${fillRate.toFixed(0)}%`,
        delta: {
          dir: (fillRate >= 90 ? "up" : "down") as KpiDir,
          text: fillRate >= 90 ? "strong" : "watch",
        },
        sub: "received ÷ ordered value",
        color: "red" as KpiColor,
        sparkline: [] as number[],
        icon: CheckCircle2,
      },
    ];
  }, [data, statusFilter]);

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

        <section
          className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4"
          aria-label="Purchase order KPIs"
        >
          {isLoading
            ? Array.from({ length: 4 }).map((_, i) => (
                <LoadingCard key={i} lines={3} className="h-[168px]" />
              ))
            : kpis.map((k) => (
                <KpiCard
                  key={k.id}
                  label={k.label}
                  value={k.value}
                  delta={k.delta}
                  sub={k.sub}
                  color={k.color}
                  sparkline={k.sparkline}
                  icon={k.icon}
                />
              ))}
        </section>

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
