"use client";

import { Header } from "@/components/layout/header";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { PageTransition } from "@/components/layout/page-transition";
import { LineageOverview } from "@/components/lineage/lineage-overview";

export default function LineagePage() {
  return (
    <PageTransition>
      <Breadcrumbs />
      <Header
        title="Data Lineage"
        description="Visualize data flow from Bronze to Silver to Gold"
      />
      <LineageOverview />
    </PageTransition>
  );
}
