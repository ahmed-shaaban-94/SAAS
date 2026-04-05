import type { LayoutItem } from "@/hooks/use-dashboard-layout";

export interface WidgetDefinition {
  id: string;
  label: string;
  description: string;
  icon: string;
  defaultLayout: Pick<LayoutItem, "w" | "h" | "minW" | "minH">;
}

export const WIDGET_REGISTRY: WidgetDefinition[] = [
  {
    id: "kpi-grid",
    label: "KPI Cards",
    description: "Key performance indicators",
    icon: "LayoutDashboard",
    defaultLayout: { w: 12, h: 3, minW: 6, minH: 2 },
  },
  {
    id: "daily-trend",
    label: "Daily Trend",
    description: "Revenue and transaction trends",
    icon: "TrendingUp",
    defaultLayout: { w: 8, h: 4, minW: 4, minH: 3 },
  },
  {
    id: "top-products",
    label: "Top Products",
    description: "Best performing products",
    icon: "Package",
    defaultLayout: { w: 6, h: 5, minW: 4, minH: 3 },
  },
  {
    id: "top-customers",
    label: "Top Customers",
    description: "Best customers by revenue",
    icon: "Users",
    defaultLayout: { w: 6, h: 5, minW: 4, minH: 3 },
  },
  {
    id: "billing-breakdown",
    label: "Billing Breakdown",
    description: "Payment method distribution",
    icon: "CreditCard",
    defaultLayout: { w: 4, h: 4, minW: 3, minH: 3 },
  },
  {
    id: "calendar-heatmap",
    label: "Calendar Heatmap",
    description: "Transaction density by day",
    icon: "Calendar",
    defaultLayout: { w: 8, h: 4, minW: 6, minH: 3 },
  },
  {
    id: "top-movers",
    label: "Top Movers",
    description: "Biggest gainers and losers",
    icon: "ArrowUpDown",
    defaultLayout: { w: 6, h: 4, minW: 4, minH: 3 },
  },
  {
    id: "forecast",
    label: "Revenue Forecast",
    description: "AI-powered revenue forecast",
    icon: "Sparkles",
    defaultLayout: { w: 6, h: 4, minW: 4, minH: 3 },
  },
];

export const DEFAULT_LAYOUT: LayoutItem[] = [
  { i: "kpi-grid", x: 0, y: 0, w: 12, h: 3, minW: 6, minH: 2 },
  { i: "daily-trend", x: 0, y: 3, w: 8, h: 4, minW: 4, minH: 3 },
  { i: "billing-breakdown", x: 8, y: 3, w: 4, h: 4, minW: 3, minH: 3 },
  { i: "top-products", x: 0, y: 7, w: 6, h: 5, minW: 4, minH: 3 },
  { i: "top-customers", x: 6, y: 7, w: 6, h: 5, minW: 4, minH: 3 },
];
