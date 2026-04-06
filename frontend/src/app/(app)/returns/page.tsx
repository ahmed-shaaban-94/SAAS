"use client";

import { Header } from "@/components/layout/header";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { PageTransition } from "@/components/layout/page-transition";
import { FilterBar } from "@/components/filters/filter-bar";
import { ReturnsOverview } from "@/components/returns/returns-overview";
import { ReturnsTrendChart } from "@/components/returns/returns-trend-chart";
import { ReturnRateGauge } from "@/components/returns/return-rate-gauge";
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
        <div className="flex items-center gap-2 mb-4">
          <div className="flex h-6 w-6 items-center justify-center rounded-md bg-red-500/10">
            <TrendingDown className="h-3.5 w-3.5 text-red-500" />
          </div>
          <h2 className="text-[11px] font-semibold uppercase tracking-widest text-text-secondary">
            Returns Analysis
          </h2>
          <div className="flex-1 section-divider" />
        </div>
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
