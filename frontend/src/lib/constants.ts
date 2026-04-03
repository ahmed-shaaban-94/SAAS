export const CHART_COLORS = [
  "#4F46E5", "#D97706", "#8B5CF6", "#0891B2",
  "#059669", "#6366F1", "#EA580C", "#2563EB",
] as const;

export const CHART_MAX_ITEMS = 10;

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "";

export const NAV_ITEMS = [
  { label: "Overview", href: "/dashboard", icon: "LayoutDashboard" },
  { label: "Goals", href: "/goals", icon: "Target" },
  { label: "Explore", href: "/explore", icon: "Compass" },
  { label: "SQL Lab", href: "/sql-lab", icon: "Terminal" },
  { label: "Products", href: "/products", icon: "Package" },
  { label: "Customers", href: "/customers", icon: "Users" },
  { label: "Staff", href: "/staff", icon: "UserCog" },
  { label: "Sites", href: "/sites", icon: "Building2" },
  { label: "Returns", href: "/returns", icon: "RotateCcw" },
  { label: "Reports", href: "/reports", icon: "FileBarChart" },
  { label: "Pipeline", href: "/pipeline", icon: "GitBranch" },
  { label: "Alerts", href: "/alerts", icon: "Bell" },
  { label: "Insights", href: "/insights", icon: "Sparkles" },
  { label: "Billing", href: "/billing", icon: "CreditCard" },
] as const;
