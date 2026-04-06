"use client";

import { Header } from "@/components/layout/header";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { PageTransition } from "@/components/layout/page-transition";
import { AISummaryCard } from "@/components/ai-light/ai-summary-card";
import { AnomalyList } from "@/components/ai-light/anomaly-list";

export default function InsightsPage() {
  return (
    <PageTransition>
      <Breadcrumbs />
      <Header
        title="AI Insights"
        description="AI-generated summaries and anomaly detection"
      />
      <AISummaryCard />
      <div className="mt-6">
        <AnomalyList />
      </div>
    </PageTransition>
  );
}
