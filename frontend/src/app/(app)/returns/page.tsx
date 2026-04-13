"use client";

import { Header } from "@/components/layout/header";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { PageTransition } from "@/components/layout/page-transition";
import { FilterBar } from "@/components/filters/filter-bar";
import { ReturnsOverview } from "@/components/returns/returns-overview";
import { ReturnsTrendChart } from "@/components/returns/returns-trend-chart";
import { ReturnRateGauge } from "@/components/returns/return-rate-gauge";
import { AnalyticsSectionHeader } from "@/components/layout/analytics-section-header";
import { TrendingDown } from "lucide-react";

export default function ReturnsPage() {
  return (
    <PageTransition>
      <Breadcrumbs />
      <Header
        title="Returns Analysis"
        description="Product returns and customer return patterns"
      />
      <FilterBar />
      <ReturnsOverview />

      {/* Returns Trend Section */}
      <div className="mt-10">
        <AnalyticsSectionHeader
          title="Returns Analysis"
          icon={TrendingDown}
          accentClassName="text-growth-red"
        />
        <div className="grid gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <ReturnsTrendChart />
          </div>
          <ReturnRateGauge />
        </div>
      </div>
    </PageTransition>
  );
}
