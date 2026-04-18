"use client";

import { Header } from "@/components/layout/header";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { PageTransition } from "@/components/layout/page-transition";
import { OpsSuiteNav } from "@/components/shared/ops-suite-nav";
import { AnalyticsSectionHeader } from "@/components/layout/analytics-section-header";
import { SupplierTable } from "@/components/suppliers/supplier-table";
import { EmptySupplier } from "@/components/suppliers/empty-supplier";
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
      <OpsSuiteNav />

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
        ) : data.length === 0 ? (
          <EmptySupplier />
        ) : (
          <SupplierTable suppliers={data} />
        )}
      </div>

      {/* Performance chart */}
      {data.length > 0 && (
        <div className="mt-10">
          <AnalyticsSectionHeader
            title="Performance Comparison"
            icon={BarChart3}
            accentClassName="text-accent"
          />
          <SupplierPerformanceChart />
        </div>
      )}
    </PageTransition>
  );
}
