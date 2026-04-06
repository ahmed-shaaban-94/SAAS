/**
 * Chart palette — indexed by position.
 * These are used as Recharts SVG fill/stroke values (CSS vars don't work in SVG).
 * Light and dark variants are provided; use `useChartTheme()` to select.
 */
export const CHART_COLORS_LIGHT = [
  "#4F46E5", "#D97706", "#8B5CF6", "#0891B2",
  "#059669", "#6366F1", "#EA580C", "#2563EB",
] as const;

export const CHART_COLORS_DARK = [
  "#6366F1", "#E5A00D", "#A78BFA", "#22D3EE",
  "#34D399", "#818CF8", "#FB923C", "#60A5FA",
] as const;

/** @deprecated Use CHART_COLORS_LIGHT/DARK with useChartTheme().
 *  Kept for backward compatibility with components not yet migrated. */
export const CHART_COLORS = CHART_COLORS_LIGHT;

export const CHART_MAX_ITEMS = 10;

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "";

export const NAV_ITEMS = [
  { label: "Overview", href: "/dashboard", icon: "LayoutDashboard" },
  { label: "Goals", href: "/goals", icon: "Target" },
  { label: "Custom Report", href: "/custom-report", icon: "BarChartBig" },
  { label: "Products", href: "/products", icon: "Package" },
  { label: "Customers", href: "/customers", icon: "Users" },
  { label: "Staff", href: "/staff", icon: "UserCog" },
  { label: "Sites", href: "/sites", icon: "Building2" },
  { label: "Returns", href: "/returns", icon: "RotateCcw" },
  { label: "Reports", href: "/reports", icon: "FileBarChart" },
  { label: "Alerts", href: "/alerts", icon: "Bell" },
  { label: "Insights", href: "/insights", icon: "Sparkles" },
  { label: "Billing", href: "/billing", icon: "CreditCard" },
] as const;
