"use client";

import { useState } from "react";
import { Trophy, Award, Flame, Swords, Activity } from "lucide-react";
import { cn } from "@/lib/utils";
import { XPLeaderboard } from "./xp-leaderboard";
import { ActivityFeed } from "./activity-feed";
import { CompetitionCard } from "./competition-card";
import { BadgeGrid } from "./badge-grid";
import { useCompetitions, useBadges, useStaffBadges, useXPLeaderboard } from "@/hooks/use-gamification";
import { LoadingCard } from "@/components/loading-card";

type Tab = "leaderboard" | "badges" | "competitions" | "feed";

const TABS: { key: Tab; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
  { key: "leaderboard", label: "Leaderboard", icon: Trophy },
  { key: "badges", label: "Badges", icon: Award },
  { key: "competitions", label: "Competitions", icon: Swords },
  { key: "feed", label: "Activity", icon: Activity },
];

export function GamificationDashboard() {
  const [activeTab, setActiveTab] = useState<Tab>("leaderboard");

  return (
    <div className="space-y-6">
      {/* Tab Navigation */}
      <div className="flex gap-1 rounded-xl border border-border bg-card p-1">
        {TABS.map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={cn(
                "flex flex-1 items-center justify-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                activeTab === tab.key
                  ? "bg-accent/10 text-accent"
                  : "text-text-secondary hover:bg-divider hover:text-text-primary",
              )}
            >
              <Icon className="h-4 w-4" />
              <span className="hidden sm:inline">{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Tab Content */}
      {activeTab === "leaderboard" && <XPLeaderboard />}
      {activeTab === "badges" && <BadgesTab />}
      {activeTab === "competitions" && <CompetitionsTab />}
      {activeTab === "feed" && <ActivityFeed />}
    </div>
  );
}

function BadgesTab() {
  const { data: allBadges, isLoading: loadingBadges } = useBadges();
  const { data: leaderboard } = useXPLeaderboard(50);
  const [selectedStaffKey, setSelectedStaffKey] = useState<number>(0);
  const { data: earnedBadges } = useStaffBadges(selectedStaffKey);

  if (loadingBadges) return <LoadingCard lines={6} />;
  if (!allBadges?.length) {
    return (
      <div className="rounded-xl border border-border bg-card p-8 text-center text-sm text-text-secondary">
        No badges defined yet.
      </div>
    );
  }

  const selectedName = leaderboard?.find((s) => s.staff_key === selectedStaffKey)?.staff_name;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <h3 className="text-sm font-semibold text-text-primary">All Available Badges</h3>
        <div className="flex items-center gap-2">
          {/* Staff selector for viewing earned badges */}
          <select
            value={selectedStaffKey}
            onChange={(e) => setSelectedStaffKey(Number(e.target.value))}
            className="rounded-lg border border-border bg-card px-3 py-1.5 text-xs text-text-primary focus:border-accent focus:outline-none"
          >
            <option value={0}>All badges (no staff)</option>
            {leaderboard?.map((s) => (
              <option key={s.staff_key} value={s.staff_key}>
                {s.staff_name}
              </option>
            ))}
          </select>
          <span className="text-xs text-text-secondary">{allBadges.length} total</span>
        </div>
      </div>
      {selectedStaffKey > 0 && selectedName && (
        <p className="text-xs text-text-secondary">
          Showing earned badges for <span className="font-medium text-text-primary">{selectedName}</span>
          {earnedBadges ? ` — ${earnedBadges.length} earned` : ""}
        </p>
      )}
      <BadgeGrid allBadges={allBadges} earnedBadges={earnedBadges || []} />
    </div>
  );
}

function CompetitionsTab() {
  const { data: competitions, isLoading } = useCompetitions();

  if (isLoading) return <LoadingCard lines={4} />;
  if (!competitions?.length) {
    return (
      <div className="rounded-xl border border-border bg-card p-8 text-center text-sm text-text-secondary">
        No competitions yet. Create one to get started!
      </div>
    );
  }

  const active = competitions.filter((c) => c.status === "active");
  const upcoming = competitions.filter((c) => c.status === "upcoming");
  const completed = competitions.filter((c) => c.status === "completed");

  return (
    <div className="space-y-6">
      {active.length > 0 && (
        <div>
          <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-text-primary">
            <Flame className="h-4 w-4 text-green-400" /> Active
          </h3>
          <div className="grid gap-3 md:grid-cols-2">
            {active.map((c) => <CompetitionCard key={c.competition_id} competition={c} />)}
          </div>
        </div>
      )}
      {upcoming.length > 0 && (
        <div>
          <h3 className="mb-3 text-sm font-semibold text-text-primary">Upcoming</h3>
          <div className="grid gap-3 md:grid-cols-2">
            {upcoming.map((c) => <CompetitionCard key={c.competition_id} competition={c} />)}
          </div>
        </div>
      )}
      {completed.length > 0 && (
        <div>
          <h3 className="mb-3 text-sm font-semibold text-text-primary">Completed</h3>
          <div className="grid gap-3 md:grid-cols-2">
            {completed.map((c) => <CompetitionCard key={c.competition_id} competition={c} />)}
          </div>
        </div>
      )}
    </div>
  );
}
