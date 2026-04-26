"use client";

import { cn } from "@/lib/utils";
import { TierBadge } from "./tier-badge";
import { XPProgressBar } from "./xp-progress-bar";
import { Award, Flame, Trophy } from "lucide-react";
import type { GamificationProfile } from "@/hooks/use-gamification";
import { formatNumber } from "@/lib/formatters";

interface PlayerCardProps {
  profile: GamificationProfile;
  className?: string;
}

export function PlayerCard({ profile, className }: PlayerCardProps) {
  const activeStreak = profile.streaks.reduce((best, s) =>
    s.current_count > best ? s.current_count : best, 0,
  );

  return (
    <div className={cn("rounded-xl border border-border bg-card p-5", className)}>
      <div className="flex items-start gap-4">
        {/* Level Circle */}
        <div className="flex h-16 w-16 flex-shrink-0 items-center justify-center rounded-full bg-accent/10 ring-2 ring-accent/30">
          <span className="text-2xl font-bold text-accent">{profile.level}</span>
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h3 className="text-lg font-semibold text-text-primary truncate">
              {profile.staff_name || `Staff #${profile.staff_key}`}
            </h3>
            <TierBadge tier={profile.current_tier} size="md" />
          </div>

          <XPProgressBar
            totalXP={profile.total_xp}
            xpToNext={profile.xp_to_next_level}
            level={profile.level}
            className="mt-2"
          />
        </div>
      </div>

      {/* Quick Stats */}
      <div className="mt-4 grid grid-cols-3 gap-3">
        <div className="flex items-center gap-2 rounded-lg bg-divider/50 px-3 py-2">
          <Award className="h-4 w-4 text-yellow-400" />
          <div>
            <p className="text-xs text-text-secondary">Badges</p>
            <p className="text-sm font-semibold text-text-primary">{profile.badge_count}</p>
          </div>
        </div>
        <div className="flex items-center gap-2 rounded-lg bg-divider/50 px-3 py-2">
          <Flame className="h-4 w-4 text-orange-400" />
          <div>
            <p className="text-xs text-text-secondary">Streak</p>
            <p className="text-sm font-semibold text-text-primary">{activeStreak} days</p>
          </div>
        </div>
        <div className="flex items-center gap-2 rounded-lg bg-divider/50 px-3 py-2">
          <Trophy className="h-4 w-4 text-accent" />
          <div>
            <p className="text-xs text-text-secondary">Total XP</p>
            <p className="text-sm font-semibold text-text-primary">{formatNumber(profile.total_xp)}</p>
          </div>
        </div>
      </div>
    </div>
  );
}
