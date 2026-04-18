/**
 * Dashboard v2 — preview of the hybrid operations dashboard.
 *
 * Composition:
 *   - Shell (sidebar + pulse bar) — conventional structure, editorial chrome
 *   - KPI row (4 stat cards)
 *   - Money Map + Burning Cash (signature widgets from Dashboard.html design)
 *   - Medallion strip (compact pipeline-health summary)
 *
 * This page uses mock data so the design can be reviewed without backend
 * integration. Once approved, each widget swaps in its real data hook.
 */

import { DashboardShell } from "@/components/dashboard-v2/shell";
import { KpiRow } from "@/components/dashboard-v2/kpi-row";
import { MoneyMap } from "@/components/dashboard-v2/money-map";
import { BurningCash } from "@/components/dashboard-v2/burning-cash";
import { MedallionStrip } from "@/components/dashboard-v2/medallion-strip";

export default function DashboardV2Page() {
  return (
    <DashboardShell
      activeHref="/dashboard-v2"
      breadcrumbs={[
        { label: "DataPulse", href: "/dashboard-v2" },
        { label: "Overview" },
      ]}
    >
      <div className="page">
        <div>
          <h1 className="page-title">Good morning.</h1>
          <p className="page-sub">
            Tomorrow is forecasted at EGP 152K revenue. Four decisions worth
            reading before the 10am branch call.
          </p>
        </div>

        <KpiRow />

        <div className="widget-grid">
          <MoneyMap />
          <BurningCash />
          <MedallionStrip />
        </div>
      </div>
    </DashboardShell>
  );
}
