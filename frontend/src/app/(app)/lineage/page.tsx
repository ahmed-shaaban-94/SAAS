"use client";

import { Header } from "@/components/layout/header";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { PageTransition } from "@/components/layout/page-transition";
import { DataOpsCommandBar } from "@/components/data-ops/command-bar";
import { LineageOverview } from "@/components/lineage/lineage-overview";

export default function LineagePage() {
  return (
    <PageTransition>
      <Breadcrumbs />
      <Header
        title="Data Lineage"
        description="Trace data flow and analyze impact across the medallion layers"
      />
      <DataOpsCommandBar />
      <LineageOverview />
    </PageTransition>
  );
}
