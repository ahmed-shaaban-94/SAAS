"use client";

import { cn } from "@/lib/utils";
import { Trophy, Clock, CheckCircle, XCircle } from "lucide-react";
import type { CompetitionResponse } from "@/hooks/use-gamification";

const STATUS_CONFIG: Record<string, { icon: React.ComponentType<{ className?: string }>; color: string; label: string }> = {
  upcoming: { icon: Clock, color: "text-blue-400", label: "Upcoming" },
  active: { icon: Trophy, color: "text-green-400", label: "Active" },
  completed: { icon: CheckCircle, color: "text-text-secondary", label: "Completed" },
  cancelled: { icon: XCircle, color: "text-red-400", label: "Cancelled" },
};

const METRIC_LABELS: Record<string, string> = {
  revenue: "Revenue",
  transactions: "Transactions",
  customers: "Customers",
  returns_reduction: "Returns Reduction",
};

interface CompetitionCardProps {
  competition: CompetitionResponse;
  onClick?: () => void;
  className?: string;
}

export function CompetitionCard({ competition, onClick, className }: CompetitionCardProps) {
  const status = STATUS_CONFIG[competition.status] || STATUS_CONFIG.upcoming;
  const StatusIcon = status.icon;

  const start = new Date(competition.start_date);
  const end = new Date(competition.end_date);
  const now = new Date();
  const totalDays = Math.ceil((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24));
  const elapsedDays = Math.max(0, Math.ceil((now.getTime() - start.getTime()) / (1000 * 60 * 60 * 24)));
  const progressPct = competition.status === "active"
    ? Math.min((elapsedDays / totalDays) * 100, 100)
    : competition.status === "completed" ? 100 : 0;

  return (
    <button
      onClick={onClick}
      className={cn(
        "w-full rounded-xl border border-border bg-card p-4 text-left transition-all hover:border-accent/40 hover:shadow-sm",
        className,
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-semibold text-text-primary truncate">{competition.title}</h3>
          {competition.description && (
            <p className="mt-0.5 text-xs text-text-secondary line-clamp-2">{competition.description}</p>
          )}
        </div>
        <div className={cn("flex items-center gap-1 text-xs font-medium", status.color)}>
          <StatusIcon className="h-3.5 w-3.5" />
          {status.label}
        </div>
      </div>

      <div className="mt-3 flex items-center gap-4 text-xs text-text-secondary">
        <span>{METRIC_LABELS[competition.metric] || competition.metric}</span>
        <span>{competition.competition_type}</span>
        <span>{start.toLocaleDateString()} — {end.toLocaleDateString()}</span>
      </div>

      {competition.status === "active" && (
        <div className="mt-3">
          <div className="h-1.5 w-full rounded-full bg-divider overflow-hidden">
            <div
              className="h-full rounded-full bg-accent transition-all duration-500"
              style={{ width: `${progressPct}%` }}
            />
          </div>
          <div className="mt-1 text-right text-[10px] text-text-secondary">
            {Math.max(0, totalDays - elapsedDays)} days remaining
          </div>
        </div>
      )}

      {competition.prize_description && (
        <div className="mt-2 rounded-lg bg-accent/5 px-3 py-1.5 text-xs text-accent">
          Prize: {competition.prize_description}
        </div>
      )}
    </button>
  );
}
