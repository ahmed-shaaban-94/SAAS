"use client";

import Link from "next/link";
import { ArrowRight, AlertTriangle } from "lucide-react";
import { useTopInsight } from "@/hooks/use-top-insight";
import type { TopInsight } from "@/types/api";
import { cn } from "@/lib/utils";

export interface AlertBannerProps {
  /** Override the hook — useful for Storybook / tests. */
  insight?: TopInsight | null;
  className?: string;
}

const CONFIDENCE_TONE: Record<TopInsight["confidence"], string> = {
  high: "border-red-500/40 bg-red-500/5 text-red-100",
  medium: "border-amber-500/40 bg-amber-500/5 text-amber-100",
  low: "border-cyan-500/40 bg-cyan-500/5 text-cyan-100",
  info: "border-white/10 bg-white/5 text-text-secondary",
};

function formatImpact(egp: number): string {
  if (egp >= 1_000_000) return `EGP ${(egp / 1_000_000).toFixed(1)}M`;
  if (egp >= 1_000) return `EGP ${Math.round(egp / 1_000)}K`;
  return `EGP ${Math.round(egp)}`;
}

/**
 * Dashboard alert banner — renders the single most-attention-worthy
 * insight surfaced by ``/ai-light/top-insight`` (#510). Hides silently
 * when the endpoint returns 204 (no data) or during initial load.
 */
export function AlertBanner({ insight, className }: AlertBannerProps) {
  const hookResult = useTopInsight();
  // Allow an explicit `insight` prop to short-circuit the hook — makes
  // the component easy to drive in tests / Storybook without MSW.
  const data = insight !== undefined ? insight : hookResult.data;

  if (!data) return null;

  return (
    <div
      role="status"
      aria-label={`AI insight: ${data.title}`}
      className={cn(
        "viz-panel flex flex-col gap-3 rounded-2xl border p-4 sm:flex-row sm:items-center sm:justify-between",
        CONFIDENCE_TONE[data.confidence] ?? CONFIDENCE_TONE.info,
        className,
      )}
    >
      <div className="flex flex-1 items-start gap-3">
        <AlertTriangle
          aria-hidden="true"
          className="mt-0.5 h-5 w-5 shrink-0 text-current"
        />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold leading-tight text-text-primary">
            {data.title}
          </p>
          <p className="mt-1 text-xs leading-snug text-text-secondary">
            {data.body}
            {data.expected_impact_egp != null && data.expected_impact_egp > 0 && (
              <>
                {" "}
                <span className="font-medium text-text-primary">
                  Expected impact: {formatImpact(data.expected_impact_egp)}
                </span>
              </>
            )}
          </p>
        </div>
      </div>
      <Link
        href={data.action_target}
        className={cn(
          "inline-flex items-center gap-1.5 self-start whitespace-nowrap rounded-lg px-3 py-1.5",
          "text-xs font-semibold border border-current/30",
          "hover:bg-current/10 focus:outline-none focus-visible:ring-2 focus-visible:ring-current",
          "transition-colors",
        )}
      >
        {data.action_label}
        <ArrowRight aria-hidden="true" className="h-3.5 w-3.5" />
      </Link>
    </div>
  );
}
