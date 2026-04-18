"use client";

import { Header } from "@/components/layout/header";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { PageTransition } from "@/components/layout/page-transition";
import { DataOpsCommandBar } from "@/components/data-ops/command-bar";
import { QualityOverview } from "@/components/quality/quality-overview";

export default function QualityPage() {
  return (
    <PageTransition>
      <Breadcrumbs />
      <Header
        title="Pipeline Health"
        description="Freshness, completeness, and quality checks across every pipeline run"
      />
      <DataOpsCommandBar />
      <QualityOverview />
    </PageTransition>
  );
}
