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

// ── Role hierarchy ────────────────────────────────────────
import type { RoleKey } from "@/types/members";

export const ROLE_HIERARCHY: Record<RoleKey, number> = {
  viewer: 0,
  editor: 1,
  admin: 2,
  owner: 3,
} as const;

/** Returns true if userRole >= requiredRole in the hierarchy */
export function hasMinRole(userRole: RoleKey, requiredRole: RoleKey): boolean {
  return ROLE_HIERARCHY[userRole] >= ROLE_HIERARCHY[requiredRole];
}

// ── Navigation types ──────────────────────────────────────
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

// ── Feature flags ────────────────────────────────────────
// Mirrors backend `feature_control_center` setting. Pages themselves
// land in Phase 1b; keeping the nav group behind a flag avoids dead
// links when only the backend READ routes exist.
const FEATURE_CONTROL_CENTER =
  process.env.NEXT_PUBLIC_FEATURE_CONTROL_CENTER === "true";
const FEATURE_PLATFORM =
  process.env.NEXT_PUBLIC_FEATURE_PLATFORM === "true";

// ── Grouped navigation ───────────────────────────────────
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
  ...(FEATURE_PLATFORM ? [OPERATIONS_GROUP] : []),
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
  ...(FEATURE_CONTROL_CENTER ? [CONTROL_CENTER_GROUP] : []),
];

/** Flat list derived from groups — backward compatible */
export const NAV_ITEMS = NAV_GROUPS.flatMap((g) => g.items);
