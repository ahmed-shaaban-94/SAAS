"use client";

import { Header } from "@/components/layout/header";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { PageTransition } from "@/components/layout/page-transition";
import { AISummaryCard } from "@/components/ai-light/ai-summary-card";
import { AnomalyList } from "@/components/ai-light/anomaly-list";
import { AnalyticsSectionHeader } from "@/components/layout/analytics-section-header";
import { AlertTriangle, Sparkles } from "lucide-react";

export default function InsightsPage() {
  return (
    <PageTransition>
      <Breadcrumbs />
      <Header
        title="AI Insights"
        description="AI-generated summaries and anomaly detection"
      />
      <AnalyticsSectionHeader title="Narrative Summary" icon={Sparkles} />
      <AISummaryCard />
      <div className="mt-10">
        <AnalyticsSectionHeader title="Signal Watch" icon={AlertTriangle} accentClassName="text-chart-amber" />
        <AnomalyList />
      </div>
    </PageTransition>
  );
}
