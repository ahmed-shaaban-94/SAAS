"use client";

import { AlertBanner } from "@/components/dashboard/new/alert-banner";
import { AnomalyFeed } from "@/components/dashboard/new/anomaly-feed";
import { BranchList } from "@/components/dashboard/new/branch-list";
import { ChannelDonut } from "@/components/dashboard/new/channel-donut";
import { ExpiryExposureCard } from "@/components/dashboard/new/expiry-exposure-card";
import { ExpiryHeatmap } from "@/components/dashboard/new/expiry-heatmap";
import { InventoryTable } from "@/components/dashboard/new/inventory-table";
import { KpiRow } from "@/components/dashboard/new/kpi-row";
import { PipelineHealthCard } from "@/components/dashboard/new/pipeline-health-card";
import { RevenueChart } from "@/components/dashboard/new/revenue-chart";
import { cn } from "@/lib/utils";

export interface DashboardGridProps {
  className?: string;
}

/**
 * Capstone layout for the new dashboard (#502) — wires together the ten
 * widgets shipped in #525 – #531 against a single responsive CSS grid.
 *
 * Breakpoints:
 *   - mobile (< sm): every widget full-width, stacked
 *   - sm / md: 2-column grid where the secondary rail collapses under
 *     the main chart
 *   - lg: canonical 12-column dashboard with RevenueChart spanning 8
 *     cols + Channel/Anomalies rail at 4 cols, then the ops row below
 *
 * Exported as a component (no page yet) so callers can embed it inside
 * whichever route / feature flag wrapper is appropriate. The existing
 * ``/dashboard`` route stays on the v2 shell until the swap PR.
 */
export function DashboardGrid({ className }: DashboardGridProps) {
  return (
    <div
      className={cn("space-y-4 lg:space-y-6", className)}
      data-testid="dashboard-grid-new"
    >
      {/* 1. Attention banner — hides itself on 204. */}
      <AlertBanner />

      {/* 2. KPI row — four tiles, already responsive internally. */}
      <KpiRow />

      {/* 3. Primary row: RevenueChart + Channel donut + anomalies rail. */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-12 lg:gap-6">
        <RevenueChart className="lg:col-span-8" />
        <div className="flex flex-col gap-4 lg:col-span-4 lg:gap-6">
          <ChannelDonut />
          <AnomalyFeed />
        </div>
      </div>

      {/* 4. Ops row: inventory + branches + pipeline + expiry tiers. */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-12 lg:gap-6">
        <InventoryTable className="lg:col-span-6" />
        <BranchList className="lg:col-span-3" />
        <div className="flex flex-col gap-4 lg:col-span-3 lg:gap-6">
          <PipelineHealthCard />
          <ExpiryExposureCard />
        </div>
      </div>

      {/* 5. Bottom row: full-width expiry heatmap calendar. */}
      <ExpiryHeatmap />
    </div>
  );
}
