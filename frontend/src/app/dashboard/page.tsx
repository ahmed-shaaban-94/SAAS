"use client";

/**
 * /dashboard — hybrid operations dashboard (v2 cutover).
 *
 * Composition:
 *   - Shell (sidebar + pulse bar) — conventional structure, editorial chrome
 *   - Header row: title + page-sub + compare toggle + print-report link
 *   - FilterBar (drives all dashboard data via FilterProvider context)
 *   - Onboarding strip + first-insight card (Phase 2 Golden Path, self-hide when done)
 *   - KPI row (4 stat cards wired to real summary + expiry data)
 *   - Money Map + Burning Cash + Medallion strip (signature v2 widgets)
 *
 * Previously lived at /dashboard-v2. That URL now redirects here.
 * The print report still lives at /dashboard/report under the legacy
 * (app) layout — it is a print-only surface and is intentionally not
 * migrated to v2 chrome.
 *
 * Golden-Path (Phase 2 #399) telemetry fires on mount so upload → first
 * insight latency stays measured after the cutover.
 */

import { useEffect } from "react";
import Link from "next/link";
import { Printer } from "lucide-react";

import { DashboardShell } from "@/components/dashboard-v2/shell";
import { KpiRow } from "@/components/dashboard-v2/kpi-row";
import { MoneyMap } from "@/components/dashboard-v2/money-map";
import { BurningCash } from "@/components/dashboard-v2/burning-cash";
import { MedallionStrip } from "@/components/dashboard-v2/medallion-strip";
import { OnboardingStrip } from "@/components/dashboard/onboarding-strip";
import { FirstInsightCard } from "@/components/dashboard/first-insight-card";
import { FilterBar } from "@/components/filters/filter-bar";
import {
  CompareProvider,
  CompareButton,
  ComparePanel,
} from "@/components/comparison/compare-toggle";
import { trackFirstDashboardView } from "@/lib/analytics-events";

export default function DashboardPage() {
  useEffect(() => {
    trackFirstDashboardView();
  }, []);

  return (
    <DashboardShell
      activeHref="/dashboard"
      breadcrumbs={[
        { label: "DataPulse", href: "/dashboard" },
        { label: "Overview" },
      ]}
    >
      <CompareProvider>
        <div className="page">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <h1 className="page-title">Good morning.</h1>
              <p className="page-sub">
                Tomorrow is forecasted at EGP 152K revenue. Four decisions
                worth reading before the 10am branch call.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <CompareButton />
              <Link
                href="/dashboard/report"
                className="flex items-center gap-1.5 rounded-xl px-3 py-2 text-sm font-medium text-text-secondary transition-all hover:text-accent"
                style={{ background: "rgba(255, 255, 255, 0.04)" }}
              >
                <Printer className="h-4 w-4" />
                <span className="hidden sm:inline">Print Report</span>
              </Link>
            </div>
          </div>

          <FilterBar />
          <ComparePanel />

          <OnboardingStrip />
          <FirstInsightCard />

          <KpiRow />

          <div className="widget-grid">
            <MoneyMap />
            <BurningCash />
            <MedallionStrip />
          </div>
        </div>
      </CompareProvider>
    </DashboardShell>
  );
}
