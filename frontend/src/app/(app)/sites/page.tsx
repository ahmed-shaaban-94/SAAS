"use client";

import { Header } from "@/components/layout/header";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { PageTransition } from "@/components/layout/page-transition";
import { FilterBar } from "@/components/filters/filter-bar";
import { SiteOverview } from "@/components/sites/site-overview";
import { RadarComparison } from "@/components/sites/radar-comparison";
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
        <div className="flex items-center gap-2 mb-4">
          <div className="flex h-6 w-6 items-center justify-center rounded-md bg-accent/10">
            <Radar className="h-3.5 w-3.5 text-accent" />
          </div>
          <h2 className="text-[11px] font-semibold uppercase tracking-widest text-text-secondary">
            Multi-Dimensional Comparison
          </h2>
          <div className="flex-1 section-divider" />
        </div>
        <RadarComparison />
      </div>
    </PageTransition>
  );
}
