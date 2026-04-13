"use client";

import { Header } from "@/components/layout/header";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { PageTransition } from "@/components/layout/page-transition";
import { FilterBar } from "@/components/filters/filter-bar";
import { SiteOverview } from "@/components/sites/site-overview";
import { RadarComparison } from "@/components/sites/radar-comparison";
import { AnalyticsSectionHeader } from "@/components/layout/analytics-section-header";
import { Radar } from "lucide-react";

export default function SitesPage() {
  return (
    <PageTransition>
      <Breadcrumbs />
      <Header
        title="Site Comparison"
        description="Performance across pharmacy locations"
      />
      <FilterBar />
      <SiteOverview />

      {/* Radar Comparison Section */}
      <div className="mt-10">
        <AnalyticsSectionHeader title="Multi-Dimensional Comparison" icon={Radar} />
        <RadarComparison />
      </div>
    </PageTransition>
  );
}
