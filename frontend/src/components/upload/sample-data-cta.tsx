"use client";

/**
 * "Use sample pharma data" CTA (Phase 2 Task 1 / #400).
 *
 * Primary alternative on step 1 of the upload wizard: a single click that
 * asks the onboarding API to load a curated 5k-row pharma demo dataset
 * (#401) and redirects the user to the dashboard's first-insight view.
 *
 * Failures stay inline — we never swallow the error.
 */

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Sparkles, Loader2 } from "lucide-react";
import { postAPI } from "@/lib/api-client";

interface SampleLoadResult {
  rows_loaded: number;
  pipeline_run_id: string;
  duration_seconds: number;
}

export function SampleDataCta() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleClick() {
    setLoading(true);
    setError(null);
    try {
      await postAPI<SampleLoadResult>("/api/v1/onboarding/load-sample");
      router.push("/dashboard?first_upload=1");
    } catch {
      setError("Could not load sample data. Please try again.");
      setLoading(false);
    }
  }

  return (
    <div className="space-y-2">
      <button
        type="button"
        onClick={handleClick}
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
