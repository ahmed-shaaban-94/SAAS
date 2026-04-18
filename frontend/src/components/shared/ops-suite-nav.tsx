"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Package, Activity, Calendar, ClipboardList, Truck } from "lucide-react";
import { cn } from "@/lib/utils";

const OPS_TABS = [
  { href: "/inventory",       label: "Inventory",       icon: Package      },
  { href: "/dispensing",      label: "Dispensing",      icon: Activity     },
  { href: "/expiry",          label: "Expiry",          icon: Calendar     },
  { href: "/purchase-orders", label: "Purchase Orders", icon: ClipboardList },
  { href: "/suppliers",       label: "Suppliers",       icon: Truck        },
] as const;

export function OpsSuiteNav() {
  const pathname = usePathname();

  return (
    <nav
      aria-label="Operations suite navigation"
      className="mb-4 flex flex-wrap gap-1.5"
    >
      {OPS_TABS.map(({ href, label, icon: Icon }) => {
        const active = pathname === href || pathname?.startsWith(href + "/");
        return (
          <Link
            key={href}
            href={href}
            aria-current={active ? "page" : undefined}
            className={cn(
              "inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium transition-colors",
              active
                ? "bg-accent/15 text-accent"
                : "text-text-secondary hover:bg-background/60 hover:text-text-primary",
            )}
          >
            <Icon className="h-3 w-3" aria-hidden="true" />
            {label}
          </Link>
        );
      })}
    </nav>
  );
}
