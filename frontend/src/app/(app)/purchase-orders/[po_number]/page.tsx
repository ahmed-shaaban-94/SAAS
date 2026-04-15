"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { usePODetail } from "@/hooks/use-po-detail";
import { Header } from "@/components/layout/header";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { PageTransition } from "@/components/layout/page-transition";
import { AnalyticsSectionHeader } from "@/components/layout/analytics-section-header";
import { POStatusPipeline } from "@/components/purchase-orders/po-status-pipeline";
import { POHeader } from "@/components/purchase-orders/po-header";
import { POLineItems } from "@/components/purchase-orders/po-line-items";
import { LoadingCard } from "@/components/loading-card";
import { ErrorRetry } from "@/components/error-retry";
import { List } from "lucide-react";

export default function PODetailPage() {
  const params = useParams<{ po_number: string }>();
  const poNumber = params.po_number;

  const { data, error, isLoading } = usePODetail(poNumber ?? null);

  return (
    <PageTransition>
      <Breadcrumbs />

      {/* Back link */}
      <Link
        href="/purchase-orders"
        className="mb-4 flex items-center gap-1.5 text-sm text-text-secondary hover:text-text-primary"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Purchase Orders
      </Link>

      <Header
        title={poNumber ? `PO ${poNumber}` : "Purchase Order"}
        description="Purchase order details and line items"
      />

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
          {/* Status pipeline */}
          <div className="mt-2 rounded-xl border border-border bg-card p-4">
            <POStatusPipeline currentStatus={data.status} />
          </div>

          {/* PO metadata */}
          <div className="mt-4">
            <POHeader po={data} />
          </div>

          {/* Line items */}
          <div className="mt-8">
            <AnalyticsSectionHeader
              title={`Line Items (${data.lines.length})`}
              icon={List}
              accentClassName="text-accent"
            />
            <POLineItems lines={data.lines} />
          </div>
        </>
      )}
    </PageTransition>
  );
}
