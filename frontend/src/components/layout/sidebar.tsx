"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useSession, signOut } from "next-auth/react";
import {
  Activity,
  BarChart3,
  BarChartBig,
  Bell,
  Brain,
  Building2,
  ChevronDown,
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
  Workflow,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { NAV_GROUPS, hasMinRole, type NavGroup } from "@/lib/constants";
import { useMyAccess } from "@/hooks/use-members";
import { HealthIndicator } from "./health-indicator";
import { SavedViewsMenu } from "./saved-views-menu";
import { ThemeToggle } from "@/components/theme-toggle";
import { LanguageToggle } from "./language-toggle";
import type { RoleKey } from "@/types/members";

interface SidebarProps {
  anomalyCount?: number;
  alertCount?: number;
}

const iconMap: Record<string, React.ComponentType<{ className?: string }>> = {
  Activity,
  BarChart3,
  BarChartBig,
  Bell,
  Brain,
  Building2,
  CreditCard,
  Database,
  FileBarChart,
  FlaskConical,
  GitBranch,
  LayoutDashboard,
  LayoutGrid,
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
  UserCog,
  Users,
  Users2,
  Workflow,
};

// ── Helpers ──────────────────────────────────────────────

function findActiveGroupId(pathname: string): string | null {
  for (const group of NAV_GROUPS) {
    for (const item of group.items) {
      if (pathname === item.href || pathname.startsWith(item.href + "/")) {
        return group.id;
      }
    }
  }
  return null;
}

const SIDEBAR_STATE_KEY = "datapulse-sidebar-collapsed";

function useSidebarState(activeGroupId: string | null) {
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>(() => {
    if (typeof window === "undefined") return {};
    try {
      const stored = localStorage.getItem(SIDEBAR_STATE_KEY);
      return stored ? JSON.parse(stored) : {};
    } catch {
      return {};
    }
  });

  useEffect(() => {
    if (activeGroupId && collapsed[activeGroupId]) {
      setCollapsed((prev) => {
        const next = { ...prev, [activeGroupId]: false };
        localStorage.setItem(SIDEBAR_STATE_KEY, JSON.stringify(next));
        return next;
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeGroupId]);

  const toggle = useCallback((groupId: string) => {
    setCollapsed((prev) => {
      const next = { ...prev, [groupId]: !prev[groupId] };
      localStorage.setItem(SIDEBAR_STATE_KEY, JSON.stringify(next));
      return next;
    });
  }, []);

  const isCollapsed = useCallback(
    (groupId: string) => !!collapsed[groupId],
    [collapsed],
  );

  return { isCollapsed, toggle };
}

// ── User Info ────────────────────────────────────────────

function UserInfo() {
  const { data: session } = useSession();

  if (!session?.user) return null;

  const displayName = session.user.name || session.user.email || "User";
  const initials = displayName
    .split(" ")
    .map((w) => w[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-3">
        <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-accent/20 text-xs font-bold text-accent">
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
        className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-text-secondary transition-colors hover:bg-divider hover:text-text-primary"
      >
        <LogOut className="h-4 w-4" />
        Sign Out
      </button>
    </div>
  );
}

// ── Nav Group List ───────────────────────────────────────

function NavGroupList({
  pathname,
  roleKey,
  onNavigate,
  anomalyCount = 0,
  alertCount = 0,
  isCollapsed,
  toggleGroup,
}: {
  pathname: string;
  roleKey: RoleKey;
  onNavigate?: () => void;
  anomalyCount?: number;
  alertCount?: number;
  isCollapsed: (groupId: string) => boolean;
  toggleGroup: (groupId: string) => void;
}) {
  return (
    <>
      {NAV_GROUPS.map((group) => {
        if (!hasMinRole(roleKey, group.minRole)) return null;

        const visibleItems = group.items.filter((item) =>
          hasMinRole(roleKey, item.minRole),
        );
        if (visibleItems.length === 0) return null;

        const GroupIcon = iconMap[group.icon];
        const groupCollapsed = isCollapsed(group.id);
        const hasActiveItem = visibleItems.some(
          (item) =>
            pathname === item.href || pathname.startsWith(item.href + "/"),
        );

        return (
          <div key={group.id} className="mb-1">
            {/* Group header */}
            <button
              onClick={() => toggleGroup(group.id)}
              className={cn(
                "flex w-full items-center gap-2 rounded-lg px-3 py-1.5 text-[11px] font-semibold uppercase tracking-wider transition-colors",
                hasActiveItem
                  ? "text-accent"
                  : "text-text-secondary hover:text-text-primary",
              )}
              aria-expanded={!groupCollapsed}
            >
              {GroupIcon && <GroupIcon className="h-3.5 w-3.5" />}
              <span>{group.label}</span>
              <ChevronDown
                className={cn(
                  "ml-auto h-3 w-3 transition-transform duration-200",
                  !groupCollapsed && "rotate-180",
                )}
              />
            </button>

            {/* Collapsible items */}
            <div
              className={cn(
                "grid transition-[grid-template-rows] duration-200 ease-in-out",
                groupCollapsed ? "grid-rows-[0fr]" : "grid-rows-[1fr]",
              )}
            >
              <div className="overflow-hidden">
                <div className="space-y-0.5 py-0.5">
                  {visibleItems.map((item) => {
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
                        aria-current={isActive ? "page" : undefined}
                        className={cn(
                          "flex items-center gap-3 rounded-lg py-2 pl-9 pr-3 text-sm font-medium transition-colors",
                          isActive
                            ? "bg-accent/10 text-accent"
                            : "text-text-secondary hover:bg-divider hover:text-text-primary",
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
          </div>
        );
      })}
    </>
  );
}

// ── Sidebar ──────────────────────────────────────────────

export function Sidebar({ anomalyCount = 0, alertCount = 0 }: SidebarProps) {
  const pathname = usePathname();
  const { access } = useMyAccess();
  const [mobileOpen, setMobileOpen] = useState(false);
  const touchStartX = useRef<number | null>(null);

  const activeGroupId = findActiveGroupId(pathname);
  const { isCollapsed, toggle } = useSidebarState(activeGroupId);

  // Default to viewer while loading — safe (shows minimal nav)
  const roleKey: RoleKey = access?.role_key ?? "viewer";

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

  const navProps = {
    pathname,
    roleKey,
    anomalyCount,
    alertCount,
    isCollapsed,
    toggleGroup: toggle,
  };

  return (
    <>
      {/* Mobile hamburger button */}
      <button
        onClick={() => setMobileOpen(true)}
        className="fixed left-3 top-3 z-50 rounded-lg bg-card p-2 text-text-primary shadow-lg border border-border sm:left-4 sm:top-4 lg:hidden"
        aria-label="Open navigation"
        aria-expanded={mobileOpen}
      >
        <Menu className="h-5 w-5" />
      </button>

      {/* Mobile overlay + drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden" role="dialog" aria-modal="true" aria-label="Navigation menu">
          <div
            className="absolute inset-0 bg-black/60"
            onClick={() => setMobileOpen(false)}
          />
          <aside
            className="absolute left-0 top-0 flex h-screen w-[min(15rem,85vw)] flex-col border-r border-border bg-card shadow-xl animate-slide-in-left"
            onTouchStart={handleTouchStart}
            onTouchEnd={handleTouchEnd}
          >
            <div className="flex h-16 items-center justify-between px-6">
              <div className="flex items-center gap-2">
                <Activity className="h-6 w-6 text-accent" />
                <span className="text-xl font-bold text-accent">DataPulse</span>
              </div>
              <button
                onClick={() => setMobileOpen(false)}
                className="rounded-md p-1 text-text-secondary hover:text-text-primary"
                aria-label="Close navigation"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <nav className="flex-1 overflow-y-auto px-3 py-4">
              <NavGroupList
                {...navProps}
                onNavigate={() => setMobileOpen(false)}
              />
            </nav>

            <SavedViewsMenu onNavigate={() => setMobileOpen(false)} />

            <div className="border-t border-border px-4 py-4 space-y-3">
              <UserInfo />
              <ThemeToggle />
              <LanguageToggle />
              <HealthIndicator />
              <p className="text-xs text-text-secondary">DataPulse v0.1.0</p>
            </div>
          </aside>
        </div>
      )}

      {/* Desktop sidebar */}
      <aside className="fixed left-0 top-0 z-40 hidden h-screen w-60 flex-col border-r border-border bg-card lg:flex">
        <div className="flex h-16 items-center gap-2 px-6">
          <Activity className="h-6 w-6 text-accent" />
          <span className="text-xl font-bold text-accent">DataPulse</span>
        </div>

        <nav className="flex-1 overflow-y-auto px-3 py-4">
          <NavGroupList {...navProps} />
        </nav>

        <SavedViewsMenu />

        <div className="border-t border-border px-4 py-4 space-y-3">
          <UserInfo />
          <ThemeToggle />
          <LanguageToggle />
          <HealthIndicator />
          <p className="text-xs text-text-secondary">DataPulse v0.1.0</p>
        </div>
      </aside>
    </>
  );
}
