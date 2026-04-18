"use client";

/**
 * SWR hook for the first-insight picker endpoint (Phase 2 Task 3 / #402).
 *
 * Returns `{ insight, isLoading, error }`. The `insight` is null when the
 * tenant has no data yet, or when the picker cannot find a candidate.
 */

import useSWR from "swr";
import { fetchAPI, swrKey } from "@/lib/api-client";
import type { FirstInsight, FirstInsightResponse } from "@/types/api";

export function useFirstInsight() {
  const { data, error, isLoading } = useSWR<FirstInsightResponse>(
    swrKey("/api/v1/insights/first"),
    () => fetchAPI<FirstInsightResponse>("/api/v1/insights/first"),
    {
      revalidateOnFocus: false,
      shouldRetryOnError: false,
    },
  );

  const insight: FirstInsight | null = data?.insight ?? null;
  return { insight, isLoading, error };
}
