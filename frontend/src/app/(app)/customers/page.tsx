"use client";

import { Header } from "@/components/layout/header";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { PageTransition } from "@/components/layout/page-transition";
import { FilterBar } from "@/components/filters/filter-bar";
import { CustomerOverview } from "@/components/customers/customer-overview";
import { RFMMatrix } from "@/components/customers/rfm-matrix";
import { SegmentFunnel } from "@/components/customers/segment-funnel";
import { UserCheck } from "lucide-react";

export default function CustomersPage() {
  return (
    <PageTransition>
      <Breadcrumbs />
      <Header
        title="Customer Intelligence"
        description="Top customers by revenue contribution"
      />
      <FilterBar />
      <CustomerOverview />

      {/* RFM Segmentation Section */}
      <div className="mt-10">
        <div className="flex items-center gap-2 mb-4">
          <div className="flex h-6 w-6 items-center justify-center rounded-md bg-accent/10">
            <UserCheck className="h-3.5 w-3.5 text-accent" />
          </div>
          <h2 className="text-[11px] font-semibold uppercase tracking-widest text-text-secondary">
            Customer Segmentation (RFM)
          </h2>
          <div className="flex-1 section-divider" />
        </div>
        <div className="space-y-6">
          <RFMMatrix />
          <SegmentFunnel />
        </div>
      </div>
    </PageTransition>
  );
}
