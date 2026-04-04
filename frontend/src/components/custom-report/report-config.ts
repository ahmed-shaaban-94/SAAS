import type { LucideIcon } from "lucide-react";
import {
  TrendingUp,
  Package,
  MapPin,
  Users,
  UserCog,
  CreditCard,
  Calendar,
  RotateCcw,
  Plus,
} from "lucide-react";

// ---- Friendly label maps ----

/** Map dimension API names to user-friendly labels */
export const DIMENSION_LABELS: Record<string, string> = {
  // Date
  year_month: "Month",
  year_quarter: "Quarter",
  year: "Year",
  day_of_week: "Day of Week",
  // Product
  drug_name: "Product Name",
  brand: "Brand",
  category: "Category",
  subcategory: "Sub-Category",
  division: "Division",
  segment: "Segment",
  // Customer
  customer_name: "Customer",
  // Site
  site_name: "Site",
  area_manager: "Area Manager",
  // Staff
  staff_name: "Staff",
  position: "Position",
  // Billing
  billing_type: "Payment Type",
  billing_group: "Payment Group",
  // Status
  status: "Status",
};

/** Map metric API names to user-friendly labels */
export const METRIC_LABELS: Record<string, string> = {
  total_net_sales: "Net Revenue",
  total_gross_sales: "Gross Sales",
  total_discount: "Total Discount",
  total_quantity: "Total Units",
  transaction_count: "Transactions",
  unique_customers: "Unique Customers",
  unique_products: "Unique Products",
  avg_order_value: "Avg. Order Value",
};

// ---- Dimension & Metric Groups ----

export interface FieldGroup {
  label: string;
  fields: string[];
}

export const DIMENSION_GROUPS: FieldGroup[] = [
  { label: "Time", fields: ["year_month", "year_quarter", "year", "day_of_week"] },
  { label: "Product", fields: ["drug_name", "brand", "category", "subcategory", "division", "segment"] },
  { label: "Customer", fields: ["customer_name"] },
  { label: "Location", fields: ["site_name", "area_manager"] },
  { label: "Staff", fields: ["staff_name", "position"] },
  { label: "Payment", fields: ["billing_type", "billing_group"] },
];

export const METRIC_GROUPS: FieldGroup[] = [
  { label: "Revenue", fields: ["total_net_sales", "total_gross_sales", "total_discount"] },
  { label: "Volume", fields: ["total_quantity", "transaction_count", "unique_customers", "unique_products"] },
  { label: "Averages", fields: ["avg_order_value"] },
];

// ---- Chart types ----

export type ChartType = "table" | "bar" | "line" | "pie";

// ---- Report Templates ----

export interface ReportTemplate {
  id: string;
  name: string;
  description: string;
  icon: LucideIcon;
  model: string;
  dimensions: string[];
  metrics: string[];
  chartType: ChartType;
}

export const REPORT_TEMPLATES: ReportTemplate[] = [
  {
    id: "sales-overview",
    name: "Sales Overview",
    description: "Revenue, orders & averages by month",
    icon: TrendingUp,
    model: "fct_sales",
    dimensions: ["year_month"],
    metrics: ["total_net_sales", "transaction_count", "avg_order_value", "total_quantity"],
    chartType: "line",
  },
  {
    id: "top-products",
    name: "Top Products",
    description: "Revenue, units & unique customers",
    icon: Package,
    model: "fct_sales",
    dimensions: ["drug_name"],
    metrics: ["total_net_sales", "total_quantity", "unique_customers", "avg_order_value"],
    chartType: "bar",
  },
  {
    id: "by-location",
    name: "By Location",
    description: "Revenue & transactions per site",
    icon: MapPin,
    model: "fct_sales",
    dimensions: ["site_name"],
    metrics: ["total_net_sales", "transaction_count", "unique_customers", "avg_order_value"],
    chartType: "bar",
  },
  {
    id: "customer-analysis",
    name: "Customers",
    description: "Spend, orders & basket size",
    icon: Users,
    model: "fct_sales",
    dimensions: ["customer_name"],
    metrics: ["total_net_sales", "transaction_count", "avg_order_value", "unique_products"],
    chartType: "table",
  },
  {
    id: "staff-performance",
    name: "Staff",
    description: "Revenue, orders & customer reach",
    icon: UserCog,
    model: "fct_sales",
    dimensions: ["staff_name"],
    metrics: ["total_net_sales", "transaction_count", "unique_customers", "avg_order_value"],
    chartType: "bar",
  },
  {
    id: "payment-methods",
    name: "Payments",
    description: "Revenue & order split by method",
    icon: CreditCard,
    model: "fct_sales",
    dimensions: ["billing_group"],
    metrics: ["total_net_sales", "transaction_count", "avg_order_value"],
    chartType: "pie",
  },
  {
    id: "monthly-trends",
    name: "Monthly",
    description: "Growth trends across metrics",
    icon: Calendar,
    model: "fct_sales",
    dimensions: ["year_month"],
    metrics: ["total_net_sales", "total_gross_sales", "total_quantity", "transaction_count"],
    chartType: "line",
  },
  {
    id: "returns-analysis",
    name: "Returns",
    description: "Return volume & value by product",
    icon: RotateCcw,
    model: "fct_sales",
    dimensions: ["drug_name"],
    metrics: ["total_quantity", "total_net_sales", "transaction_count"],
    chartType: "table",
  },
  {
    id: "from-scratch",
    name: "From Scratch",
    description: "Build your own",
    icon: Plus,
    model: "fct_sales",
    dimensions: [],
    metrics: [],
    chartType: "table",
  },
];

// ---- Helpers ----

export function friendlyDimensionLabel(name: string): string {
  return DIMENSION_LABELS[name] ?? name.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function friendlyMetricLabel(name: string): string {
  return METRIC_LABELS[name] ?? name.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function friendlyColumnLabel(name: string): string {
  return METRIC_LABELS[name] ?? DIMENSION_LABELS[name] ?? name.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}
