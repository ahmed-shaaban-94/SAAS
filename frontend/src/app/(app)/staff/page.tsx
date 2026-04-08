"use client";

import { Header } from "@/components/layout/header";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { PageTransition } from "@/components/layout/page-transition";
import { FilterBar } from "@/components/filters/filter-bar";
import { StaffOverview } from "@/components/staff/staff-overview";
import { GamifiedLeaderboard } from "@/components/staff/gamified-leaderboard";
import { StaffQuotaSection } from "@/components/staff/staff-quota-section";
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

      {/* Quota Attainment Section */}
      <div className="mt-10">
        <div className="flex items-center gap-2 mb-4">
          <div className="flex h-6 w-6 items-center justify-center rounded-md bg-accent/10">
            <Target className="h-3.5 w-3.5 text-accent" />
          </div>
          <h2 className="text-[11px] font-semibold uppercase tracking-widest text-text-secondary">
            Quota Attainment
          </h2>
          <div className="flex-1 section-divider" />
        </div>
        <StaffQuotaSection />
      </div>

      {/* Gamified Leaderboard Section */}
      <div className="mt-10">
        <div className="flex items-center gap-2 mb-4">
          <div className="flex h-6 w-6 items-center justify-center rounded-md bg-accent/10">
            <Trophy className="h-3.5 w-3.5 text-accent" />
          </div>
          <h2 className="text-[11px] font-semibold uppercase tracking-widest text-text-secondary">
            Leaderboard
          </h2>
          <div className="flex-1 section-divider" />
        </div>
        <GamifiedLeaderboard />
      </div>
    </PageTransition>
  );
}
