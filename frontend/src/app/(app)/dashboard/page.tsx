import Link from "next/link";
import { Printer, TrendingUp, Trophy, PieChart, Zap, Target, Calendar } from "lucide-react";
import { Header } from "@/components/layout/header";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { PageTransition } from "@/components/layout/page-transition";
import { FilterBar } from "@/components/filters/filter-bar";
import { LoadingCard } from "@/components/loading-card";
import dynamic from "next/dynamic";

// Above-fold: regular imports (seen immediately)
import { KPIGrid } from "@/components/dashboard/kpi-grid";
import { DailyTrendChart } from "@/components/dashboard/daily-trend-chart";
import { MonthlyTrendChart } from "@/components/dashboard/monthly-trend-chart";
import { LastUpdated } from "@/components/dashboard/last-updated";

// Below-fold: lazy load with loading skeleton
const BillingBreakdownChart = dynamic(
  () => import("@/components/dashboard/billing-breakdown-chart").then(m => ({ default: m.BillingBreakdownChart })),
  { loading: () => <LoadingCard lines={3} /> },
);
const CustomerTypeChart = dynamic(
  () => import("@/components/dashboard/customer-type-chart").then(m => ({ default: m.CustomerTypeChart })),
  { loading: () => <LoadingCard lines={3} /> },
);
const QuickRankings = dynamic(
  () => import("@/components/dashboard/quick-rankings").then(m => ({ default: m.QuickRankings })),
  { loading: () => <LoadingCard lines={3} /> },
);
const TopMoversCard = dynamic(
  () => import("@/components/dashboard/top-movers-card").then(m => ({ default: m.TopMoversCard })),
  { loading: () => <LoadingCard lines={3} /> },
);
const CalendarHeatmap = dynamic(
  () => import("@/components/dashboard/calendar-heatmap").then(m => ({ default: m.CalendarHeatmap })),
  { loading: () => <LoadingCard lines={3} /> },
);
const EgyptMap = dynamic(
  () => import("@/components/dashboard/egypt-map").then(m => ({ default: m.EgyptMap })),
  { loading: () => <LoadingCard lines={3} /> },
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
      <div className="flex h-6 w-6 items-center justify-center rounded-md bg-accent/10">
        <Icon className="h-3.5 w-3.5 text-accent" />
      </div>
      <h2 className="text-[11px] font-semibold uppercase tracking-widest text-text-secondary">
        {title}
      </h2>
      <div className="flex-1 section-divider" />
    </div>
  );
}

export default function DashboardPage() {
  return (
    <PageTransition>
      <div>
        <Breadcrumbs />
        <div className="flex items-start justify-between">
          <Header
            title="Executive Overview"
            description="Sales performance at a glance"
          />
          <div className="flex items-center gap-3">
            <Link
              href="/dashboard/report"
              className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium text-text-secondary transition-all hover:bg-accent/10 hover:text-accent"
            >
              <Printer className="h-4 w-4" />
              Print Report
            </Link>
            <LastUpdated />
          </div>
        </div>
        <FilterBar />

        {/* Client boundary: single API call provides data to KPI + trends + rankings */}
        <DashboardContent>
          {/* KPI Section */}
          <KPIGrid />

          {/* Trends Section */}
          <div className="mt-10">
            <SectionHeader icon={TrendingUp} title="Trends" />
            <div className="mt-4 grid gap-6 lg:grid-cols-2">
              <DailyTrendChart />
              <MonthlyTrendChart />
            </div>
          </div>

          {/* Sales Distribution Section */}
          <div className="mt-10">
            <SectionHeader icon={PieChart} title="Sales Distribution" />
            <div className="mt-4 grid gap-6 lg:grid-cols-2">
              <BillingBreakdownChart />
              <CustomerTypeChart />
            </div>
          </div>

          {/* Rankings Section */}
          <div className="mt-10">
            <SectionHeader icon={Trophy} title="Top Performers" />
            <div className="mt-4">
              <QuickRankings />
            </div>
          </div>

          {/* Top Movers Section */}
          <div className="mt-10">
            <SectionHeader icon={Zap} title="Top Movers" />
            <div className="mt-4">
              <TopMoversCard />
            </div>
          </div>

          {/* Strategic Insights Section */}
          <div className="mt-10">
            <SectionHeader icon={Target} title="Goals & Forecast" />
            <div className="mt-4 grid gap-6 lg:grid-cols-2">
              <TargetProgress />
              <ForecastCard />
            </div>
          </div>

          {/* Geographic & Temporal Section */}
          <div className="mt-10">
            <SectionHeader icon={Calendar} title="Revenue Patterns" />
            <div className="mt-4 grid gap-6 lg:grid-cols-3">
              <div className="lg:col-span-2">
                <CalendarHeatmap />
              </div>
              <EgyptMap />
            </div>
          </div>
        </DashboardContent>
      </div>
    </PageTransition>
  );
}
