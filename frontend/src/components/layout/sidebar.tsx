"use client";

import { useState, useCallback } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  LayoutDashboard,
  Package,
  Users,
  UserCog,
  Building2,
  RotateCcw,
  GitBranch,
  Sparkles,
  Menu,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { NAV_ITEMS } from "@/lib/constants";
import { HealthIndicator } from "./health-indicator";

const iconMap: Record<string, React.ComponentType<{ className?: string }>> = {
  LayoutDashboard,
  Package,
  Users,
  UserCog,
  Building2,
  RotateCcw,
  GitBranch,
  Sparkles,
};

interface SidebarProps {
  anomalyCount?: number;
}

function AnomalyBadge({ count }: { count: number }) {
  if (count <= 0) return null;
  return (
    <span className="ml-auto flex h-5 min-w-5 items-center justify-center rounded-full bg-red-500 px-1.5 text-[10px] font-bold leading-none text-white">
      {count > 99 ? "99+" : count}
    </span>
  );
}

function NavLink({
  item,
  isActive,
  anomalyCount,
  onClick,
}: {
  item: (typeof NAV_ITEMS)[number];
  isActive: boolean;
  anomalyCount?: number;
  onClick?: () => void;
}) {
  const Icon = iconMap[item.icon];
  const showBadge = item.label === "Insights" && anomalyCount && anomalyCount > 0;

  return (
    <Link
      href={item.href}
      onClick={onClick}
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
      {showBadge && <AnomalyBadge count={anomalyCount} />}
    </Link>
  );
}

export function Sidebar({ anomalyCount }: SidebarProps) {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  const closeMobile = useCallback(() => setMobileOpen(false), []);

  return (
    <>
      {/* Desktop sidebar */}
      <aside className="fixed left-0 top-0 z-40 hidden h-screen w-60 flex-col border-r border-border bg-card lg:flex">
        {/* Logo */}
        <div className="flex h-16 items-center gap-2 px-6">
          <Activity className="h-6 w-6 text-accent" />
          <span className="text-xl font-bold text-accent">DataPulse</span>
        </div>

        {/* Navigation */}
        <nav aria-label="Main navigation" className="flex-1 space-y-1 px-3 py-4">
          {NAV_ITEMS.map((item) => {
            const isActive = pathname === item.href || pathname?.startsWith(item.href + "/");
            return (
              <NavLink
                key={item.href}
                item={item}
                isActive={isActive}
                anomalyCount={anomalyCount}
              />
            );
          })}
        </nav>

        {/* Footer */}
        <div className="border-t border-border px-6 py-4 space-y-2">
          <HealthIndicator />
          <p className="text-xs text-text-secondary">DataPulse v0.1.0</p>
        </div>
      </aside>

      {/* Mobile top bar */}
      <div className="fixed left-0 right-0 top-0 z-40 flex h-14 items-center justify-between border-b border-border bg-card px-4 lg:hidden">
        <div className="flex items-center gap-2">
          <Activity className="h-5 w-5 text-accent" />
          <span className="text-lg font-bold text-accent">DataPulse</span>
        </div>
        <button
          type="button"
          onClick={() => setMobileOpen(true)}
          className="relative inline-flex items-center justify-center rounded-md p-2 text-text-secondary hover:bg-divider hover:text-text-primary focus:outline-none focus:ring-2 focus:ring-accent"
          aria-label="Open navigation menu"
        >
          <Menu className="h-6 w-6" />
          {anomalyCount && anomalyCount > 0 ? (
            <span className="absolute right-1 top-1 h-2.5 w-2.5 rounded-full bg-red-500" />
          ) : null}
        </button>
      </div>

      {/* Mobile drawer backdrop */}
      <div
        className={cn(
          "fixed inset-0 z-50 bg-black/60 transition-opacity duration-300 lg:hidden",
          mobileOpen ? "opacity-100" : "pointer-events-none opacity-0"
        )}
        onClick={closeMobile}
        aria-hidden="true"
      />

      {/* Mobile drawer */}
      <aside
        className={cn(
          "fixed left-0 top-0 z-50 flex h-screen w-72 flex-col border-r border-border bg-card transition-transform duration-300 ease-in-out lg:hidden",
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        {/* Drawer header */}
        <div className="flex h-14 items-center justify-between px-4">
          <div className="flex items-center gap-2">
            <Activity className="h-5 w-5 text-accent" />
            <span className="text-lg font-bold text-accent">DataPulse</span>
          </div>
          <button
            type="button"
            onClick={closeMobile}
            className="inline-flex items-center justify-center rounded-md p-2 text-text-secondary hover:bg-divider hover:text-text-primary focus:outline-none focus:ring-2 focus:ring-accent"
            aria-label="Close navigation menu"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Drawer navigation */}
        <nav aria-label="Main navigation" className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
          {NAV_ITEMS.map((item) => {
            const isActive = pathname === item.href || pathname?.startsWith(item.href + "/");
            return (
              <NavLink
                key={item.href}
                item={item}
                isActive={isActive}
                anomalyCount={anomalyCount}
                onClick={closeMobile}
              />
            );
          })}
        </nav>

        {/* Drawer footer */}
        <div className="border-t border-border px-6 py-4 space-y-2">
          <HealthIndicator />
          <p className="text-xs text-text-secondary">DataPulse v0.1.0</p>
        </div>
      </aside>
    </>
  );
}
