"use client";

import { Info } from "lucide-react";

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
        title="Model Lineage (Admin)"
        description="dbt model dependency graph for debugging and impact analysis"
      />
      <div className="mb-4 flex items-start gap-2 rounded-lg border border-border/60 bg-background/40 px-3 py-2 text-xs text-text-secondary">
        <Info className="mt-0.5 h-3.5 w-3.5 shrink-0 text-accent" />
        <p>
          This is a debug surface for admins. For run-level impact and data trust signals,
          see <a href="/quality" className="font-medium text-accent hover:underline">Pipeline Health</a>.
        </p>
      </div>
      <DataOpsCommandBar />
      <LineageOverview />
    </PageTransition>
  );
}
