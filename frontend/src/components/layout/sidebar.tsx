"use client";

import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useSession, signOut } from "@/lib/auth-bridge";
import {
  Activity,
  BarChart3,
  BarChartBig,
  Bell,
  Brain,
  Briefcase,
  Building2,
  Calendar,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ClipboardList,
  CreditCard,
  Database,
  FileBarChart,
  FlaskConical,
  GitBranch,
  LayoutDashboard,
  LayoutGrid,
  LogOut,
  Menu,
  Package,
  Palette,
  RotateCcw,
  ScrollText,
  Settings,
  Shield,
  ShieldCheck,
  Sparkles,
  Target,
  Trophy,
  Upload,
  User,
  UserCog,
  Users,
  Users2,
  Truck,
  Warehouse,
  Workflow,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { NAV_GROUPS, type NavGroup } from "@/lib/constants";
import { HealthIndicator } from "./health-indicator";
import { SavedViewsMenu } from "./saved-views-menu";
import { ThemeToggle } from "@/components/theme-toggle";
import { LocaleSwitcher } from "@/components/locale-switcher";
import { useLocale } from "next-intl";
import { type Locale } from "@/i18n/config";

interface SidebarProps {
  anomalyCount?: number;
  alertCount?: number;
}

const iconMap: Record<string, React.ComponentType<{ className?: string }>> = {
  Briefcase,
  LayoutDashboard,
  LayoutGrid,
  BarChart3,
  BarChartBig,
  Target,
  Package,
  Users,
  UserCog,
  Building2,
  RotateCcw,
  FileBarChart,
  GitBranch,
  Bell,
  Sparkles,
  CreditCard,
  Database,
  Brain,
  FlaskConical,
  Workflow,
  Upload,
  ShieldCheck,
  Users2,
  Shield,
  Trophy,
  ScrollText,
  Settings,
  Palette,
  Warehouse,
  Calendar,
  ClipboardList,
  Truck,
};

function UserInfo({ collapsed }: { collapsed?: boolean }) {
  const { data: session } = useSession();

  if (!session?.user) return null;

  const displayName = session.user.name || session.user.email || "User";
  const initials = displayName
    .split(" ")
    .map((w) => w[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);

  if (collapsed) {
    return (
      <div className="flex flex-col items-center gap-2">
        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-accent/15 text-xs font-bold text-accent shadow-[0_10px_24px_rgba(0,199,242,0.2)]">
          {initials || <User className="h-4 w-4" />}
        </div>
        <button
          onClick={() => signOut({ callbackUrl: "/login" })}
          className="viz-panel-soft flex h-8 w-8 items-center justify-center rounded-xl text-text-secondary transition-colors hover:text-text-primary"
          title="Sign Out"
        >
          <LogOut className="h-4 w-4" />
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-3">
        <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-accent/15 text-xs font-bold text-accent shadow-[0_10px_24px_rgba(0,199,242,0.2)]">
          {initials || <User className="h-4 w-4" />}
        </div>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium text-text-primary">
            {displayName}
          </p>
          {session.user.email && session.user.name && (
            <p className="truncate text-xs text-text-secondary">
              {session.user.email}
            </p>
          )}
        </div>
      </div>
      <button
        onClick={() => signOut({ callbackUrl: "/login" })}
        className="viz-panel-soft flex w-full items-center gap-2 rounded-xl px-3 py-2 text-sm text-text-secondary transition-colors hover:text-text-primary"
      >
        <LogOut className="h-4 w-4" />
        Sign Out
      </button>
    </div>
  );
}

function NavGroupSection({
  group,
  pathname,
  collapsed,
  onNavigate,
  anomalyCount = 0,
  alertCount = 0,
  defaultOpen,
}: {
  group: NavGroup;
  pathname: string;
  collapsed?: boolean;
  onNavigate?: () => void;
  anomalyCount?: number;
  alertCount?: number;
  defaultOpen?: boolean;
}) {
  const hasActiveItem = group.items.some(
    (item) => pathname === item.href || pathname?.startsWith(item.href + "/"),
  );
  const [open, setOpen] = useState(defaultOpen || hasActiveItem);
  const GroupIcon = iconMap[group.icon];

  // Collapsed mode: show only group icon as a button with tooltip
  if (collapsed) {
    return (
      <div className="relative group/grp">
        <div
          className={cn(
            "flex h-9 w-9 items-center justify-center rounded-lg mx-auto transition-colors cursor-pointer",
            hasActiveItem
              ? "bg-accent/12 text-accent shadow-[0_12px_24px_rgba(0,199,242,0.18)]"
              : "text-text-secondary hover:bg-white/5 hover:text-text-primary",
          )}
          title={group.label}
        >
          {GroupIcon && <GroupIcon className="h-5 w-5" />}
        </div>

        {/* Flyout menu on hover */}
        <div className="pointer-events-none absolute left-full top-0 z-50 ml-2 opacity-0 transition-all duration-150 group-hover/grp:pointer-events-auto group-hover/grp:opacity-100">
          <div className="viz-panel min-w-[180px] rounded-2xl py-1.5 shadow-xl">
            <div className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-text-secondary">
              {group.label}
            </div>
            {group.items.map((item) => {
              const Icon = iconMap[item.icon];
              const isActive =
                pathname === item.href ||
                pathname?.startsWith(item.href + "/");
              const showInsightsBadge =
                item.label === "Insights" && anomalyCount > 0;
              const showAlertsBadge =
                item.label === "Alerts" && alertCount > 0;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={onNavigate}
                  className={cn(
                    "flex items-center gap-2.5 px-3 py-2 text-sm transition-colors",
                    isActive
                      ? "bg-accent/12 text-accent"
                      : "text-text-secondary hover:bg-white/5 hover:text-text-primary",
                  )}
                >
                  {Icon && <Icon className="h-4 w-4" />}
                  <span>{item.label}</span>
                  {showInsightsBadge && (
                    <span className="ml-auto rounded-full bg-chart-amber px-1.5 py-0.5 text-xs font-bold text-black">
                      {anomalyCount}
                    </span>
                  )}
                  {showAlertsBadge && (
                    <span className="ml-auto flex h-5 w-5 items-center justify-center rounded-full bg-red-500 text-[10px] font-bold text-white animate-pulse">
                      {alertCount}
                    </span>
                  )}
                </Link>
              );
            })}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div>
      {/* Group header */}
      <button
        onClick={() => setOpen((prev) => !prev)}
        className={cn(
          "flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-xs font-semibold uppercase tracking-wider transition-colors",
          hasActiveItem
            ? "text-accent"
            : "text-text-secondary hover:bg-white/5 hover:text-text-primary",
        )}
        aria-expanded={open}
      >
        {GroupIcon && <GroupIcon className="h-4 w-4" />}
        <span>{group.label}</span>
        <ChevronDown
          className={cn(
            "ml-auto h-3.5 w-3.5 transition-transform duration-200",
            open && "rotate-180",
          )}
        />
      </button>

      {/* Group items */}
      <div
        className={cn(
          "overflow-hidden transition-all duration-200",
          open ? "max-h-96 opacity-100" : "max-h-0 opacity-0",
        )}
      >
        <div className="ml-2 space-y-0.5 border-l border-border/50 pl-2">
          {group.items.map((item) => {
            const Icon = iconMap[item.icon];
            const isActive =
              pathname === item.href ||
              pathname?.startsWith(item.href + "/");
            const showInsightsBadge =
              item.label === "Insights" && anomalyCount > 0;
            const showAlertsBadge =
              item.label === "Alerts" && alertCount > 0;
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={onNavigate}
                className={cn(
                  "flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-accent/12 text-accent"
                    : "text-text-secondary hover:bg-white/5 hover:text-text-primary",
                )}
              >
                {Icon && <Icon className="h-4 w-4" />}
                <span>{item.label}</span>
                {showInsightsBadge && (
                  <span className="ml-auto rounded-full bg-chart-amber px-1.5 py-0.5 text-xs font-bold text-black">
                    {anomalyCount}
                  </span>
                )}
                {showAlertsBadge && (
                  <span className="ml-auto flex h-5 w-5 items-center justify-center rounded-full bg-red-500 text-[10px] font-bold text-white animate-pulse">
                    {alertCount}
                  </span>
                )}
              </Link>
            );
          })}
        </div>
      </div>
    </div>
  );
}

export function Sidebar({ anomalyCount = 0, alertCount = 0 }: SidebarProps) {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const touchStartX = useRef<number | null>(null);
  const locale = useLocale() as Locale;

  const handleTouchStart = (e: React.TouchEvent) => {
    touchStartX.current = e.touches[0].clientX;
  };

  const handleTouchEnd = (e: React.TouchEvent) => {
    if (touchStartX.current === null) return;
    const deltaX = e.changedTouches[0].clientX - touchStartX.current;
    if (deltaX < -60) setMobileOpen(false);
    touchStartX.current = null;
  };

  useEffect(() => {
    if (!mobileOpen) return;
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === "Escape") setMobileOpen(false);
    };
    document.addEventListener("keydown", handleEsc);
    return () => document.removeEventListener("keydown", handleEsc);
  }, [mobileOpen]);

  const sidebarWidth = collapsed ? "w-16" : "w-60";

  return (
    <>
      {/* CSS variable for main content offset */}
      <style jsx global>{`
        :root {
          --sidebar-width: ${collapsed ? "4rem" : "15rem"};
        }
      `}</style>

      {/* Mobile hamburger button */}
      <button
        onClick={() => setMobileOpen(true)}
        className="viz-panel fixed left-4 top-4 z-50 rounded-xl p-2 text-text-primary shadow-lg lg:hidden"
        aria-label="Open navigation"
        aria-expanded={mobileOpen}
      >
        <Menu className="h-5 w-5" />
      </button>

      {/* Mobile overlay + drawer */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-50 lg:hidden"
          role="dialog"
          aria-modal="true"
          aria-label="Navigation menu"
        >
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-black/60"
            onClick={() => setMobileOpen(false)}
          />
          {/* Drawer — always expanded on mobile */}
          <aside
            className="absolute left-0 top-0 flex h-screen w-60 flex-col border-r border-border bg-card shadow-xl animate-slide-in-left"
            onTouchStart={handleTouchStart}
            onTouchEnd={handleTouchEnd}
          >
            {/* Logo + close */}
            <div className="flex h-16 items-center justify-between px-4">
              <div className="flex items-center gap-2">
                <Activity className="h-6 w-6 text-accent" />
                <span className="text-xl font-bold tracking-tight text-text-primary">DataPulse</span>
              </div>
              <button
                onClick={() => setMobileOpen(false)}
                className="viz-panel-soft rounded-xl p-1.5 text-text-secondary hover:text-text-primary"
                aria-label="Close navigation"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Navigation groups */}
            <nav data-testid="sidebar-nav" className="flex-1 overflow-y-auto px-2 py-2 space-y-1">
              {NAV_GROUPS.map((group) => (
                <NavGroupSection
                  key={group.id}
                  group={group}
                  pathname={pathname}
                  onNavigate={() => setMobileOpen(false)}
                  anomalyCount={anomalyCount}
                  alertCount={alertCount}
                  defaultOpen
                />
              ))}
            </nav>

            {/* Saved Views */}
            <SavedViewsMenu onNavigate={() => setMobileOpen(false)} />

            {/* Footer */}
            <div className="border-t border-border px-4 py-3 space-y-3">
              <UserInfo />
              <div className="flex items-center justify-between gap-2">
                <ThemeToggle />
                <LocaleSwitcher currentLocale={locale} />
              </div>
              <HealthIndicator />
              <p className="text-xs text-text-secondary">DataPulse v0.1.0</p>
            </div>
          </aside>
        </div>
      )}

      {/* Desktop sidebar */}
      <aside
        className={cn(
          "fixed left-0 top-0 z-40 hidden h-screen flex-col border-r border-border bg-card/95 backdrop-blur-xl transition-all duration-200 lg:flex",
          sidebarWidth,
        )}
      >
        {/* Logo + collapse toggle */}
        <div
          className={cn(
            "flex h-16 items-center border-b border-border/70",
            collapsed ? "justify-center px-2" : "justify-between px-4",
          )}
        >
          <div className="flex items-center gap-2">
            <Activity className="h-6 w-6 text-accent flex-shrink-0" />
            {!collapsed && (
              <span className="text-lg font-bold tracking-tight text-text-primary">DataPulse</span>
            )}
          </div>
          <button
            onClick={() => setCollapsed((prev) => !prev)}
            className={cn(
              "viz-panel-soft rounded-xl p-1.5 text-text-secondary transition-colors hover:text-text-primary",
              collapsed && "mx-auto mt-2",
            )}
            title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {collapsed ? (
              <ChevronRight className="h-4 w-4" />
            ) : (
              <ChevronLeft className="h-4 w-4" />
            )}
          </button>
        </div>

        {/* Navigation groups */}
        <nav
          className={cn(
            "flex-1 overflow-y-auto py-3",
            collapsed ? "px-1 space-y-2" : "px-2 space-y-1",
          )}
        >
          {NAV_GROUPS.map((group) => (
            <NavGroupSection
              key={group.id}
              group={group}
              pathname={pathname}
              collapsed={collapsed}
              anomalyCount={anomalyCount}
              alertCount={alertCount}
            />
          ))}
        </nav>

        {/* Saved Views — hidden when collapsed */}
        {!collapsed && <SavedViewsMenu />}

        {/* Footer */}
        <div
          className={cn(
            "border-t border-border py-3 space-y-2",
            collapsed ? "px-2 flex flex-col items-center" : "px-4",
          )}
        >
          <UserInfo collapsed={collapsed} />
          {!collapsed && (
            <>
              <div className="flex items-center justify-between gap-2">
                <ThemeToggle />
                <LocaleSwitcher currentLocale={locale} />
              </div>
              <HealthIndicator />
              <p className="text-xs text-text-secondary">DataPulse v0.1.0</p>
            </>
          )}
          {collapsed && (
            <div className="flex flex-col items-center gap-2">
              <ThemeToggle />
              <LocaleSwitcher currentLocale={locale} />
              <HealthIndicator />
            </div>
          )}
        </div>
      </aside>
    </>
  );
}
