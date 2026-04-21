"use client";

/**
 * /suppliers — Supplier directory + performance comparison.
 *
 * Pharma Ops batch (Apr 2026): added a 4-tile `KpiCard` grid
 * (total, active, avg lead time, avg payment terms) derived from the
 * existing supplier-directory endpoint — no new backend work.
 */

import { useMemo } from "react";
import {
  Building2,
  BarChart3,
  CheckCircle2,
  Truck,
  CalendarDays,
  Users,
} from "lucide-react";

import { DashboardShell } from "@/components/dashboard-v2/shell";
import { AnalyticsSectionHeader } from "@/components/layout/analytics-section-header";
import { KpiCard, type KpiColor, type KpiDir } from "@/components/dashboard/new";
import { SupplierTable } from "@/components/suppliers/supplier-table";
import { EmptySupplier } from "@/components/suppliers/empty-supplier";
import { SupplierPerformanceChart } from "@/components/suppliers/supplier-performance-chart";
import { useSuppliers } from "@/hooks/use-suppliers";
import { LoadingCard } from "@/components/loading-card";
import { ErrorRetry } from "@/components/error-retry";
import { formatNumber } from "@/lib/formatters";

export default function SuppliersPage() {
  const { data, error, isLoading } = useSuppliers();

  const kpis = useMemo(() => {
    const total = data.length;
    const active = data.filter((s) => s.is_active).length;
    const leadTimes = data
      .map((s) => s.lead_time_days)
      .filter((v): v is number => Number.isFinite(v) && v > 0);
    const avgLead =
      leadTimes.length > 0
        ? leadTimes.reduce((a, b) => a + b, 0) / leadTimes.length
        : 0;
    const paymentTerms = data
      .map((s) => s.payment_terms_days)
      .filter((v): v is number => Number.isFinite(v) && v > 0);
    const avgTerms =
      paymentTerms.length > 0
        ? paymentTerms.reduce((a, b) => a + b, 0) / paymentTerms.length
        : 0;

    return [
      {
        id: "total",
        label: "Total Suppliers",
        value: formatNumber(total),
        delta: { dir: "up" as KpiDir, text: "in directory" },
        sub: "registered vendor records",
        color: "accent" as KpiColor,
        sparkline: [] as number[],
        icon: Users,
      },
      {
        id: "active",
        label: "Active Suppliers",
        value: formatNumber(active),
        delta: {
          dir: "up" as KpiDir,
          text: total > 0 ? `${((active / total) * 100).toFixed(0)}% of total` : "—",
        },
        sub: "currently engaged for ordering",
        color: "purple" as KpiColor,
        sparkline: [] as number[],
        icon: CheckCircle2,
      },
      {
        id: "lead",
        label: "Avg Lead Time",
        value: avgLead > 0 ? `${avgLead.toFixed(1)} d` : "—",
        delta: {
          dir: (avgLead > 0 && avgLead <= 7 ? "up" : "down") as KpiDir,
          text: avgLead === 0 ? "no data" : avgLead <= 7 ? "fast" : "slow",
        },
        sub: "days from PO to receipt",
        color: "amber" as KpiColor,
        sparkline: [] as number[],
        icon: Truck,
      },
      {
        id: "terms",
        label: "Avg Payment Terms",
        value: avgTerms > 0 ? `${avgTerms.toFixed(0)} d` : "—",
        delta: { dir: "up" as KpiDir, text: "net days" },
        sub: "cash-flow window",
        color: "red" as KpiColor,
        sparkline: [] as number[],
        icon: CalendarDays,
      },
    ];
  }, [data]);

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
            Directory and performance — one surface.
          </p>
        </div>

        <section
          className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4"
          aria-label="Supplier KPIs"
        >
          {isLoading
            ? Array.from({ length: 4 }).map((_, i) => (
                <LoadingCard key={i} lines={3} className="h-[168px]" />
              ))
            : kpis.map((k) => (
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
