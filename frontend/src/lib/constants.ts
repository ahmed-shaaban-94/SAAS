export const CHART_COLORS = [
  "#00BFA5", "#2196F3", "#FFB300", "#E91E63",
  "#9C27B0", "#FF5722", "#00ACC1", "#8BC34A",
] as const;

export const CHART_MAX_ITEMS = 10;

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "";

export const NAV_ITEMS = [
  { label: "Overview", href: "/dashboard", icon: "LayoutDashboard" },
  { label: "Goals", href: "/goals", icon: "Target" },
  { label: "Explore", href: "/explore", icon: "Compass" },
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
