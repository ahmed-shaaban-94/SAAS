"use client";

/**
 * Dashboard v2 — hybrid operations dashboard.
 *
 * Composition:
 *   - Shell (sidebar + pulse bar) — conventional structure, editorial chrome
 *   - Horizon mode toggle in page header — switches the dashboard between
 *     today's values and forecasted values with confidence bands
 *   - KPI row (4 stat cards) — adapts to horizon mode
 *   - Money Map + Burning Cash (signature widgets from Dashboard.html design)
 *   - Medallion strip (compact pipeline-health summary)
 */

import { DashboardShell } from "@/components/dashboard-v2/shell";
import { KpiRow } from "@/components/dashboard-v2/kpi-row";
import { MoneyMap } from "@/components/dashboard-v2/money-map";
import { BurningCash } from "@/components/dashboard-v2/burning-cash";
import { MedallionStrip } from "@/components/dashboard-v2/medallion-strip";
import { HorizonProvider } from "@/components/horizon/horizon-context";
import { HorizonToggle } from "@/components/horizon/horizon-toggle";

export default function DashboardV2Page() {
  return (
    <HorizonProvider>
      <DashboardShell
        activeHref="/dashboard-v2"
        breadcrumbs={[
          { label: "DataPulse", href: "/dashboard-v2" },
          { label: "Overview" },
        ]}
      >
        <div className="page">
          <div className="page-header">
            <div className="title-group">
              <h1 className="page-title">Good morning.</h1>
              <p className="page-sub">
                Tomorrow is forecasted at EGP 152K revenue. Four decisions worth
                reading before the 10am branch call.
              </p>
            </div>
            <HorizonToggle />
          </div>

          <KpiRow />

          <div className="widget-grid">
            <MoneyMap />
            <BurningCash />
            <MedallionStrip />
          </div>
        </div>
      </DashboardShell>
    </HorizonProvider>
  );
}
