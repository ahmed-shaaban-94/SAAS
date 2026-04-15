"use client";

import { Header } from "@/components/layout/header";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { PageTransition } from "@/components/layout/page-transition";
import { AnalyticsSectionHeader } from "@/components/layout/analytics-section-header";
import { SupplierTable } from "@/components/suppliers/supplier-table";
import { SupplierPerformanceChart } from "@/components/suppliers/supplier-performance-chart";
import { useSuppliers } from "@/hooks/use-suppliers";
import { LoadingCard } from "@/components/loading-card";
import { ErrorRetry } from "@/components/error-retry";
import { Building2, BarChart3 } from "lucide-react";

export default function SuppliersPage() {
  const { data, error, isLoading } = useSuppliers();

  const activeCount = data.filter((s) => s.is_active).length;

  return (
    <PageTransition>
      <Breadcrumbs />
      <Header
        title="Suppliers"
        description={`${data.length} suppliers · ${activeCount} active`}
      />

      {/* Supplier directory */}
      <div className="mt-6">
        <AnalyticsSectionHeader
          title="Supplier Directory"
          icon={Building2}
          accentClassName="text-accent"
        />

        {isLoading ? (
          <LoadingCard lines={8} className="h-64" />
        ) : error ? (
          <ErrorRetry
            title="Failed to load suppliers"
            description="Please try again."
          />
        ) : (
          <SupplierTable suppliers={data} />
        )}
      </div>

      {/* Performance chart */}
      <div className="mt-10">
        <AnalyticsSectionHeader
          title="Performance Comparison"
          icon={BarChart3}
          accentClassName="text-accent"
        />
        <SupplierPerformanceChart />
      </div>
    </PageTransition>
  );
}
