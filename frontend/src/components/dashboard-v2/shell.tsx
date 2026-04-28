"use client";

/**
 * Dashboard v2 shell — sidebar + pulse bar + page chrome.
 *
 * Layered approach:
 *   - Sidebar is data-driven from `NAV_GROUPS` in `@/lib/constants` so
 *     it stays aligned with the legacy (app)/layout.tsx sidebar and
 *     surfaces all 9 navigation groups (Analytics, Dimensions,
 *     Intelligence, Data Ops, Collaboration, Settings, Operations,
 *     POS, Control Center). Adding a new route to NAV_GROUPS lights it
 *     up automatically in both sidebars.
 *   - Pulse bar chrome from Dashboard.html (animated ECG at the top of
 *     every page, app-level).
 *   - Responsive behavior: below 1024px the sidebar becomes a
 *     slide-in drawer triggered by a hamburger button. Above 1024px it
 *     is a permanent column with an optional collapse toggle
 *     (240px ↔ 68px). ESC + backdrop tap + swipe-left close the drawer.
 *     Route change also auto-closes the drawer (so users don't see the
 *     drawer overlay the page they just navigated to).
 *
 * History: this file previously hard-coded its own 4-section nav
 * (`NAV_SECTIONS`) which orphaned ~32 migrated routes after PR #564.
 * PR #567 switched to data-driven NAV_GROUPS; PR #569 added the
 * responsive layer on top. Both changes coexist here.
 */

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  BarChart3,
  BarChartBig,
  Bell,
  Brain,
  Briefcase,
  Building2,
  Calendar,
  ChevronLeft,
  ChevronRight,
  ClipboardList,
  Clock,
  CreditCard,
  Database,
  FileBarChart,
  FlaskConical,
  GitBranch,
  History,
  LayoutDashboard,
  LayoutGrid,
  Menu,
  Monitor,
  Package,
  Palette,
  Plug,
  Receipt,
  RotateCcw,
  ScrollText,
  Settings,
  Settings2,
  Shield,
  ShieldCheck,
  ShoppingCart,
  SlidersHorizontal,
  Sparkles,
  Target,
  Trophy,
  Truck,
  Upload,
  UserCog,
  Users,
  Users2,
  Warehouse,
  Workflow,
  X,
} from "lucide-react";
import { VISIBLE_NAV_GROUPS } from "@/lib/constants";
import "./dashboard-v2.css";

/**
 * Shared icon registry — mirrors the one in
 * `@/components/layout/sidebar.tsx` so both sidebars resolve the same
 * string keys defined in NAV_GROUPS. When NAV_GROUPS gains a new icon
 * name, add it to both registries or extract this to a shared module.
 */
const ICON_MAP: Record<string, React.ComponentType<{ size?: number | string }>> = {
  Activity,
  BarChart3,
  BarChartBig,
  Bell,
  Brain,
  Briefcase,
  Building2,
  Calendar,
  ClipboardList,
  Clock,
  CreditCard,
  Database,
  FileBarChart,
  FlaskConical,
  GitBranch,
  History,
  LayoutDashboard,
  LayoutGrid,
  Monitor,
  Package,
  Palette,
  Plug,
  Receipt,
  RotateCcw,
  ScrollText,
  Settings,
  Settings2,
  Shield,
  ShieldCheck,
  ShoppingCart,
  SlidersHorizontal,
  Sparkles,
  Target,
  Trophy,
  Truck,
  Upload,
  UserCog,
  Users,
  Users2,
  Warehouse,
  Workflow,
};

function LogoMark() {
  return (
    <span className="brand-mark">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
        <path
          d="M3 13h3l2-6 4 12 3-8 2 4h4"
          stroke="#f7fbff"
          strokeWidth="2.2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    </span>
  );
}

interface SidebarProps {
  activeHref?: string;
  mobileOpen: boolean;
  onMobileClose: () => void;
  collapsed: boolean;
  onToggleCollapse: () => void;
}

function Sidebar({
  activeHref,
  mobileOpen,
  onMobileClose,
  collapsed,
  onToggleCollapse,
}: SidebarProps) {
  const touchStartX = useRef<number | null>(null);

  function handleTouchStart(e: React.TouchEvent) {
    touchStartX.current = e.touches[0].clientX;
  }
  function handleTouchEnd(e: React.TouchEvent) {
    if (touchStartX.current === null) return;
    const deltaX = e.changedTouches[0].clientX - touchStartX.current;
    if (deltaX < -60) onMobileClose();
    touchStartX.current = null;
  }

  useEffect(() => {
    if (!mobileOpen) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onMobileClose();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [mobileOpen, onMobileClose]);

  return (
    <aside
      className={`side${mobileOpen ? " open" : ""}${collapsed ? " collapsed" : ""}`}
      role="navigation"
      aria-label="Primary navigation"
      onTouchStart={handleTouchStart}
      onTouchEnd={handleTouchEnd}
    >
      <div className="side-header">
        <Link href="/dashboard" className="brand">
          <LogoMark />
          {!collapsed && <span>DataPulse</span>}
        </Link>

        {/* Mobile close button — visible only inside the drawer (CSS) */}
        <button
          type="button"
          className="side-close"
          onClick={onMobileClose}
          aria-label="Close menu"
        >
          <X size={18} />
        </button>

        {/* Desktop collapse toggle — hidden on mobile by CSS */}
        <button
          type="button"
          className="side-collapse"
          onClick={onToggleCollapse}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
        </button>
      </div>

      {VISIBLE_NAV_GROUPS.map((group) => (
        <div key={group.id}>
          {!collapsed && <div className="nav-section">{group.label}</div>}
          {group.items.map((item) => {
            const Icon = ICON_MAP[item.icon] ?? LayoutDashboard;
            const isActive =
              activeHref === item.href ||
              (activeHref?.startsWith(item.href + "/") ?? false);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`nav-link ${isActive ? "active" : ""}`}
                aria-current={isActive ? "page" : undefined}
                title={collapsed ? item.label : undefined}
              >
                <Icon size={14} />
                {!collapsed && <span>{item.label}</span>}
              </Link>
            );
          })}
        </div>
      ))}
    </aside>
  );
}

interface PulseStat {
  label: string;
  value: string;
  tone?: "default" | "positive";
}

function PulseBar({ stats }: { stats: PulseStat[] }) {
  const pathRef = useRef<SVGPathElement>(null);
  const headRef = useRef<SVGCircleElement>(null);

  useEffect(() => {
    if (!pathRef.current || !headRef.current) return;
    const W = 1200;
    const H = 44;
    const mid = H / 2;
    const N = 220;
    const pts: Array<[number, number]> = [];
    for (let i = 0; i < N; i++) {
      const t = i / N;
      let y = mid;
      y -= Math.sin(t * Math.PI * 1.2) * 6;
      y += (Math.random() - 0.5) * 3;
      if (Math.random() < 0.08) y -= 5 + Math.random() * 6;
      if (i === 40 || i === 110 || i === 180) y -= 14;
      pts.push([t * W, y]);
    }
    let d = "";
    pts.forEach((p, i) => {
      d += (i ? "L" : "M") + p[0].toFixed(1) + " " + p[1].toFixed(1);
    });
    pathRef.current.setAttribute("d", d);
    const last = pts[pts.length - 1];
    headRef.current.setAttribute("cx", String(last[0]));
    headRef.current.setAttribute("cy", String(last[1]));
  }, []);

  return (
    <div className="pulse-bar">
      <div className="pulse-row">
        <div className="pulse-label">
          <span className="pulse-dot" /> Platform pulse
        </div>
        <div className="pulse-wrap">
          <svg className="pulse-svg" viewBox="0 0 1200 44" preserveAspectRatio="none">
            <defs>
              <linearGradient id="dv2-pulse" x1="0" y1="0" x2="1" y2="0">
                <stop offset="0" stopColor="#00c7f2" stopOpacity="0" />
                <stop offset="0.3" stopColor="#00c7f2" stopOpacity="0.9" />
                <stop offset="1" stopColor="#5cdfff" />
              </linearGradient>
            </defs>
            <path
              ref={pathRef}
              stroke="url(#dv2-pulse)"
              strokeWidth="1.8"
              fill="none"
              strokeLinecap="round"
            />
            <circle ref={headRef} r="3.5" fill="#5cdfff" filter="drop-shadow(0 0 4px #5cdfff)" />
          </svg>
        </div>
        <div className="pulse-stat">
          {stats.map((s, i) => (
            <span key={i} className={s.tone === "positive" ? "g" : ""}>
              <b>{s.value}</b> {s.label}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}

// ─── Shell wrapper ──────────────────────────────────────────────

interface DashboardShellProps {
  activeHref?: string;
  pulseStats?: PulseStat[];
  breadcrumbs?: Array<{ label: string; href?: string }>;
  children: React.ReactNode;
}

const DEFAULT_STATS: PulseStat[] = [
  { label: "tx/min", value: "12,847" },
  { label: "branches online", value: "24/24" },
  { label: "uptime", value: "99.94%", tone: "positive" },
];

export function DashboardShell({
  activeHref = "/dashboard",
  pulseStats = DEFAULT_STATS,
  breadcrumbs,
  children,
}: DashboardShellProps) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const pathname = usePathname();

  // Auto-close the mobile drawer whenever the user navigates — otherwise
  // the drawer stays over the page they just landed on, which feels stuck.
  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  return (
    <div className={`dashboard-v2${collapsed ? " collapsed" : ""}${mobileOpen ? " mobile-open" : ""}`}>
      {/* Mobile hamburger — visible only below lg breakpoint (see CSS). */}
      <button
        type="button"
        className="mobile-menu-btn"
        onClick={() => setMobileOpen(true)}
        aria-label="Open navigation menu"
        aria-expanded={mobileOpen}
      >
        <Menu size={20} />
      </button>

      {/* Mobile backdrop — closes drawer on tap. Hidden on desktop via CSS. */}
      {mobileOpen && (
        <div
          className="side-backdrop"
          onClick={() => setMobileOpen(false)}
          aria-hidden="true"
        />
      )}

      <div className="app">
        <Sidebar
          activeHref={activeHref}
          mobileOpen={mobileOpen}
          onMobileClose={() => setMobileOpen(false)}
          collapsed={collapsed}
          onToggleCollapse={() => setCollapsed((v) => !v)}
        />
        <div className="main">
          <PulseBar stats={pulseStats} />
          {breadcrumbs && breadcrumbs.length > 0 && (
            <div className="topbar">
              <div className="crumbs">
                {breadcrumbs.map((bc, i) => (
                  <span key={i} style={{ display: "contents" }}>
                    {i > 0 && <span className="sep">/</span>}
                    {bc.href ? (
                      <Link href={bc.href}>{bc.label}</Link>
                    ) : (
                      <b>{bc.label}</b>
                    )}
                  </span>
                ))}
              </div>
            </div>
          )}
          {children}
        </div>
      </div>
    </div>
  );
}
