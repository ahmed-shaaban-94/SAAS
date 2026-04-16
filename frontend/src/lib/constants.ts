/**
 * Chart palette — indexed by position.
 * Semi-transparent fills (via CSS opacity or alpha channel) are derived in
 * each chart component, so we only store the solid base colour here.
 */
export const CHART_COLORS = [
  "#06b6d4", // cyan-500
  "#8b5cf6", // violet-500
  "#f59e0b", // amber-500
  "#10b981", // emerald-500
  "#ef4444", // red-500
  "#3b82f6", // blue-500
  "#ec4899", // pink-500
  "#14b8a6", // teal-500
  "#f97316", // orange-500
  "#a855f7", // purple-500
] as const;

/** ISO weekday labels for Recharts tooltips / axes. */
export const WEEKDAY_LABELS = [
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
  "Sunday",
] as const;

/** Standard grid breakpoints used by KPI cards and chart grids. */
export const GRID_BREAKPOINTS = {
  sm: 640,
  md: 768,
  lg: 1024,
  xl: 1280,
} as const;

export type RoleKey = "owner" | "admin" | "editor" | "viewer";
export interface NavItem {
  label: string;
  href: string;
  icon: string;
  minRole: RoleKey;
}
export interface NavGroup {
  id: string;
  label: string;
  icon: string;
  minRole: RoleKey;
  items: NavItem[];
}

// ── Grouped navigation ───────────────────────────────────
const OPERATIONS_GROUP: NavGroup = {
  id: "operations",
  label: "Operations",
  icon: "Warehouse",
  minRole: "editor",
  items: [
    { label: "Inventory", href: "/inventory", icon: "Package", minRole: "editor" },
    { label: "Dispensing", href: "/dispensing", icon: "Activity", minRole: "viewer" },
    { label: "Expiry Tracking", href: "/expiry", icon: "Calendar", minRole: "editor" },
    { label: "Purchase Orders", href: "/purchase-orders", icon: "ClipboardList", minRole: "editor" },
    { label: "Suppliers", href: "/suppliers", icon: "Truck", minRole: "editor" },
  ],
};

const CONTROL_CENTER_GROUP: NavGroup = {
  id: "control-center",
  label: "Control Center",
  icon: "Settings2",
  minRole: "admin",
  items: [
    { label: "Sources",   href: "/control-center/sources",   icon: "Plug",              minRole: "admin"  },
    { label: "Profiles",  href: "/control-center/profiles",  icon: "SlidersHorizontal", minRole: "admin"  },
    { label: "Mappings",  href: "/control-center/mappings",  icon: "GitBranch",         minRole: "editor" },
    { label: "Releases",  href: "/control-center/releases",  icon: "History",           minRole: "admin"  },
    { label: "Sync Runs", href: "/control-center/sync-runs", icon: "Activity",          minRole: "admin"  },
  ],
};

export const NAV_GROUPS: NavGroup[] = [
  {
    id: "analytics",
    label: "Analytics",
    icon: "BarChart3",
    minRole: "viewer",
    items: [
      { label: "Overview", href: "/dashboard", icon: "LayoutDashboard", minRole: "viewer" },
      { label: "Executive Briefing", href: "/briefing", icon: "Briefcase", minRole: "viewer" },
      { label: "My Dashboard", href: "/my-dashboard", icon: "LayoutGrid", minRole: "viewer" },
      { label: "Custom Report", href: "/custom-report", icon: "BarChartBig", minRole: "viewer" },
      { label: "Reports", href: "/reports", icon: "FileBarChart", minRole: "viewer" },
      { label: "Goals", href: "/goals", icon: "Target", minRole: "viewer" },
    ],
  },
  {
    id: "dimensions",
    label: "Dimensions",
    icon: "Database",
    minRole: "viewer",
    items: [
      { label: "Products", href: "/products", icon: "Package", minRole: "viewer" },
      { label: "Customers", href: "/customers", icon: "Users", minRole: "viewer" },
      { label: "Staff", href: "/staff", icon: "UserCog", minRole: "viewer" },
      { label: "Sites", href: "/sites", icon: "Building2", minRole: "viewer" },
      { label: "Returns", href: "/returns", icon: "RotateCcw", minRole: "viewer" },
    ],
  },
  {
    id: "intelligence",
    label: "Intelligence",
    icon: "Brain",
    minRole: "viewer",
    items: [
      { label: "Insights", href: "/insights", icon: "Sparkles", minRole: "viewer" },
      { label: "Alerts", href: "/alerts", icon: "Bell", minRole: "viewer" },
      { label: "What-If", href: "/scenarios", icon: "FlaskConical", minRole: "viewer" },
    ],
  },
  {
    id: "data-ops",
    label: "Data Ops",
    icon: "Workflow",
    minRole: "editor",
    items: [
      { label: "Import Data", href: "/upload", icon: "Upload", minRole: "editor" },
      { label: "Data Quality", href: "/quality", icon: "ShieldCheck", minRole: "editor" },
      { label: "Data Lineage", href: "/lineage", icon: "GitBranch", minRole: "editor" },
    ],
  },
  {
    id: "collaboration",
    label: "Collaboration",
    icon: "Users2",
    minRole: "editor",
    items: [
      { label: "Team", href: "/team", icon: "Shield", minRole: "admin" },
      { label: "Gamification", href: "/gamification", icon: "Trophy", minRole: "editor" },
      { label: "Audit Log", href: "/audit", icon: "ScrollText", minRole: "editor" },
    ],
  },
  OPERATIONS_GROUP,
  {
    id: "settings",
    label: "Settings",
    icon: "Settings",
    minRole: "admin",
    items: [
      { label: "Branding", href: "/branding", icon: "Palette", minRole: "admin" },
      { label: "Billing", href: "/billing", icon: "CreditCard", minRole: "owner" },
    ],
  },
  CONTROL_CENTER_GROUP,
];

/** Flat list derived from groups — backward compatible */
export const NAV_ITEMS = NAV_GROUPS.flatMap((g) => g.items);
