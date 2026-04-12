/**
 * Widget catalog — definitions for all available dashboard widgets.
 * Each widget has a unique key, display info, default grid size, and
 * a reference to the React component that renders it.
 */

export interface WidgetDef {
  key: string;
  label: string;
  description: string;
  icon: string;
  category: "kpi" | "chart" | "table" | "insight";
  defaultW: number;
  defaultH: number;
  minW: number;
  minH: number;
}

export const WIDGET_CATALOG: WidgetDef[] = [
  // KPI widgets
  {
    key: "kpi-grid",
    label: "KPI Cards",
    description: "Revenue, orders, customers, growth",
    icon: "BarChart3",
    category: "kpi",
    defaultW: 4,
    defaultH: 2,
    minW: 2,
    minH: 2,
  },
  {
    key: "trend-kpis",
    label: "Trend KPI Cards",
    description: "KPIs with sparkline trends",
    icon: "TrendingUp",
    category: "kpi",
    defaultW: 4,
    defaultH: 2,
    minW: 2,
    minH: 2,
  },
  // Chart widgets
  {
    key: "daily-trend",
    label: "Daily Revenue Trend",
    description: "Line chart of daily revenue",
    icon: "LineChart",
    category: "chart",
    defaultW: 2,
    defaultH: 4,
    minW: 2,
    minH: 2,
  },
  {
    key: "monthly-trend",
    label: "Monthly Revenue Trend",
    description: "Bar chart of monthly revenue",
    icon: "BarChartBig",
    category: "chart",
    defaultW: 2,
    defaultH: 4,
    minW: 2,
    minH: 2,
  },
  {
    key: "billing-breakdown",
    label: "Billing Breakdown",
    description: "Revenue by payment method",
    icon: "PieChart",
    category: "chart",
    defaultW: 2,
    defaultH: 3,
    minW: 1,
    minH: 2,
  },
  {
    key: "customer-type",
    label: "Customer Type",
    description: "New vs returning customers",
    icon: "Users",
    category: "chart",
    defaultW: 2,
    defaultH: 3,
    minW: 1,
    minH: 2,
  },
  {
    key: "calendar-heatmap",
    label: "Calendar Heatmap",
    description: "Revenue heatmap by day",
    icon: "Calendar",
    category: "chart",
    defaultW: 4,
    defaultH: 3,
    minW: 3,
    minH: 2,
  },
  {
    key: "waterfall",
    label: "Waterfall Chart",
    description: "Revenue waterfall breakdown",
    icon: "BarChart3",
    category: "chart",
    defaultW: 2,
    defaultH: 3,
    minW: 2,
    minH: 2,
  },
  // Table widgets
  {
    key: "top-products",
    label: "Top Products",
    description: "Best selling products table",
    icon: "Package",
    category: "table",
    defaultW: 2,
    defaultH: 4,
    minW: 2,
    minH: 3,
  },
  {
    key: "top-customers",
    label: "Top Customers",
    description: "Highest revenue customers",
    icon: "Users",
    category: "table",
    defaultW: 2,
    defaultH: 4,
    minW: 2,
    minH: 3,
  },
  {
    key: "top-staff",
    label: "Top Staff",
    description: "Top performing staff members",
    icon: "UserCog",
    category: "table",
    defaultW: 2,
    defaultH: 4,
    minW: 2,
    minH: 3,
  },
  // Insight widgets
  {
    key: "forecast",
    label: "Revenue Forecast",
    description: "AI-powered revenue forecast",
    icon: "Sparkles",
    category: "insight",
    defaultW: 2,
    defaultH: 3,
    minW: 2,
    minH: 2,
  },
  {
    key: "target-progress",
    label: "Target Progress",
    description: "Goals vs actual performance",
    icon: "Target",
    category: "insight",
    defaultW: 2,
    defaultH: 2,
    minW: 1,
    minH: 2,
  },
  {
    key: "top-movers",
    label: "Top Movers",
    description: "Biggest gainers and losers",
    icon: "ArrowUpDown",
    category: "insight",
    defaultW: 2,
    defaultH: 3,
    minW: 2,
    minH: 2,
  },
  {
    key: "narrative",
    label: "AI Narrative",
    description: "AI-generated business summary",
    icon: "MessageSquare",
    category: "insight",
    defaultW: 4,
    defaultH: 2,
    minW: 2,
    minH: 2,
  },
];

export const CATEGORY_LABELS: Record<string, string> = {
  kpi: "KPIs",
  chart: "Charts",
  table: "Tables",
  insight: "Insights",
};
