"use client";

/**
 * /insights — v2 cutover. AI narrative summaries + anomaly watch on
 * the shared DashboardShell.
 */

import { AlertTriangle, Sparkles } from "lucide-react";

import { DashboardShell } from "@/components/dashboard-v2/shell";
import { AISummaryCard } from "@/components/ai-light/ai-summary-card";
import { AnomalyList } from "@/components/ai-light/anomaly-list";
import { AnalyticsSectionHeader } from "@/components/layout/analytics-section-header";

export default function InsightsPage() {
  return (
    <DashboardShell
      activeHref="/insights"
      breadcrumbs={[
        { label: "DataPulse", href: "/dashboard" },
        { label: "Dashboards" },
        { label: "Insights" },
      ]}
    >
      <div className="page">
        <div>
          <h1 className="page-title">Insights.</h1>
          <p className="page-sub">
            AI-generated narrative summaries and signal watch across the
            business.
          </p>
        </div>

        <div>
          <AnalyticsSectionHeader title="Narrative Summary" icon={Sparkles} />
          <AISummaryCard />
        </div>

        <div style={{ marginTop: 40 }}>
          <AnalyticsSectionHeader
            title="Signal Watch"
            icon={AlertTriangle}
            accentClassName="text-chart-amber"
          />
          <AnomalyList />
        </div>
      </div>
    </DashboardShell>
  );
}
