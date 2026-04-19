"use client";

/**
 * /products/[key] — drill-down detail on the v2 focus shell.
 */

import { useParams, notFound } from "next/navigation";

import { FocusShell } from "@/components/dashboard-v2/shell";
import { useProductDetail } from "@/hooks/use-product-detail";
import { LoadingCard } from "@/components/loading-card";
import { ErrorRetry } from "@/components/error-retry";
import { EmptyState } from "@/components/empty-state";
import { StatCard } from "@/components/shared/stat-card";
import { MiniTrendChart } from "@/components/shared/mini-trend-chart";
import { formatCurrency, formatNumber, formatPercent } from "@/lib/formatters";

export default function ProductDetailPage() {
  const params = useParams<{ key: string }>();
  const productKey = Number(params.key);
  if (isNaN(productKey)) {
    notFound();
  }
  const { data, error, isLoading, mutate } = useProductDetail(productKey);

  const breadcrumbs: Array<{ label: string; href?: string }> = [
    { label: "DataPulse", href: "/dashboard" },
    { label: "Products", href: "/products" },
    { label: data?.drug_name ?? String(productKey) },
  ];

  const shell = (body: React.ReactNode) => (
    <FocusShell backHref="/products" backLabel="Products" breadcrumbs={breadcrumbs}>
      {body}
    </FocusShell>
  );

  if (isLoading) {
    return shell(
      <div className="space-y-6">
        <LoadingCard lines={2} />
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <LoadingCard key={i} lines={2} />
          ))}
        </div>
      </div>,
    );
  }

  if (error) {
    return shell(
      <ErrorRetry
        title="Failed to load product details"
        description={error.message || "An error occurred while fetching product data."}
        onRetry={() => mutate()}
      />,
    );
  }

  if (!data) {
    return shell(
      <EmptyState
        title="Product not found"
        description="The requested product could not be found."
      />,
    );
  }

  return shell(
    <>
      <div>
        <h1 className="page-title">{data.drug_name}</h1>
        <p className="page-sub">
          {data.drug_brand} · {data.drug_category}
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard label="Drug Code" value={data.drug_code} />
        <StatCard label="Brand" value={data.drug_brand} />
        <StatCard label="Category" value={data.drug_category} />
        <StatCard label="Total Quantity" value={formatNumber(data.total_quantity)} />
        <StatCard label="Total Sales" value={formatCurrency(data.total_sales)} />
        <StatCard label="Net Amount" value={formatCurrency(data.total_net_amount)} />
        <StatCard label="Return Rate" value={formatPercent(data.return_rate)} />
        <StatCard label="Unique Customers" value={formatNumber(data.unique_customers)} />
      </div>

      {data.monthly_trend && data.monthly_trend.length > 0 && (
        <MiniTrendChart data={data.monthly_trend} title="Monthly Revenue Trend" />
      )}
    </>,
  );
}
