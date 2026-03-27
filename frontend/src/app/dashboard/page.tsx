import { Header } from "@/components/layout/header";
import { KPIGrid } from "@/components/dashboard/kpi-grid";
import { DailyTrendChart } from "@/components/dashboard/daily-trend-chart";
import { MonthlyTrendChart } from "@/components/dashboard/monthly-trend-chart";
import { FilterBar } from "@/components/filters/filter-bar";

export default function DashboardPage() {
  return (
    <div>
      <Header
        title="Executive Overview"
        description="Sales performance at a glance"
      />
      <FilterBar />
      <KPIGrid />
      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <DailyTrendChart />
        <MonthlyTrendChart />
      </div>
    </div>
  );
}
