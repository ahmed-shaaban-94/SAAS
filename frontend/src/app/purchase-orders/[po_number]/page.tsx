"use client";

/**
 * /purchase-orders/[po_number] — drill-down detail on the v2 focus shell.
 *
 * Parent /purchase-orders is already on the v2 shell (from the
 * ops-pages-v2-rollout PR); the /purchase-orders/layout.tsx that
 * forwards to V2Layout is reused for this subroute.
 */

import { useParams } from "next/navigation";
import { List } from "lucide-react";

import { FocusShell } from "@/components/dashboard-v2/shell";
import { AnalyticsSectionHeader } from "@/components/layout/analytics-section-header";
import { POStatusPipeline } from "@/components/purchase-orders/po-status-pipeline";
import { POHeader } from "@/components/purchase-orders/po-header";
import { POLineItems } from "@/components/purchase-orders/po-line-items";
import { usePODetail } from "@/hooks/use-po-detail";
import { LoadingCard } from "@/components/loading-card";
import { ErrorRetry } from "@/components/error-retry";

export default function PODetailPage() {
  const params = useParams<{ po_number: string }>();
  const poNumber = params.po_number;
  const { data, error, isLoading } = usePODetail(poNumber ?? null);

  const breadcrumbs: Array<{ label: string; href?: string }> = [
    { label: "DataPulse", href: "/dashboard" },
    { label: "Operations" },
    { label: "Purchase orders", href: "/purchase-orders" },
    { label: poNumber ?? "—" },
  ];

  return (
    <FocusShell
      backHref="/purchase-orders"
      backLabel="Purchase orders"
      breadcrumbs={breadcrumbs}
    >
      <div>
        <h1 className="page-title">{poNumber ? `PO ${poNumber}` : "Purchase Order"}</h1>
        <p className="page-sub">Purchase order details and line items.</p>
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
    </FocusShell>
  );
}
