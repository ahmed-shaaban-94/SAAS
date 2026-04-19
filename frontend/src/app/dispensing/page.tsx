"use client";

/**
 * /dispensing — v2 cutover. Dispense velocity, stock coverage, and
 * reconciliation on the shared DashboardShell.
 */

import { DashboardShell } from "@/components/dashboard-v2/shell";
import { FilterBar } from "@/components/filters/filter-bar";
import { AnalyticsSectionHeader } from "@/components/layout/analytics-section-header";
import { DispenseRateCards } from "@/components/dispensing/dispense-rate-cards";
import { DaysOfStockChart } from "@/components/dispensing/days-of-stock-chart";
import { VelocityGrid } from "@/components/dispensing/velocity-grid";
import { StockoutRiskTable } from "@/components/dispensing/stockout-risk-table";
import { ReconciliationSummary } from "@/components/dispensing/reconciliation-summary";
import { DispensingOverview } from "@/components/dispensing/dispensing-overview";
import { TrendingUp, BarChart3, AlertTriangle, RefreshCw } from "lucide-react";

export default function DispensingPage() {
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

        <FilterBar />

        <DispensingOverview />

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
