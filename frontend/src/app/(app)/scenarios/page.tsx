"use client";

import { Header } from "@/components/layout/header";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { PageTransition } from "@/components/layout/page-transition";
import { ScenarioOverview } from "@/components/scenarios/scenario-overview";

export default function ScenariosPage() {
  return (
    <PageTransition>
      <Breadcrumbs />
      <Header
        title="What-If Analysis"
        description="Simulate price, volume, and cost changes to see projected impact"
      />
      <ScenarioOverview />
    </PageTransition>
  );
}
