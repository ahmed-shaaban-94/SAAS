"use client";

import { cn } from "@/lib/utils";
import { TierBadge } from "./tier-badge";
import type { BadgeResponse, StaffBadgeResponse } from "@/hooks/use-gamification";
import {
  Sparkles, Target, Banknote, Gem, Flame, Zap,
  Users, TrendingUp, Crown, Award, Shield, Trophy,
} from "lucide-react";

const ICON_MAP: Record<string, React.ComponentType<{ className?: string }>> = {
  sparkles: Sparkles,
  target: Target,
  banknote: Banknote,
  gem: Gem,
  flame: Flame,
  fire: Flame,
  zap: Zap,
  users: Users,
  "trending-up": TrendingUp,
  crown: Crown,
  award: Award,
  shield: Shield,
  trophy: Trophy,
};

interface BadgeGridProps {
  allBadges: BadgeResponse[];
  earnedBadges: StaffBadgeResponse[];
  className?: string;
}

export function BadgeGrid({ allBadges, earnedBadges, className }: BadgeGridProps) {
  const earnedKeys = new Set(earnedBadges.map((b) => b.badge_key));

  return (
    <div className={cn("grid grid-cols-3 gap-3 sm:grid-cols-4 md:grid-cols-6", className)}>
      {allBadges.map((badge) => {
        const earned = earnedKeys.has(badge.badge_key);
        const Icon = ICON_MAP[badge.icon] || Trophy;
        const earnedBadge = earnedBadges.find((eb) => eb.badge_key === badge.badge_key);

        return (
          <div
            key={badge.badge_id}
            className={cn(
              "relative flex flex-col items-center gap-2 rounded-xl border p-3 text-center transition-all",
              earned
                ? "border-accent/30 bg-accent/5 shadow-sm"
                : "border-border bg-card opacity-40 grayscale",
            )}
            title={earned && earnedBadge
              ? `Earned: ${new Date(earnedBadge.earned_at).toLocaleDateString()}`
              : badge.description_en || badge.title_en
            }
          >
            <div
              className={cn(
                "flex h-10 w-10 items-center justify-center rounded-full",
                earned ? "bg-accent/15" : "bg-divider",
              )}
            >
              <Icon className={cn("h-5 w-5", earned ? "text-accent" : "text-text-secondary")} />
            </div>
            <span className="text-[11px] font-medium leading-tight text-text-primary">
              {badge.title_en}
            </span>
            <TierBadge tier={badge.tier} />
          </div>
        );
      })}
    </div>
  );
}
