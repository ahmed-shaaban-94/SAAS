"use client";

import { Header } from "@/components/layout/header";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { PageTransition } from "@/components/layout/page-transition";
import { FilterBar } from "@/components/filters/filter-bar";
import { StaffOverview } from "@/components/staff/staff-overview";
import { GamifiedLeaderboard } from "@/components/staff/gamified-leaderboard";
import { StaffQuotaSection } from "@/components/staff/staff-quota-section";
import { AnalyticsSectionHeader } from "@/components/layout/analytics-section-header";
import { Trophy, Target } from "lucide-react";

export default function StaffPage() {
  return (
    <PageTransition>
      <Breadcrumbs />
      <Header
        title="Staff Performance"
        description="Sales team performance rankings"
      />
      <FilterBar />
      <StaffOverview />

      <div className="mt-10">
        <AnalyticsSectionHeader title="Quota Attainment" icon={Target} />
        <StaffQuotaSection />
      </div>

      <div className="mt-10">
        <AnalyticsSectionHeader title="Leaderboard" icon={Trophy} accentClassName="text-chart-amber" />
        <GamifiedLeaderboard />
      </div>
    </PageTransition>
  );
}
