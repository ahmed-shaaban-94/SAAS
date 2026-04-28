"use client";

import { DashboardShell } from "@/components/dashboard-v2/shell";
import { ScenarioOverview } from "@/components/scenarios/scenario-overview";

export default function ScenariosPage() {
  return (
    <DashboardShell
      activeHref="/scenarios"
      breadcrumbs={[
        { label: "DataPulse", href: "/dashboard" },
        { label: "Planning" },
        { label: "Scenarios" },
      ]}
    >
      <div className="page">
        <div>
          <h1 className="page-title">What-if analysis.</h1>
          <p className="page-sub">
            Simulate price, volume, and cost changes to see projected impact.
          </p>
        </div>
        <ScenarioOverview />
      </div>
    </DashboardShell>
  );
}
