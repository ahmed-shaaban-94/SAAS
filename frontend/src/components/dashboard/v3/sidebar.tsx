"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  Compass,
  LineChart,
  Boxes,
  Building2,
  Truck,
  CalendarClock,
  Workflow,
  Database,
  Layers,
} from "lucide-react";
import type { ComponentType, SVGProps } from "react";

type IconType = ComponentType<SVGProps<SVGSVGElement>>;

interface NavItem {
  label: string;
  href: string;
  icon: IconType;
}

interface NavSection {
  section: string;
  items: NavItem[];
}

const nav: NavSection[] = [
  {
    section: "Overview",
    items: [
      { label: "Dashboard", href: "/dashboard/v3", icon: LayoutDashboard },
      { label: "Explorer", href: "/dashboard/v3/explorer", icon: Compass },
      { label: "Forecasts", href: "/dashboard/v3/forecasts", icon: LineChart },
    ],
  },
  {
    section: "Operations",
    items: [
      { label: "Inventory", href: "/dashboard/v3/inventory", icon: Boxes },
      { label: "Branches", href: "/dashboard/v3/branches", icon: Building2 },
      { label: "Suppliers", href: "/dashboard/v3/suppliers", icon: Truck },
      { label: "Expiry", href: "/dashboard/v3/expiry", icon: CalendarClock },
    ],
  },
  {
    section: "Data",
    items: [
      { label: "Pipelines", href: "/dashboard/v3/pipelines", icon: Workflow },
      { label: "Sources", href: "/dashboard/v3/sources", icon: Database },
      { label: "Models", href: "/dashboard/v3/models", icon: Layers },
    ],
  },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="sticky top-0 h-screen overflow-y-auto border-r border-border/50 bg-page/40 p-5">
      <div className="flex items-center gap-2.5 pb-4 mb-4 border-b border-border/40">
        <div
          className="grid h-8 w-8 place-items-center rounded-[9px] bg-gradient-to-br from-accent to-chart-purple font-bold text-page"
          style={{ boxShadow: "0 6px 16px rgba(0,199,242,0.35)" }}
        >
          DP
        </div>
        <div className="text-[15px] font-bold tracking-tight">DataPulse</div>
      </div>

      {nav.map((group) => (
        <div key={group.section}>
          <div className="px-3 pt-3.5 pb-2 text-[10.5px] uppercase tracking-[0.22em] text-text-tertiary">
            {group.section}
          </div>
          {group.items.map((item) => {
            const active = pathname === item.href;
            const Icon = item.icon;
            return (
              <Link
                key={item.label}
                href={item.href}
                className={cn(
                  "my-px flex items-center gap-2.5 rounded-[10px] px-3 py-2 text-[13.5px] transition",
                  active
                    ? "bg-gradient-to-r from-accent/[0.12] to-accent/0 text-text-primary"
                    : "text-text-secondary hover:bg-white/[0.04] hover:text-text-primary",
                )}
                style={
                  active
                    ? { boxShadow: "inset 2px 0 0 #00c7f2" }
                    : undefined
                }
              >
                <Icon className="h-4 w-4" aria-hidden />
                {item.label}
              </Link>
            );
          })}
        </div>
      ))}
    </aside>
  );
}
