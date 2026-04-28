"use client";

/**
 * /purchase-orders/[po_number] — single PO drill-down on the v2 shell.
 */

import Link from "next/link";
import { useMemo } from "react";
import { useParams } from "next/navigation";
import {
  ArrowLeft,
  List,
  Banknote,
  PackageCheck,
  ClipboardList,
  Target,
} from "lucide-react";

import { usePODetail } from "@/hooks/use-po-detail";
import { DashboardShell } from "@/components/dashboard-v2/shell";
import { KpiCard, type KpiColor, type KpiDir } from "@/components/dashboard/new";
import { AnalyticsSectionHeader } from "@/components/layout/analytics-section-header";
import { POStatusPipeline } from "@/components/purchase-orders/po-status-pipeline";
import { POHeader } from "@/components/purchase-orders/po-header";
import { POLineItems } from "@/components/purchase-orders/po-line-items";
import { LoadingCard } from "@/components/loading-card";
import { ErrorRetry } from "@/components/error-retry";
import { formatCurrency, formatNumber } from "@/lib/formatters";

export default function PODetailPage() {
  const params = useParams<{ po_number: string }>();
  const poNumber = params.po_number;

  const { data, error, isLoading } = usePODetail(poNumber ?? null);

  const kpis = useMemo(() => {
    if (!data) return null;
    const fillPct =
      data.total_ordered_value > 0
        ? (data.total_received_value / data.total_ordered_value) * 100
        : 0;

    return [
      {
        id: "ordered",
        label: "Ordered Value",
        value: formatCurrency(data.total_ordered_value),
        delta: { dir: "up" as KpiDir, text: `${formatNumber(data.lines.length)} lines` },
        sub: "total PO value at order time",
        color: "accent" as KpiColor,
        sparkline: [] as number[],
        icon: Banknote,
      },
      {
        id: "received",
        label: "Received Value",
        value: formatCurrency(data.total_received_value),
        delta: {
          dir: (data.total_received_value >= data.total_ordered_value ? "up" : "down") as KpiDir,
          text: `${fillPct.toFixed(0)}% delivered`,
        },
        sub: "value of units actually received",
        color: "purple" as KpiColor,
        sparkline: [] as number[],
        icon: PackageCheck,
      },
      {
        id: "lines",
        label: "Line Items",
        value: formatNumber(data.lines.length),
        delta: { dir: "up" as KpiDir, text: "distinct SKUs" },
        sub: "products on this PO",
        color: "amber" as KpiColor,
        sparkline: [] as number[],
        icon: ClipboardList,
      },
      {
        id: "fill",
        label: "Fill Rate",
        value: `${fillPct.toFixed(0)}%`,
        delta: {
          dir: (fillPct >= 90 ? "up" : "down") as KpiDir,
          text: fillPct >= 90 ? "on target" : "watch",
        },
        sub: "received ÷ ordered value",
        color: "red" as KpiColor,
        sparkline: [] as number[],
        icon: Target,
      },
    ];
  }, [data]);

  return (
    <DashboardShell
      activeHref="/purchase-orders"
      breadcrumbs={[
        { label: "DataPulse", href: "/dashboard" },
        { label: "Operations" },
        { label: "Purchase orders", href: "/purchase-orders" },
        { label: poNumber ?? "Detail" },
      ]}
    >
      <div className="page">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h1 className="page-title">{poNumber ? `PO ${poNumber}` : "Purchase order"}</h1>
            <p className="page-sub">Purchase order details and line items.</p>
          </div>
          <Link
            href="/purchase-orders"
            className="flex items-center gap-1.5 self-start text-sm text-text-secondary hover:text-text-primary"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Purchase Orders
          </Link>
        </div>

        {isLoading && (
          <div className="space-y-4">
            <LoadingCard lines={3} />
            <LoadingCard lines={6} className="h-64" />
          </div>
        )}

        {error && (
          <ErrorRetry
            title="Failed to load purchase order"
            description="Please try again."
          />
        )}

        {data && (
          <>
            <section
              className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4"
              aria-label="Purchase order KPIs"
            >
              {kpis!.map((k) => (
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

            <div className="rounded-xl border border-border bg-card p-4">
              <POStatusPipeline currentStatus={data.status} />
            </div>

            <POHeader po={data} />

            <div>
              <AnalyticsSectionHeader
                title={`Line Items (${data.lines.length})`}
                icon={List}
                accentClassName="text-accent"
              />
              <POLineItems lines={data.lines} />
            </div>
          </>
        )}
      </div>
    </DashboardShell>
  );
}
