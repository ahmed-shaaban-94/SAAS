"use client";

import { Header } from "@/components/layout/header";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { PageTransition } from "@/components/layout/page-transition";
import { QualityOverview } from "@/components/quality/quality-overview";

export default function QualityPage() {
  return (
    <PageTransition>
      <Breadcrumbs />
      <Header
        title="Data Quality"
        description="Monitor pipeline quality scores and check results"
      />
      <QualityOverview />
    </PageTransition>
  );
}
