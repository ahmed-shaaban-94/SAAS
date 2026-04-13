"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Plug, SlidersHorizontal, GitBranch, History, Activity } from "lucide-react";

const TABS = [
  { label: "Sources",   href: "/control-center/sources",   icon: Plug },
  { label: "Profiles",  href: "/control-center/profiles",  icon: SlidersHorizontal },
  { label: "Mappings",  href: "/control-center/mappings",  icon: GitBranch },
  { label: "Releases",  href: "/control-center/releases",  icon: History },
  { label: "Sync Runs", href: "/control-center/sync-runs", icon: Activity },
] as const;

export default function ControlCenterLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div>
      <nav className="mb-6 flex gap-1 overflow-x-auto border-b border-border/50 pb-0">
        {TABS.map(({ label, href, icon: Icon }) => {
          const active = pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-2 whitespace-nowrap border-b-2 px-4 py-2 text-sm font-medium transition-colors ${
                active
                  ? "border-primary text-primary"
                  : "border-transparent text-text-secondary hover:text-text-primary"
              }`}
            >
              <Icon className="h-4 w-4" />
              {label}
            </Link>
          );
        })}
      </nav>
      {children}
    </div>
  );
}
