"use client";

import { cn } from "@/lib/utils";
import { Award, TrendingUp, Flame, Trophy, Zap } from "lucide-react";
import { useActivityFeed } from "@/hooks/use-gamification";
import { LoadingCard } from "@/components/loading-card";

const EVENT_CONFIG: Record<string, { icon: React.ComponentType<{ className?: string }>; color: string }> = {
  badge_earned: { icon: Award, color: "text-yellow-400" },
  level_up: { icon: TrendingUp, color: "text-green-400" },
  streak_milestone: { icon: Flame, color: "text-orange-400" },
  competition_win: { icon: Trophy, color: "text-purple-400" },
  xp_bonus: { icon: Zap, color: "text-blue-400" },
};

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;
  return new Date(dateStr).toLocaleDateString();
}

export function ActivityFeed() {
  const { data, isLoading } = useActivityFeed(20);

  if (isLoading) return <LoadingCard lines={6} />;
  if (!data?.length) {
    return (
      <div className="rounded-xl border border-border bg-card p-6 text-center text-sm text-text-secondary">
        No activity yet. Achievements will appear here as the team progresses.
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-border bg-card overflow-hidden">
      <div className="divide-y divide-border">
        {data.map((item) => {
          const config = EVENT_CONFIG[item.event_type] || EVENT_CONFIG.xp_bonus;
          const Icon = config.icon;
          return (
            <div key={item.id} className="flex items-start gap-3 px-4 py-3">
              <div className={cn("mt-0.5 flex h-7 w-7 items-center justify-center rounded-full bg-divider")}>
                <Icon className={cn("h-3.5 w-3.5", config.color)} />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm text-text-primary">
                  <span className="font-medium">{item.staff_name}</span>{" "}
                  <span className="text-text-secondary">{item.title}</span>
                </p>
                {item.description && (
                  <p className="text-xs text-text-secondary">{item.description}</p>
                )}
              </div>
              <span className="whitespace-nowrap text-[10px] text-text-secondary">
                {timeAgo(item.created_at)}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
