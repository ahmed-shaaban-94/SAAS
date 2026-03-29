"use client";

import Link from "next/link";
import { useParams, notFound } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { useCustomerDetail } from "@/hooks/use-customer-detail";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { PageTransition } from "@/components/layout/page-transition";
import { LoadingCard } from "@/components/loading-card";
import { ErrorRetry } from "@/components/error-retry";
import { EmptyState } from "@/components/empty-state";
import { StatCard } from "@/components/shared/stat-card";
import { formatCurrency, formatNumber } from "@/lib/formatters";

export default function CustomerDetailPage() {
  const params = useParams<{ key: string }>();
  const customerKey = Number(params.key);
  if (isNaN(customerKey)) {
    notFound();
  }
  const { data, error, isLoading, mutate } = useCustomerDetail(customerKey);

  if (isLoading) {
    return (
      <PageTransition>
        <div className="space-y-6">
          <LoadingCard lines={2} />
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <LoadingCard key={i} lines={2} />
            ))}
          </div>
        </div>
      </PageTransition>
    );
  }

  if (error) {
    return (
      <PageTransition>
        <ErrorRetry
          title="Failed to load customer details"
          description={error.message || "An error occurred while fetching customer data."}
          onRetry={() => mutate()}
        />
      </PageTransition>
    );
  }

  if (!data) {
    return (
      <PageTransition>
        <EmptyState
          title="Customer not found"
          description="The requested customer could not be found."
        />
      </PageTransition>
    );
  }

  return (
    <PageTransition>
      <div className="space-y-6">
        <Breadcrumbs />

        <div>
          <h1 className="text-2xl font-bold text-text-primary">{data.customer_name}</h1>
          <p className="mt-1 text-sm text-text-secondary">ID: {data.customer_id}</p>
        </div>

        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <StatCard label="Customer ID" value={data.customer_id} />
          <StatCard label="Total Quantity" value={formatNumber(data.total_quantity)} />
          <StatCard label="Net Amount" value={formatCurrency(data.total_net_amount)} />
          <StatCard label="Transactions" value={formatNumber(data.transaction_count)} />
          <StatCard label="Unique Products" value={formatNumber(data.unique_products)} />
          <StatCard label="Return Count" value={formatNumber(data.return_count)} />
        </div>

        <Link
          href="/customers"
          className="inline-flex items-center gap-1 text-sm text-accent hover:underline"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Customers
        </Link>
      </div>
    </PageTransition>
  );
}
