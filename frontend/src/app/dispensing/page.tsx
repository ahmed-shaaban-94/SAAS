"use client";

/**
 * /dispensing — Dispense velocity, stock coverage, and reconciliation
 * on the shared DashboardShell.
 *
 * Pharma Ops batch (Apr 2026): replaced the StatCard-based
 * `DispensingOverview` with a 4-tile `KpiCard` grid aligned with the
 * rest of the app.
 */

import { useMemo } from "react";
import { Pill, AlertTriangle, Clock, RefreshCw, TrendingUp, BarChart3 } from "lucide-react";

import { DashboardShell } from "@/components/dashboard-v2/shell";
import { FilterBar } from "@/components/filters/filter-bar";
import { AnalyticsSectionHeader } from "@/components/layout/analytics-section-header";
import { KpiCard, type KpiColor, type KpiDir } from "@/components/dashboard/new";
import { LoadingCard } from "@/components/loading-card";
import { DispenseRateCards } from "@/components/dispensing/dispense-rate-cards";
import { DaysOfStockChart } from "@/components/dispensing/days-of-stock-chart";
import { VelocityGrid } from "@/components/dispensing/velocity-grid";
import { StockoutRiskTable } from "@/components/dispensing/stockout-risk-table";
import { ReconciliationSummary } from "@/components/dispensing/reconciliation-summary";
import { useFilters } from "@/contexts/filter-context";
import { useDispenseRate } from "@/hooks/use-dispense-rate";
import { useStockoutRisk } from "@/hooks/use-stockout-risk";
import { useDaysOfStock } from "@/hooks/use-days-of-stock";
import { useReconciliation } from "@/hooks/use-reconciliation";
import { formatNumber } from "@/lib/formatters";

export default function DispensingPage() {
  const { filters } = useFilters();
  const rate = useDispenseRate(filters);
  const risk = useStockoutRisk();
  const days = useDaysOfStock(filters);
  const recon = useReconciliation();

  const kpiLoading = rate.isLoading || risk.isLoading || days.isLoading || recon.isLoading;

  const kpis = useMemo(() => {
    const activeProducts = rate.data.length;
    const stockoutRisk = risk.data.length;
    const daysWithStock = days.data.filter((d) => d.days_of_stock !== null);
    const avgDays =
      daysWithStock.length > 0
        ? daysWithStock.reduce((s, d) => s + (d.days_of_stock ?? 0), 0) /
          daysWithStock.length
        : 0;
    const varianceCount = recon.data?.items_with_variance ?? 0;

    return [
      {
        id: "active",
        label: "Active Products",
        value: formatNumber(activeProducts),
        delta: { dir: "up" as KpiDir, text: "dispensing now" },
        sub: "with recent rate measurements",
        color: "accent" as KpiColor,
        sparkline: [] as number[],
        icon: Pill,
      },
      {
        id: "stockout-risk",
        label: "Stockout Risk",
        value: formatNumber(stockoutRisk),
        delta: {
          dir: (stockoutRisk === 0 ? "up" : "down") as KpiDir,
          text: stockoutRisk === 0 ? "clear" : "needs reorder",
        },
        sub: "items projected to run out",
        color: "red" as KpiColor,
        sparkline: [] as number[],
        icon: AlertTriangle,
      },
      {
        id: "days-of-stock",
        label: "Avg Days of Stock",
        value: avgDays.toFixed(1),
        delta: {
          dir: (avgDays >= 14 ? "up" : "down") as KpiDir,
          text: avgDays >= 14 ? "comfortable" : "tight",
        },
        sub: "across items with velocity",
        color: "amber" as KpiColor,
        sparkline: [] as number[],
        icon: Clock,
      },
      {
        id: "recon",
        label: "Recon Variances",
        value: formatNumber(varianceCount),
        delta: {
          dir: (varianceCount === 0 ? "up" : "down") as KpiDir,
          text: varianceCount === 0 ? "in balance" : "investigate",
        },
        sub: "ledger vs physical count",
        color: "purple" as KpiColor,
        sparkline: [] as number[],
        icon: RefreshCw,
      },
    ];
  }, [rate.data, risk.data, days.data, recon.data]);

  return (
    <DashboardShell
      activeHref="/dispensing"
      breadcrumbs={[
        { label: "DataPulse", href: "/dashboard" },
        { label: "Operations" },
        { label: "Dispensing" },
      ]}
    >
      <div className="page">
        <div>
          <h1 className="page-title">Dispensing.</h1>
          <p className="page-sub">
            Dispense velocity, stock coverage, and reconciliation across every
            pharmacy branch.
          </p>
        </div>

        <section
          className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4"
          aria-label="Dispensing KPIs"
        >
          {kpiLoading
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

        <FilterBar />

        <div style={{ marginTop: 24 }}>
          <AnalyticsSectionHeader
            title="Top Dispensed Products"
            icon={TrendingUp}
            accentClassName="text-accent"
          />
          <DispenseRateCards />
        </div>

        <div className="grid gap-6 lg:grid-cols-2" style={{ marginTop: 40 }}>
          <div>
            <AnalyticsSectionHeader
              title="Days of Stock"
              icon={BarChart3}
              accentClassName="text-accent"
            />
            <DaysOfStockChart />
          </div>
          <div>
            <AnalyticsSectionHeader
              title="Stockout Risk"
              icon={AlertTriangle}
              accentClassName="text-red-400"
            />
            <StockoutRiskTable />
          </div>
        </div>

        <div style={{ marginTop: 40 }}>
          <AnalyticsSectionHeader
            title="Velocity Classification"
            icon={TrendingUp}
            accentClassName="text-accent"
          />
          <VelocityGrid />
        </div>

        <div style={{ marginTop: 40 }}>
          <AnalyticsSectionHeader
            title="Stock Reconciliation"
            icon={RefreshCw}
            accentClassName="text-accent"
          />
          <ReconciliationSummary />
        </div>
      </div>
    </DashboardShell>
  );
}
