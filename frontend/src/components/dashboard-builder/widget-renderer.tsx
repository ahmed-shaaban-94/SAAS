"use client";

import type { ComponentType } from "react";
import dynamic from "next/dynamic";
import { LoadingCard } from "@/components/loading-card";

function load<P extends object = object>(
  loader: () => Promise<{ [key: string]: ComponentType<P> }>,
  name: string,
) {
  return dynamic<P>(
    () => loader().then((mod) => mod[name] ?? mod["default" as keyof typeof mod]),
    { loading: () => <LoadingCard lines={4} /> },
  );
}

const KPIGrid = load(() => import("@/components/dashboard/kpi-grid"), "KPIGrid");
const TrendKPICards = load(() => import("@/components/dashboard/trend-kpi-cards"), "TrendKPICards");
const DailyTrendChart = load(() => import("@/components/dashboard/daily-trend-chart"), "DailyTrendChart");
const MonthlyTrendChart = load(() => import("@/components/dashboard/monthly-trend-chart"), "MonthlyTrendChart");
const BillingBreakdownChart = load(() => import("@/components/dashboard/billing-breakdown-chart"), "BillingBreakdownChart");
const CustomerTypeChart = load(() => import("@/components/dashboard/customer-type-chart"), "CustomerTypeChart");
const CalendarHeatmap = load(() => import("@/components/dashboard/calendar-heatmap"), "CalendarHeatmap");
const WaterfallChart = load(() => import("@/components/dashboard/waterfall-chart"), "WaterfallChart");
const QuickRankings = load<{ type: string }>(() => import("@/components/dashboard/quick-rankings"), "QuickRankings");
const ForecastCard = load(() => import("@/components/dashboard/forecast-card"), "ForecastCard");
const TargetProgress = load(() => import("@/components/dashboard/target-progress"), "TargetProgress");
const TopMoversCard = load(() => import("@/components/dashboard/top-movers-card"), "TopMoversCard");
const NarrativeSummaryCard = load(() => import("@/components/dashboard/narrative-summary-card"), "NarrativeSummaryCard");

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
