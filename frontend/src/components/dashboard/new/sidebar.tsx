"use client";

import Link from "next/link";
import {
  LayoutDashboard,
  Compass,
  LineChart,
  Package,
  Building2,
  Truck,
  CalendarClock,
  Workflow,
  Database,
  Boxes,
} from "lucide-react";
import type { ComponentType, SVGProps } from "react";

type Icon = ComponentType<SVGProps<SVGSVGElement>>;

interface NavItem {
  label: string;
  href: string;
  icon: Icon;
  active?: boolean;
}

interface NavGroup {
  section: string;
  items: NavItem[];
}

const NAV: NavGroup[] = [
  {
    section: "Overview",
    items: [
      { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard, active: true },
      { label: "Explorer", href: "/explore", icon: Compass },
      { label: "Forecasts", href: "/forecasts", icon: LineChart },
    ],
  },
  {
    section: "Operations",
    items: [
      { label: "Inventory", href: "/inventory", icon: Package },
      { label: "Branches", href: "/sites", icon: Building2 },
      { label: "Suppliers", href: "/suppliers", icon: Truck },
      { label: "Expiry", href: "/expiry", icon: CalendarClock },
    ],
  },
  {
    section: "Data",
    items: [
      { label: "Pipelines", href: "/pipelines", icon: Workflow },
      { label: "Sources", href: "/sources", icon: Database },
      { label: "Models", href: "/models", icon: Boxes },
    ],
  },
];

export function DashboardSidebar({ activeHref = "/dashboard" }: { activeHref?: string }) {
  return (
    <aside
      className="sticky top-0 h-screen overflow-y-auto border-r border-border/50 bg-page/40 p-5"
      aria-label="Primary navigation"
    >
      <div className="flex items-center gap-2.5 pb-4 mb-4 border-b border-border/40">
        <div
          className="w-8 h-8 rounded-[9px] grid place-items-center text-page font-bold
                     bg-gradient-to-br from-accent to-chart-purple shadow-[0_6px_16px_rgba(0,199,242,0.35)]"
          aria-hidden
        >
          DP
        </div>
        <div className="text-[15px] font-bold tracking-tight">DataPulse</div>
      </div>

      {NAV.map((group) => (
        <div key={group.section}>
          <div className="text-[10.5px] tracking-[0.22em] uppercase text-ink-tertiary px-3 pt-3.5 pb-2">
            {group.section}
          </div>
          {group.items.map((item) => {
            const Icon = item.icon;
            const isActive = activeHref === item.href || item.active;
            return (
              <Link
                key={item.label}
                href={item.href}
                aria-current={isActive ? "page" : undefined}
                className={[
                  "flex items-center gap-2.5 px-3 py-2 rounded-[10px] text-[13.5px] my-px transition",
                  "focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/60",
                  isActive
                    ? "bg-gradient-to-r from-accent/[0.12] to-accent/0 text-ink-primary shadow-[inset_2px_0_0_var(--accent-color)]"
                    : "text-ink-secondary hover:bg-white/[0.04] hover:text-ink-primary",
                ].join(" ")}
              >
                <Icon className="w-4 h-4" aria-hidden />
                {item.label}
              </Link>
            );
          })}
        </div>
      ))}
    </aside>
  );
}
