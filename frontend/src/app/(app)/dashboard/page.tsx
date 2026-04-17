"use client";

import { useEffect } from "react";
import Link from "next/link";
import { Printer, TrendingUp, Target, Calendar } from "lucide-react";
import { Header } from "@/components/layout/header";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { PageTransition } from "@/components/layout/page-transition";
import { FilterBar } from "@/components/filters/filter-bar";
import { LoadingCard } from "@/components/loading-card";
import { CompareProvider, CompareButton, ComparePanel } from "@/components/comparison/compare-toggle";
import { trackFirstDashboardView } from "@/lib/analytics-events";
import { FirstInsightCard } from "@/components/dashboard/first-insight-card";
import { OnboardingStrip } from "@/components/dashboard/onboarding-strip";
import dynamic from "next/dynamic";

// Above-fold: regular imports (seen immediately)
import { DayHeroConnected } from "@/components/dashboard/day-hero-connected";
import { KPIGrid } from "@/components/dashboard/kpi-grid";
import { NarrativeSummaryCard } from "@/components/dashboard/narrative-summary-card";
import { DailyTrendChart } from "@/components/dashboard/daily-trend-chart";
import { LastUpdated } from "@/components/dashboard/last-updated";
import { LazySection } from "@/components/dashboard/lazy-section";

// Below-fold: lazy load with loading skeleton
const TopMoversCard = dynamic(
  () => import("@/components/dashboard/top-movers-card").then(m => ({ default: m.TopMoversCard })),
  { loading: () => <LoadingCard lines={3} /> },
);
const WhyChangedPanel = dynamic(
  () => import("@/components/dashboard/why-changed-panel").then(m => ({ default: m.WhyChangedPanel })),
  { loading: () => <LoadingCard lines={4} />, ssr: false },
);
const CalendarHeatmap = dynamic(
  () => import("@/components/dashboard/calendar-heatmap").then(m => ({ default: m.CalendarHeatmap })),
  { loading: () => <LoadingCard lines={3} />, ssr: false },
);
const EgyptMap = dynamic(
  () => import("@/components/dashboard/egypt-map").then(m => ({ default: m.EgyptMap })),
  { loading: () => <LoadingCard lines={3} />, ssr: false },
);
const TargetProgress = dynamic(
  () => import("@/components/dashboard/target-progress").then(m => ({ default: m.TargetProgress })),
  { loading: () => <LoadingCard lines={3} /> },
);
const ForecastCard = dynamic(
  () => import("@/components/dashboard/forecast-card").then(m => ({ default: m.ForecastCard })),
  { loading: () => <LoadingCard lines={3} /> },
);

// Client wrapper that provides composite dashboard data via context
import { DashboardContent } from "./dashboard-content";

function SectionHeader({ icon: Icon, title }: { icon: React.ComponentType<{ className?: string }>; title: string }) {
  return (
    <div className="flex items-center gap-2">
      <div className="viz-panel-soft flex h-8 w-8 items-center justify-center rounded-xl">
        <Icon className="h-3.5 w-3.5 text-accent" />
      </div>
      <h2 className="text-[11px] font-semibold uppercase tracking-[0.24em] text-text-secondary">
        {title}
      </h2>
      <div className="flex-1 section-divider" />
    </div>
  );
}

export default function DashboardPage() {
  // Golden-Path instrumentation: fire first_dashboard_view once per session.
  // See Phase 2 Task 0 (#399).
  useEffect(() => {
    trackFirstDashboardView();
  }, []);

  return (
    <PageTransition>
      <CompareProvider>
      <div>
        <Breadcrumbs />
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <Header
            title="Executive Overview"
            description="Sales performance at a glance"
          />
          <div className="flex items-center gap-2 sm:gap-3">
            <CompareButton />
            <Link
              href="/dashboard/report"
              className="viz-panel-soft flex items-center gap-1.5 rounded-xl px-3 py-2 text-sm font-medium text-text-secondary transition-all hover:text-accent"
            >
              <Printer className="h-4 w-4" />
              <span className="hidden sm:inline">Print Report</span>
            </Link>
            <LastUpdated />
          </div>
        </div>
        <FilterBar />
        <ComparePanel />

        {/* Phase 2 #404: onboarding progress strip — self-hides when all done or stale. */}
        <OnboardingStrip />

        {/* Phase 2 #402: first-insight card — self-hides when no insight or dismissed. */}
        <FirstInsightCard />

        {/* Client boundary: single API call provides data to KPI + trends + rankings */}
        <DashboardContent>
          {/* ── Row 1: Hero Snapshot + AI Summary ── */}
          <div className="grid gap-4 lg:grid-cols-3">
            <div className="lg:col-span-2">
              <DayHeroConnected />
            </div>
            <NarrativeSummaryCard />
          </div>

          {/* ── Row 2: Primary KPIs (4 cards) ── */}
          <KPIGrid />

          {/* ── Row 3: Trends + Intelligence Rail ── */}
          <div className="mt-8">
            <SectionHeader icon={TrendingUp} title="Trends & Intelligence" />
            <div className="mt-4 grid gap-4 lg:grid-cols-3">
              <div className="lg:col-span-2">
                <DailyTrendChart />
              </div>
              <div className="space-y-4">
                <TopMoversCard />
                <WhyChangedPanel />
              </div>
            </div>
          </div>

          {/* ── Row 4: Goals & Forecast ── */}
          <LazySection minHeight="280px">
            <div className="mt-8">
              <SectionHeader icon={Target} title="Goals & Forecast" />
              <div className="mt-4 grid gap-4 lg:grid-cols-2">
                <TargetProgress />
                <ForecastCard />
              </div>
            </div>
          </LazySection>

          {/* ── Row 5: Revenue Patterns ── */}
          <LazySection minHeight="300px">
            <div className="mt-8">
              <SectionHeader icon={Calendar} title="Revenue Patterns" />
              <div className="mt-4 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                <div className="md:col-span-2">
                  <CalendarHeatmap />
                </div>
                <EgyptMap />
              </div>
            </div>
          </LazySection>
        </DashboardContent>
      </div>
      </CompareProvider>
    </PageTransition>
  );
}
