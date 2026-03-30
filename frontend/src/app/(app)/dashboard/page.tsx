import Link from "next/link";
import { Printer } from "lucide-react";
import { Header } from "@/components/layout/header";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { PageTransition } from "@/components/layout/page-transition";
import { KPIGrid } from "@/components/dashboard/kpi-grid";
import { DailyTrendChart } from "@/components/dashboard/daily-trend-chart";
import { MonthlyTrendChart } from "@/components/dashboard/monthly-trend-chart";
import { QuickRankings } from "@/components/dashboard/quick-rankings";
import { LastUpdated } from "@/components/dashboard/last-updated";
import { FilterBar } from "@/components/filters/filter-bar";

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
              className="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium text-text-secondary transition-colors hover:bg-divider hover:text-text-primary"
            >
              <Printer className="h-4 w-4" />
              Print Report
            </Link>
            <LastUpdated />
          </div>
        </div>
        <FilterBar />
        <KPIGrid />
        <div className="mt-6 grid gap-6 lg:grid-cols-2">
          <DailyTrendChart />
          <MonthlyTrendChart />
        </div>
        <div className="mt-6">
          <QuickRankings />
        </div>
      </div>
    </PageTransition>
  );
}
