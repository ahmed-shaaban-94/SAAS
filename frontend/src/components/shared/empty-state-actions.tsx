"use client";

/**
 * Reusable primary-action slots for <EmptyState /> (Phase 2 Task 4 / #403).
 *
 * Two canonical options:
 * - LoadSampleAction  — one-click sample pharma dataset + redirect.
 * - UploadDataAction  — link to /upload for users who want to bring a file.
 *
 * Pages compose them inside <EmptyState action={...} /> to turn every
 * "nothing to show" into a next-step router, not a dead end.
 */

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Sparkles, Upload, Loader2 } from "lucide-react";

import { postAPI } from "@/lib/api-client";
import { trackUploadCompleted } from "@/lib/analytics-events";

interface SampleLoadResult {
  rows_loaded: number;
  pipeline_run_id: string;
  duration_seconds: number;
}

export function LoadSampleAction() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleClick() {
    setLoading(true);
    setError(null);
    try {
      const result = await postAPI<SampleLoadResult>(
        "/api/v1/onboarding/load-sample",
      );
      trackUploadCompleted({
        run_id: result.pipeline_run_id,
        duration_seconds: result.duration_seconds,
        rows_loaded: result.rows_loaded,
      });
      router.push("/dashboard?first_upload=1");
    } catch {
      setError("Could not load sample data. Please try again.");
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col items-center gap-2">
      <button
        type="button"
        onClick={handleClick}
        disabled={loading}
        className="inline-flex items-center gap-1.5 rounded-xl bg-accent px-4 py-2 text-sm font-semibold text-page transition-opacity disabled:cursor-not-allowed disabled:opacity-70 hover:opacity-90"
      >
        {loading ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" />
            Preparing sample…
          </>
        ) : (
          <>
            <Sparkles className="h-4 w-4" />
            Load sample data
          </>
        )}
      </button>
      {error && (
        <p role="alert" className="text-xs text-red-500">
          {error}
        </p>
      )}
    </div>
  );
}

export interface UploadDataActionProps {
  /** Custom label; defaults to "Upload your data". */
  label?: string;
  /** Custom href; defaults to `/upload`. */
  href?: string;
}

export function UploadDataAction({
  label = "Upload your data",
  href = "/upload",
}: UploadDataActionProps) {
  return (
    <Link
      href={href}
      className="inline-flex items-center gap-1.5 rounded-xl border border-border bg-background/50 px-4 py-2 text-sm font-semibold text-text-primary transition-colors hover:border-accent/40 hover:text-accent"
    >
      <Upload className="h-4 w-4" />
      {label}
    </Link>
  );
}
