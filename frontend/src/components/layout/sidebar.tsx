"use client";

import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useSession, signOut } from "next-auth/react";
import {
  Activity,
  BarChartBig,
  Bell,
  CreditCard,
  FileBarChart,
  LayoutDashboard,
  LayoutGrid,
  Menu,
  Package,
  Shield,
  Target,
  Users,
  UserCog,
  Building2,
  RotateCcw,
  FlaskConical,
  GitBranch,
  Palette,
  ScrollText,
  ShieldCheck,
  Sparkles,
  Trophy,
  Upload,
  LogOut,
  User,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { NAV_ITEMS } from "@/lib/constants";
import { HealthIndicator } from "./health-indicator";
import { SavedViewsMenu } from "./saved-views-menu";
import { ThemeToggle } from "@/components/theme-toggle";
import { LanguageToggle } from "./language-toggle";

interface SidebarProps {
  anomalyCount?: number;
  alertCount?: number;
}

const iconMap: Record<string, React.ComponentType<{ className?: string }>> = {
  LayoutDashboard,
  LayoutGrid,
  Target,
  BarChartBig,
  Package,
  Users,
  UserCog,
  Building2,
  RotateCcw,
  FileBarChart,
  FlaskConical,
  GitBranch,
  Bell,
  Sparkles,
  Shield,
  ShieldCheck,
  Palette,
  ScrollText,
  Trophy,
  Upload,
  CreditCard,
};

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
        {/* Avatar */}
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

function NavLinks({
  pathname,
  onNavigate,
  anomalyCount = 0,
  alertCount = 0,
}: {
  pathname: string;
  onNavigate?: () => void;
  anomalyCount?: number;
  alertCount?: number;
}) {
  return (
    <>
      {NAV_ITEMS.map((item) => {
        const Icon = iconMap[item.icon];
        const isActive = pathname === item.href || pathname?.startsWith(item.href + "/");
        const showInsightsBadge = item.label === "Insights" && anomalyCount > 0;
        const showAlertsBadge = item.label === "Alerts" && alertCount > 0;
        return (
          <Link
            key={item.href}
            href={item.href}
            onClick={onNavigate}
            aria-current={isActive ? "page" : undefined}
            className={cn(
              "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
              isActive
                ? "bg-accent/10 text-accent"
                : "text-text-secondary hover:bg-divider hover:text-text-primary"
            )}
          >
            {Icon && <Icon className="h-5 w-5" />}
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
    </>
  );
}

export function Sidebar({ anomalyCount = 0, alertCount = 0 }: SidebarProps) {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);
  const touchStartX = useRef<number | null>(null);

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
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-black/60"
            onClick={() => setMobileOpen(false)}
          />
          {/* Drawer */}
          <aside
            className="absolute left-0 top-0 flex h-screen w-[min(15rem,85vw)] flex-col border-r border-border bg-card shadow-xl animate-slide-in-left"
            onTouchStart={handleTouchStart}
            onTouchEnd={handleTouchEnd}
          >
            {/* Logo + close */}
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

            {/* Navigation */}
            <nav className="flex-1 space-y-1 px-3 py-4">
              <NavLinks pathname={pathname} onNavigate={() => setMobileOpen(false)} anomalyCount={anomalyCount} alertCount={alertCount} />
            </nav>

            {/* Saved Views */}
            <SavedViewsMenu onNavigate={() => setMobileOpen(false)} />

            {/* Footer */}
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
        {/* Logo */}
        <div className="flex h-16 items-center gap-2 px-6">
          <Activity className="h-6 w-6 text-accent" />
          <span className="text-xl font-bold text-accent">DataPulse</span>
        </div>

        {/* Navigation */}
        <nav className="flex-1 space-y-1 px-3 py-4">
          <NavLinks pathname={pathname} anomalyCount={anomalyCount} alertCount={alertCount} />
        </nav>

        {/* Saved Views */}
        <SavedViewsMenu />

        {/* Footer */}
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
