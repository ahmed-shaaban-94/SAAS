"use client";

import { Header } from "@/components/layout/header";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { PageTransition } from "@/components/layout/page-transition";
import { FilterBar } from "@/components/filters/filter-bar";
import { CustomerOverview } from "@/components/customers/customer-overview";
import { RFMMatrix } from "@/components/customers/rfm-matrix";
import { SegmentFunnel } from "@/components/customers/segment-funnel";
import { AnalyticsSectionHeader } from "@/components/layout/analytics-section-header";
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
        <AnalyticsSectionHeader title="Customer Segmentation (RFM)" icon={UserCheck} />
        <div className="space-y-6">
          <RFMMatrix />
          <SegmentFunnel />
        </div>
      </div>
    </PageTransition>
  );
}
