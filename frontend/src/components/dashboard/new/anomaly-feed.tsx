"use client";

import { TrendingUp, TrendingDown, Info } from "lucide-react";
import { useAnomalyCards } from "@/hooks/use-anomaly-cards";
import type { AnomalyCard } from "@/types/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { SkeletonEnhanced } from "@/components/ui/skeleton-enhanced";
import { cn } from "@/lib/utils";

export interface AnomalyFeedProps {
  /** Override the hook — useful for Storybook / tests. */
  items?: AnomalyCard[];
  limit?: number;
  className?: string;
}

const KIND_ICON: Record<AnomalyCard["kind"], typeof TrendingUp> = {
  up: TrendingUp,
  down: TrendingDown,
  info: Info,
};

const KIND_ACCENT: Record<AnomalyCard["kind"], string> = {
  up: "text-cyan-300",
  down: "text-red-300",
  info: "text-text-secondary",
};

const CONFIDENCE_BADGE: Record<AnomalyCard["confidence"], string> = {
  high: "bg-red-500/15 text-red-200 border-red-500/30",
  medium: "bg-amber-500/15 text-amber-200 border-amber-500/30",
  low: "bg-cyan-500/15 text-cyan-200 border-cyan-500/30",
  info: "bg-white/5 text-text-secondary border-white/10",
};

/**
 * Dashboard anomaly-feed widget — renders the top unsuppressed anomalies
 * returned by ``/anomalies/cards`` (#508). The backend pre-computes
 * title / body / time_ago / confidence so the UI is pure display.
 */
export function AnomalyFeed({ items, limit = 10, className }: AnomalyFeedProps) {
  const hookResult = useAnomalyCards(limit);
  const data = items !== undefined ? items : hookResult.data;
  const isLoading = items === undefined && hookResult.isLoading;

  return (
    <Card className={cn("flex flex-col", className)}>
      <CardHeader className="pb-3">
        <CardTitle>Anomalies</CardTitle>
      </CardHeader>
      <CardContent className="flex-1 space-y-2 p-4 pt-0">
        {isLoading && (
          <div role="status" aria-label="Loading anomalies">
            <SkeletonEnhanced className="h-16" lines={3} />
          </div>
        )}
        {!isLoading && data && data.length === 0 && (
          <p className="py-8 text-center text-sm text-text-secondary">
            No active anomalies — metrics are tracking expected ranges.
          </p>
        )}
        {!isLoading &&
          data &&
          data.length > 0 &&
          data.map((card) => {
            const Icon = KIND_ICON[card.kind] ?? Info;
            return (
              <article
                key={card.id}
                className="rounded-xl border border-white/5 bg-white/[0.015] p-3 transition-colors hover:bg-white/[0.03]"
              >
                <div className="flex items-start gap-3">
                  <Icon
                    aria-hidden="true"
                    className={cn("mt-0.5 h-4 w-4 shrink-0", KIND_ACCENT[card.kind])}
                  />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-start justify-between gap-2">
                      <h4 className="text-sm font-semibold leading-tight text-text-primary">
                        {card.title}
                      </h4>
                      <span
                        className={cn(
                          "shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide",
                          CONFIDENCE_BADGE[card.confidence] ?? CONFIDENCE_BADGE.info,
                        )}
                      >
                        {card.confidence}
                      </span>
                    </div>
                    <p className="mt-1 text-xs leading-snug text-text-secondary">
                      {card.body}
                    </p>
                    <p className="mt-1.5 text-[11px] text-text-secondary/70">{card.time_ago}</p>
                  </div>
                </div>
              </article>
            );
          })}
      </CardContent>
    </Card>
  );
}
