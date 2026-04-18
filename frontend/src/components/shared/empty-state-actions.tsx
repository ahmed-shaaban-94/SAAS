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

import Link from "next/link";
import { Sparkles, Upload, Loader2 } from "lucide-react";

import { useLoadSample } from "@/hooks/use-load-sample";

export function LoadSampleAction() {
  const { loading, error, loadSample } = useLoadSample();

  return (
    <div className="flex flex-col items-center gap-2">
      <button
        type="button"
        onClick={() => void loadSample()}
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
