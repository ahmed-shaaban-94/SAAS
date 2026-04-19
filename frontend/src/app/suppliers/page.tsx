"use client";

/**
 * /suppliers — v2 cutover. Supplier directory + performance comparison
 * on the shared DashboardShell.
 */

import { Building2, BarChart3 } from "lucide-react";

import { DashboardShell } from "@/components/dashboard-v2/shell";
import { AnalyticsSectionHeader } from "@/components/layout/analytics-section-header";
import { SupplierTable } from "@/components/suppliers/supplier-table";
import { EmptySupplier } from "@/components/suppliers/empty-supplier";
import { SupplierPerformanceChart } from "@/components/suppliers/supplier-performance-chart";
import { useSuppliers } from "@/hooks/use-suppliers";
import { LoadingCard } from "@/components/loading-card";
import { ErrorRetry } from "@/components/error-retry";

export default function SuppliersPage() {
  const { data, error, isLoading } = useSuppliers();

  const activeCount = data.filter((s) => s.is_active).length;

  return (
    <DashboardShell
      activeHref="/suppliers"
      breadcrumbs={[
        { label: "DataPulse", href: "/dashboard" },
        { label: "Operations" },
        { label: "Suppliers" },
      ]}
    >
      <div className="page">
        <div>
          <h1 className="page-title">Suppliers.</h1>
          <p className="page-sub">
            {data.length} suppliers · {activeCount} active. Directory and
            performance, one surface.
          </p>
        </div>

        <div>
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

        {data.length > 0 && (
          <div style={{ marginTop: 40 }}>
            <AnalyticsSectionHeader
              title="Performance Comparison"
              icon={BarChart3}
              accentClassName="text-accent"
            />
            <SupplierPerformanceChart />
          </div>
        )}
      </div>
    </DashboardShell>
  );
}
