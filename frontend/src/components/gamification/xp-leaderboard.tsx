"use client";

import Link from "next/link";
import { cn } from "@/lib/utils";
import { TierBadge } from "./tier-badge";
import { Crown, Medal, Award } from "lucide-react";
import { useXPLeaderboard } from "@/hooks/use-gamification";
import { LoadingCard } from "@/components/loading-card";
import { formatNumber } from "@/lib/formatters";

const PODIUM_ICONS = [Crown, Medal, Award];
const PODIUM_COLORS = ["text-yellow-400", "text-slate-300", "text-orange-400"];

export function XPLeaderboard() {
  const { data, isLoading } = useXPLeaderboard(20);

  if (isLoading) return <LoadingCard lines={8} className="h-96" />;
  if (!data?.length) {
    return (
      <div className="rounded-xl border border-border bg-card p-8 text-center text-sm text-text-secondary">
        No leaderboard data yet. XP will accumulate as the team makes sales.
      </div>
    );
  }

  const top3 = data.slice(0, 3);
  const rest = data.slice(3);

  return (
    <div className="space-y-4">
      {/* Top 3 Podium */}
      <div className="grid grid-cols-3 gap-3">
        {[1, 0, 2].map((idx) => {
          const entry = top3[idx];
          if (!entry) return <div key={idx} />;
          const Icon = PODIUM_ICONS[idx];
          return (
            <Link
              key={entry.staff_key}
              href={`/staff/${entry.staff_key}`}
              className={cn(
                "flex flex-col items-center gap-2 rounded-xl border border-border bg-card p-4 transition-colors hover:border-accent/40",
                idx === 0 && "ring-1 ring-yellow-500/20",
              )}
            >
              <Icon className={cn("h-6 w-6", PODIUM_COLORS[idx])} />
              <span className="text-sm font-semibold text-text-primary truncate w-full text-center">
                {entry.staff_name}
              </span>
              <TierBadge tier={entry.current_tier} />
              <div className="text-xs text-text-secondary">
                Lv.{entry.level} &middot; {formatNumber(entry.total_xp)} XP
              </div>
              <div className="text-[10px] text-text-secondary">
                {entry.badge_count} badges
              </div>
            </Link>
          );
        })}
      </div>

      {/* Rest of the list */}
      {rest.length > 0 && (
        <div className="rounded-xl border border-border bg-card overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-card-header">
                <th className="px-4 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-text-secondary">#</th>
                <th className="px-4 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-text-secondary">Name</th>
                <th className="px-4 py-2.5 text-center text-[11px] font-semibold uppercase tracking-wider text-text-secondary">Level</th>
                <th className="px-4 py-2.5 text-right text-[11px] font-semibold uppercase tracking-wider text-text-secondary">XP</th>
                <th className="px-4 py-2.5 text-center text-[11px] font-semibold uppercase tracking-wider text-text-secondary">Tier</th>
                <th className="px-4 py-2.5 text-center text-[11px] font-semibold uppercase tracking-wider text-text-secondary">Badges</th>
              </tr>
            </thead>
            <tbody>
              {rest.map((entry) => (
                <tr key={entry.staff_key} className="border-b border-border last:border-0 hover:bg-divider/50 transition-colors">
                  <td className="px-4 py-2.5 text-text-secondary">{entry.rank}</td>
                  <td className="px-4 py-2.5">
                    <Link href={`/staff/${entry.staff_key}`} className="font-medium text-text-primary hover:text-accent">
                      {entry.staff_name}
                    </Link>
                  </td>
                  <td className="px-4 py-2.5 text-center text-text-primary">{entry.level}</td>
                  <td className="px-4 py-2.5 text-right text-text-primary">{formatNumber(entry.total_xp)}</td>
                  <td className="px-4 py-2.5 text-center"><TierBadge tier={entry.current_tier} /></td>
                  <td className="px-4 py-2.5 text-center text-text-secondary">{entry.badge_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
