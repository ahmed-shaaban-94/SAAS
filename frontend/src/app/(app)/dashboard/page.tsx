import Link from "next/link";
import { Printer, TrendingUp, Trophy, PieChart, Zap } from "lucide-react";
import { Header } from "@/components/layout/header";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { PageTransition } from "@/components/layout/page-transition";
import { KPIGrid } from "@/components/dashboard/kpi-grid";
import { DailyTrendChart } from "@/components/dashboard/daily-trend-chart";
import { MonthlyTrendChart } from "@/components/dashboard/monthly-trend-chart";
import { QuickRankings } from "@/components/dashboard/quick-rankings";
import { BillingBreakdownChart } from "@/components/dashboard/billing-breakdown-chart";
import { CustomerTypeChart } from "@/components/dashboard/customer-type-chart";
import { TopMoversCard } from "@/components/dashboard/top-movers-card";
import { LastUpdated } from "@/components/dashboard/last-updated";
import { FilterBar } from "@/components/filters/filter-bar";

function SectionHeader({ icon: Icon, title }: { icon: React.ComponentType<{ className?: string }>; title: string }) {
  return (
    <div className="flex items-center gap-2.5">
      <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-accent/10">
        <Icon className="h-4 w-4 text-accent" />
      </div>
      <h2 className="text-sm font-semibold uppercase tracking-wider text-text-secondary">
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

        {/* KPI Section */}
        <KPIGrid />

        {/* Trends Section */}
        <div className="mt-8">
          <SectionHeader icon={TrendingUp} title="Trends" />
          <div className="mt-4 grid gap-6 lg:grid-cols-2">
            <DailyTrendChart />
            <MonthlyTrendChart />
          </div>
        </div>

        {/* Sales Distribution Section */}
        <div className="mt-8">
          <SectionHeader icon={PieChart} title="Sales Distribution" />
          <div className="mt-4 grid gap-6 lg:grid-cols-2">
            <BillingBreakdownChart />
            <CustomerTypeChart />
          </div>
        </div>

        {/* Rankings Section */}
        <div className="mt-8">
          <SectionHeader icon={Trophy} title="Top Performers" />
          <div className="mt-4">
            <QuickRankings />
          </div>
        </div>

        {/* Top Movers Section */}
        <div className="mt-8">
          <SectionHeader icon={Zap} title="Top Movers" />
          <div className="mt-4">
            <TopMoversCard />
          </div>
        </div>
      </div>
    </PageTransition>
  );
}
