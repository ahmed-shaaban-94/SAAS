"use client";

import dynamic from "next/dynamic";
import { LoadingCard } from "@/components/loading-card";

// Lazy-load dashboard components to keep bundle size manageable
const KPIGrid = dynamic(() => import("@/components/dashboard/kpi-grid").then(m => m.KPIGrid || m.default), { loading: () => <LoadingCard lines={2} /> });
const TrendKPICards = dynamic(() => import("@/components/dashboard/trend-kpi-cards").then(m => m.TrendKPICards || m.default), { loading: () => <LoadingCard lines={2} /> });
const DailyTrendChart = dynamic(() => import("@/components/dashboard/daily-trend-chart").then(m => m.DailyTrendChart || m.default), { loading: () => <LoadingCard lines={4} /> });
const MonthlyTrendChart = dynamic(() => import("@/components/dashboard/monthly-trend-chart").then(m => m.MonthlyTrendChart || m.default), { loading: () => <LoadingCard lines={4} /> });
const BillingBreakdownChart = dynamic(() => import("@/components/dashboard/billing-breakdown-chart").then(m => m.BillingBreakdownChart || m.default), { loading: () => <LoadingCard lines={4} /> });
const CustomerTypeChart = dynamic(() => import("@/components/dashboard/customer-type-chart").then(m => m.CustomerTypeChart || m.default), { loading: () => <LoadingCard lines={4} /> });
const CalendarHeatmap = dynamic(() => import("@/components/dashboard/calendar-heatmap").then(m => m.CalendarHeatmap || m.default), { loading: () => <LoadingCard lines={4} /> });
const WaterfallChart = dynamic(() => import("@/components/dashboard/waterfall-chart").then(m => m.WaterfallChart || m.default), { loading: () => <LoadingCard lines={4} /> });
const QuickRankings = dynamic(() => import("@/components/dashboard/quick-rankings").then(m => m.QuickRankings || m.default), { loading: () => <LoadingCard lines={6} /> });
const ForecastCard = dynamic(() => import("@/components/dashboard/forecast-card").then(m => m.ForecastCard || m.default), { loading: () => <LoadingCard lines={4} /> });
const TargetProgress = dynamic(() => import("@/components/dashboard/target-progress").then(m => m.TargetProgress || m.default), { loading: () => <LoadingCard lines={3} /> });
const TopMoversCard = dynamic(() => import("@/components/dashboard/top-movers-card").then(m => m.TopMoversCard || m.default), { loading: () => <LoadingCard lines={4} /> });
const NarrativeSummaryCard = dynamic(() => import("@/components/dashboard/narrative-summary-card").then(m => m.NarrativeSummaryCard || m.default), { loading: () => <LoadingCard lines={3} /> });

interface WidgetRendererProps {
  widgetKey: string;
}

export function WidgetRenderer({ widgetKey }: WidgetRendererProps) {
  switch (widgetKey) {
    case "kpi-grid":
      return <KPIGrid />;
    case "trend-kpis":
      return <TrendKPICards />;
    case "daily-trend":
      return <DailyTrendChart />;
    case "monthly-trend":
      return <MonthlyTrendChart />;
    case "billing-breakdown":
      return <BillingBreakdownChart />;
    case "customer-type":
      return <CustomerTypeChart />;
    case "calendar-heatmap":
      return <CalendarHeatmap />;
    case "waterfall":
      return <WaterfallChart />;
    case "top-products":
      return <QuickRankings type="products" />;
    case "top-customers":
      return <QuickRankings type="customers" />;
    case "top-staff":
      return <QuickRankings type="staff" />;
    case "forecast":
      return <ForecastCard />;
    case "target-progress":
      return <TargetProgress />;
    case "top-movers":
      return <TopMoversCard />;
    case "narrative":
      return <NarrativeSummaryCard />;
    default:
      return (
        <div className="flex h-full items-center justify-center text-sm text-text-secondary">
          Unknown widget: {widgetKey}
        </div>
      );
  }
}
