"use client";

/**
 * "Use sample pharma data" CTA (Phase 2 Task 1 / #400).
 *
 * Primary alternative on step 1 of the upload wizard. Delegates the
 * endpoint call + tracker + redirect to `useLoadSample` (follow-up #8)
 * so the logic stays in one place.
 */

import { Sparkles, Loader2 } from "lucide-react";
import { useLoadSample } from "@/hooks/use-load-sample";

export function SampleDataCta() {
  const { loading, error, loadSample } = useLoadSample();

  return (
    <div className="space-y-2">
      <button
        type="button"
        onClick={() => void loadSample()}
        disabled={loading}
        className="viz-panel-soft flex w-full items-center justify-center gap-2 rounded-[1.5rem] border border-accent/30 bg-accent/8 px-5 py-4 text-sm font-semibold text-text-primary transition-colors hover:bg-accent/12 disabled:cursor-not-allowed disabled:opacity-70"
      >
        {loading ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" />
            Preparing sample pharma data…
          </>
        ) : (
          <>
            <Sparkles className="h-4 w-4 text-accent" />
            Use sample pharma data
          </>
        )}
      </button>
      <p className="text-center text-xs text-text-tertiary">
        5 000 rows from a 10-branch pharma chain. No signup, no file required.
      </p>
      {error && (
        <div
          role="alert"
          className="rounded-xl border border-red-500/20 bg-red-500/8 px-3 py-2 text-xs text-red-500"
        >
          {error}
        </div>
      )}
    </div>
  );
}
