"use client";

/**
 * Shared sample-dataset loader (Phase 2 follow-up #8).
 *
 * Consolidates the duplicated POST + trackUploadCompleted + redirect
 * logic that SampleDataCta and LoadSampleAction both needed. New CTAs
 * should compose this hook instead of reimplementing the sequence.
 */

import { useCallback, useState } from "react";
import { useRouter } from "next/navigation";

import { postAPI } from "@/lib/api-client";
import { trackUploadCompleted } from "@/lib/analytics-events";

interface SampleLoadResult {
  rows_loaded: number;
  pipeline_run_id: string;
  duration_seconds: number;
}

export interface UseLoadSampleOptions {
  /**
   * Destination path after a successful load. Pass `null` to skip the
   * redirect (caller will do its own navigation). Defaults to the
   * first-insight entry point: `/dashboard?first_upload=1`.
   */
  redirectTo?: string | null;
}

export interface UseLoadSampleResult {
  loading: boolean;
  error: string | null;
  loadSample: () => Promise<SampleLoadResult | null>;
}

const DEFAULT_REDIRECT = "/dashboard?first_upload=1";
const GENERIC_ERROR = "Could not load sample data. Please try again.";

export function useLoadSample(
  options: UseLoadSampleOptions = {},
): UseLoadSampleResult {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const redirectTo =
    options.redirectTo === null
      ? null
      : (options.redirectTo ?? DEFAULT_REDIRECT);

  const loadSample = useCallback(async (): Promise<SampleLoadResult | null> => {
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
      if (redirectTo !== null) {
        router.push(redirectTo);
      }
      setLoading(false);
      return result;
    } catch {
      setError(GENERIC_ERROR);
      setLoading(false);
      return null;
    }
  }, [redirectTo, router]);

  return { loading, error, loadSample };
}
