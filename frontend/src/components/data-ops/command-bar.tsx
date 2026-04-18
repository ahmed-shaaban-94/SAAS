"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Upload, ShieldX } from "lucide-react";
import { cn } from "@/lib/utils";

const ACTIONS = [
  { label: "Upload Files", href: "/upload", icon: Upload },
  { label: "Pipeline Health", href: "/quality", icon: ShieldX },
] as const;

export function DataOpsCommandBar() {
  const pathname = usePathname();

  return (
    <div className="viz-panel-soft mb-6 flex flex-wrap items-center gap-2 rounded-[1.5rem] p-2">
      {ACTIONS.map(({ label, href, icon: Icon }) => {
        const isActive = pathname === href;
        return (
          <Link
            key={href}
            href={href}
            className={cn(
              "flex items-center gap-1.5 rounded-[1rem] px-3 py-2 text-xs font-semibold uppercase tracking-[0.14em] transition-all",
              isActive
                ? "bg-accent text-page shadow-[0_12px_24px_rgba(0,199,242,0.2)]"
                : "text-text-secondary hover:bg-background/60 hover:text-text-primary",
            )}
          >
            <Icon className="h-3.5 w-3.5" />
            {label}
          </Link>
        );
      })}
    </div>
  );
}
