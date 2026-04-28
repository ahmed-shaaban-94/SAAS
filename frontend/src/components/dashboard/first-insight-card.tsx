"use client";

/**
 * First-Insight Card (Phase 2 Task 3 / #402).
 *
 * Shown on the dashboard after a new user's first upload. Renders the
 * single highest-priority insight the picker (GET /api/v1/insights/first)
 * returned, with a dismiss button that persists to sessionStorage. A
 * backend-backed dismissal timestamp on `users.onboarding_state` is a
 * follow-up (#404 or separate).
 */

import { useEffect, useState } from "react";
import Link from "next/link";
import { Sparkles, X, ArrowRight } from "lucide-react";

import { useFirstInsight } from "@/hooks/use-first-insight";
import { useOnboarding } from "@/hooks/use-onboarding";
import { trackFirstInsightSeen } from "@/lib/analytics-events";

const DISMISS_KEY = "ttfi_first_insight_dismissed";

export function FirstInsightCard() {
  const { insight, isLoading } = useFirstInsight();
  const { dismissFirstInsight } = useOnboarding();
  const [dismissed, setDismissed] = useState<boolean>(() => {
    if (typeof sessionStorage === "undefined") return false;
    return sessionStorage.getItem(DISMISS_KEY) === "1";
  });

  useEffect(() => {
    if (dismissed && typeof sessionStorage !== "undefined") {
      sessionStorage.setItem(DISMISS_KEY, "1");
    }
  }, [dismissed]);

  // Fire the Task 0 funnel event when the card actually renders with
  // content — this is what "the user saw a first insight" really means.
  // The tracker is session-idempotent so remounts do not double-fire.
  useEffect(() => {
    if (!dismissed && !isLoading && insight) {
      trackFirstInsightSeen({
        kind: insight.kind,
        confidence: insight.confidence,
      });
    }
  }, [dismissed, isLoading, insight]);

  if (dismissed || isLoading || !insight) return null;

  const confidencePct = Math.round(insight.confidence * 100);

  return (
    <div
      role="region"
      aria-label="First insight"
      className="viz-panel relative mb-6 rounded-[1.75rem] border border-accent/30 bg-accent/6 p-5"
    >
      <button
        type="button"
        aria-label="Dismiss first insight"
        onClick={() => {
          setDismissed(true);
          void dismissFirstInsight().catch(() => undefined);
        }}
        className="absolute right-3 top-3 rounded-full p-1.5 text-text-secondary transition-colors hover:bg-background/60 hover:text-text-primary"
      >
        <X className="h-4 w-4" />
      </button>

      <div className="flex items-start gap-3">
        <div className="viz-panel-soft flex h-9 w-9 shrink-0 items-center justify-center rounded-xl">
          <Sparkles className="h-4 w-4 text-accent" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-accent">
              First insight
            </p>
            <span className="rounded-full bg-background/50 px-2 py-0.5 text-[10px] font-medium text-text-secondary">
              Confidence: {confidencePct}%
            </span>
          </div>
          <h3 className="mt-1 text-base font-semibold text-text-primary">
            {insight.title}
          </h3>
          <p className="mt-1 text-sm text-text-secondary">{insight.body}</p>
          <div className="mt-3 flex items-center gap-3">
            <Link
              href={insight.action_href}
              className="text-xs font-semibold text-accent hover:underline"
            >
              Open →
            </Link>
            <Link
              href="/dashboard"
              className="inline-flex items-center gap-1 text-xs font-medium text-text-secondary hover:text-text-primary"
            >
              View more insights
              <ArrowRight className="h-3 w-3" />
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
