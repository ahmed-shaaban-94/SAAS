"use client";

import { cn } from "@/lib/utils";

const TIER_CONFIG: Record<string, { bg: string; text: string; label: string }> = {
  bronze: { bg: "bg-orange-900/20", text: "text-orange-400", label: "Bronze" },
  silver: { bg: "bg-slate-400/20", text: "text-slate-300", label: "Silver" },
  gold: { bg: "bg-yellow-500/20", text: "text-yellow-400", label: "Gold" },
  platinum: { bg: "bg-purple-500/20", text: "text-purple-400", label: "Platinum" },
  diamond: { bg: "bg-cyan-400/20", text: "text-cyan-300", label: "Diamond" },
};

interface TierBadgeProps {
  tier: string;
  className?: string;
  size?: "sm" | "md";
}

export function TierBadge({ tier, className, size = "sm" }: TierBadgeProps) {
  const config = TIER_CONFIG[tier] || TIER_CONFIG.bronze;
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full font-semibold uppercase tracking-wider",
        config.bg,
        config.text,
        size === "sm" ? "px-2 py-0.5 text-[10px]" : "px-3 py-1 text-xs",
        className,
      )}
    >
      {config.label}
    </span>
  );
}
