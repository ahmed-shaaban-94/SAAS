"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  LayoutDashboard,
  Menu,
  Package,
  Users,
  UserCog,
  Building2,
  RotateCcw,
  GitBranch,
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
};

function NavLinks({
  pathname,
  onNavigate,
}: {
  pathname: string;
  onNavigate?: () => void;
}) {
  return (
    <>
      {NAV_ITEMS.map((item) => {
        const Icon = iconMap[item.icon];
        const isActive = pathname === item.href || pathname?.startsWith(item.href + "/");
        return (
          <Link
            key={item.href}
            href={item.href}
            onClick={onNavigate}
            className={cn(
              "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
              isActive
                ? "bg-accent/10 text-accent"
                : "text-text-secondary hover:bg-divider hover:text-text-primary"
            )}
          >
            {Icon && <Icon className="h-5 w-5" />}
            <span>{item.label}</span>
          </Link>
        );
      })}
    </>
  );
}

export function Sidebar() {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <>
      {/* Mobile hamburger button */}
      <button
        onClick={() => setMobileOpen(true)}
        className="fixed left-4 top-4 z-50 rounded-lg bg-card p-2 text-text-primary shadow-lg border border-border lg:hidden"
        aria-label="Open navigation"
      >
        <Menu className="h-5 w-5" />
      </button>

      {/* Mobile overlay + drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-black/60"
            onClick={() => setMobileOpen(false)}
          />
          {/* Drawer */}
          <aside className="absolute left-0 top-0 flex h-screen w-60 flex-col border-r border-border bg-card shadow-xl animate-slide-in-left">
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
              <NavLinks pathname={pathname} onNavigate={() => setMobileOpen(false)} />
            </nav>

            {/* Footer */}
            <div className="border-t border-border px-6 py-4 space-y-2">
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
          <NavLinks pathname={pathname} />
        </nav>

        {/* Footer */}
        <div className="border-t border-border px-6 py-4 space-y-2">
          <HealthIndicator />
          <p className="text-xs text-text-secondary">DataPulse v0.1.0</p>
        </div>
      </aside>
    </>
  );
}
