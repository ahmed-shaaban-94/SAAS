"use client";

import { Header } from "@/components/layout/header";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { PageTransition } from "@/components/layout/page-transition";
import { GamificationDashboard } from "@/components/gamification/gamification-dashboard";

export default function GamificationPage() {
  return (
    <PageTransition>
      <Breadcrumbs />
      <Header
        title="Gamification"
        description="Badges, XP, streaks, competitions, and leaderboards"
      />
      <GamificationDashboard />
    </PageTransition>
  );
}
