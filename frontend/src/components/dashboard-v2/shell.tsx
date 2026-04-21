"use client";

/**
 * Dashboard v2 shell — sidebar + pulse bar + page chrome.
 *
 * Layered approach:
 *   - Conventional sidebar structure (v1 of the HTML prototypes) for
 *     extensibility — sections + nav links + badges, not editorial.
 *   - Pulse bar chrome from Dashboard.html (animated ECG at the top of
 *     every page, app-level).
 *   - Responsive behavior: below 1024px the sidebar becomes a
 *     slide-in drawer triggered by a hamburger button. Above 1024px it
 *     is a permanent column with an optional collapse toggle
 *     (240px ↔ 68px). ESC + backdrop tap + swipe-left close the drawer.
 *     Route change also auto-closes the drawer (so users don't see the
 *     drawer overlay the page they just navigated to).
 */

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  TrendingUp,
  Package,
  Calendar,
  Users,
  Truck,
  FileText,
  Bell,
  Settings,
  ShoppingCart,
  Activity,
  Target,
  Menu,
  X,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import "./dashboard-v2.css";

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

interface NavItemDef {
  href: string;
  label: string;
  icon: React.ComponentType<{ size?: number | string }>;
  badge?: { text: string; tone?: "accent" | "red" };
}

interface NavSectionDef {
  label: string;
  items: NavItemDef[];
}

const NAV_SECTIONS: NavSectionDef[] = [
  {
    label: "Dashboards",
    items: [
      { href: "/dashboard", label: "Overview", icon: LayoutDashboard },
      { href: "/briefing", label: "Morning briefing", icon: LayoutDashboard },
      {
        href: "/insights",
        label: "Insights",
        icon: LayoutDashboard,
        badge: { text: "12", tone: "accent" as const },
      },
    ],
  },
  {
    label: "Operations",
    items: [
      { href: "/inventory", label: "Inventory", icon: Package },
      { href: "/expiry", label: "Expiry", icon: Calendar, badge: { text: "4", tone: "red" as const } },
      { href: "/dispensing", label: "Dispensing", icon: Activity },
      { href: "/suppliers", label: "Suppliers", icon: Truck },
      { href: "/purchase-orders", label: "Purchase orders", icon: FileText },
    ],
  },
  {
    label: "Analytics",
    items: [
      { href: "/analytics/revenue", label: "Revenue", icon: TrendingUp },
      { href: "/analytics/customers", label: "Customers", icon: Users },
      { href: "/targets", label: "Targets", icon: Target },
    ],
  },
  {
    label: "Account",
    items: [
      { href: "/pos", label: "POS terminal", icon: ShoppingCart },
      { href: "/alerts", label: "Alerts", icon: Bell },
      { href: "/settings", label: "Settings", icon: Settings },
    ],
  },
];

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
      aria-label="Primary"
      onTouchStart={handleTouchStart}
      onTouchEnd={handleTouchEnd}
    >
      <div className="side-header">
        <Link href="/dashboard" className="brand">
          <LogoMark />
          {!collapsed && <span>DataPulse</span>}
        </Link>

        {/* Mobile close button — visible only when drawer is open */}
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

      {NAV_SECTIONS.map((section) => (
        <div key={section.label}>
          {!collapsed && <div className="nav-section">{section.label}</div>}
          {section.items.map((item) => {
            const Icon = item.icon;
            const isActive = activeHref === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`nav-link ${isActive ? "active" : ""}`}
                title={collapsed ? item.label : undefined}
              >
                <Icon size={14} />
                {!collapsed && <span>{item.label}</span>}
                {!collapsed && item.badge && (
                  <span className={`n ${item.badge.tone === "red" ? "red" : ""}`}>
                    {item.badge.text}
                  </span>
                )}
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
