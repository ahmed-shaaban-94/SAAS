"use client";

import Link from "next/link";
import { useParams, notFound } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { useProductDetail } from "@/hooks/use-product-detail";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { PageTransition } from "@/components/layout/page-transition";
import { LoadingCard } from "@/components/loading-card";
import { ErrorRetry } from "@/components/error-retry";
import { EmptyState } from "@/components/empty-state";
import { StatCard } from "@/components/shared/stat-card";
import { formatCurrency, formatNumber, formatPercent } from "@/lib/formatters";

export default function ProductDetailPage() {
  const params = useParams<{ key: string }>();
  const productKey = Number(params.key);
  if (isNaN(productKey)) {
    notFound();
  }
  const { data, error, isLoading, mutate } = useProductDetail(productKey);

  if (isLoading) {
    return (
      <PageTransition>
        <div className="space-y-6">
          <LoadingCard lines={2} />
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            {Array.from({ length: 8 }).map((_, i) => (
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
          title="Failed to load product details"
          description={error.message || "An error occurred while fetching product data."}
          onRetry={() => mutate()}
        />
      </PageTransition>
    );
  }

  if (!data) {
    return (
      <PageTransition>
        <EmptyState
          title="Product not found"
          description="The requested product could not be found."
        />
      </PageTransition>
    );
  }

  return (
    <PageTransition>
      <div className="space-y-6">
        <Breadcrumbs />

        <div>
          <h1 className="text-2xl font-bold text-text-primary">{data.drug_name}</h1>
          <p className="mt-1 text-sm text-text-secondary">{data.drug_brand} &middot; {data.drug_category}</p>
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

        <Link
          href="/products"
          className="inline-flex items-center gap-1 text-sm text-accent hover:underline"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Products
        </Link>
      </div>
    </PageTransition>
  );
}
