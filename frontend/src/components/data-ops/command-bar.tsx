"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Upload, ShieldX, GitBranch } from "lucide-react";
import { cn } from "@/lib/utils";

const ACTIONS = [
  { label: "Upload Files", href: "/upload", icon: Upload },
  { label: "Data Quality", href: "/quality", icon: ShieldX },
  { label: "Data Lineage", href: "/lineage", icon: GitBranch },
] as const;

export function DataOpsCommandBar() {
  const pathname = usePathname();

  return (
    <div className="flex flex-wrap items-center gap-2 rounded-xl border border-border bg-card p-2 mb-6">
      {ACTIONS.map(({ label, href, icon: Icon }) => {
        const isActive = pathname === href;
        return (
          <Link
            key={href}
            href={href}
            className={cn(
              "flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-all",
              isActive
                ? "bg-accent/15 text-accent"
                : "text-text-secondary hover:bg-muted hover:text-text-primary",
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
