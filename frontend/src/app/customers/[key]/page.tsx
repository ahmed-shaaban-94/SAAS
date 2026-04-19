"use client";

/**
 * /customers/[key] — drill-down detail on the v2 focus shell.
 */

import { useParams, notFound } from "next/navigation";

import { FocusShell } from "@/components/dashboard-v2/shell";
import { useCustomerDetail } from "@/hooks/use-customer-detail";
import { LoadingCard } from "@/components/loading-card";
import { ErrorRetry } from "@/components/error-retry";
import { EmptyState } from "@/components/empty-state";
import { StatCard } from "@/components/shared/stat-card";
import { MiniTrendChart } from "@/components/shared/mini-trend-chart";
import { formatCurrency, formatNumber } from "@/lib/formatters";

export default function CustomerDetailPage() {
  const params = useParams<{ key: string }>();
  const customerKey = Number(params.key);
  if (isNaN(customerKey)) {
    notFound();
  }
  const { data, error, isLoading, mutate } = useCustomerDetail(customerKey);

  const breadcrumbs: Array<{ label: string; href?: string }> = [
    { label: "DataPulse", href: "/dashboard" },
    { label: "Customers", href: "/customers" },
    { label: data?.customer_name ?? String(customerKey) },
  ];

  const shell = (body: React.ReactNode) => (
    <FocusShell backHref="/customers" backLabel="Customers" breadcrumbs={breadcrumbs}>
      {body}
    </FocusShell>
  );

  if (isLoading) {
    return shell(
      <div className="space-y-6">
        <LoadingCard lines={2} />
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <LoadingCard key={i} lines={2} />
          ))}
        </div>
      </div>,
    );
  }

  if (error) {
    return shell(
      <ErrorRetry
        title="Failed to load customer details"
        description={error.message || "An error occurred while fetching customer data."}
        onRetry={() => mutate()}
      />,
    );
  }

  if (!data) {
    return shell(
      <EmptyState
        title="Customer not found"
        description="The requested customer could not be found."
      />,
    );
  }

  return shell(
    <>
      <div>
        <h1 className="page-title">{data.customer_name}</h1>
        <p className="page-sub">ID: {data.customer_id}</p>
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard label="Customer ID" value={data.customer_id} />
        <StatCard label="Total Quantity" value={formatNumber(data.total_quantity)} />
        <StatCard label="Net Amount" value={formatCurrency(data.total_net_amount)} />
        <StatCard label="Transactions" value={formatNumber(data.transaction_count)} />
        <StatCard label="Unique Products" value={formatNumber(data.unique_products)} />
        <StatCard label="Return Count" value={formatNumber(data.return_count)} />
      </div>

      {data.monthly_trend && data.monthly_trend.length > 0 && (
        <MiniTrendChart data={data.monthly_trend} title="Monthly Revenue Trend" />
      )}
    </>,
  );
}
