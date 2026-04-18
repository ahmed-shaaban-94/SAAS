"use client";

import { Header } from "@/components/layout/header";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { PageTransition } from "@/components/layout/page-transition";
import { OpsSuiteNav } from "@/components/shared/ops-suite-nav";
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
    <PageTransition>
      <Breadcrumbs />
      <Header
        title="Dispensing Analytics"
        description="Dispense velocity, stock coverage, and reconciliation"
      />
      <FilterBar />
      <OpsSuiteNav />
      <DispensingOverview />

      {/* Top movers */}
      <div className="mt-6">
        <AnalyticsSectionHeader
          title="Top Dispensed Products"
          icon={TrendingUp}
          accentClassName="text-accent"
        />
        <DispenseRateCards />
      </div>

      {/* Days of stock + Stockout risk */}
      <div className="mt-10 grid gap-6 lg:grid-cols-2">
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

      {/* Velocity grid */}
      <div className="mt-10">
        <AnalyticsSectionHeader
          title="Velocity Classification"
          icon={TrendingUp}
          accentClassName="text-accent"
        />
        <VelocityGrid />
      </div>

      {/* Reconciliation */}
      <div className="mt-10">
        <AnalyticsSectionHeader
          title="Stock Reconciliation"
          icon={RefreshCw}
          accentClassName="text-accent"
        />
        <ReconciliationSummary />
      </div>
    </PageTransition>
  );
}
