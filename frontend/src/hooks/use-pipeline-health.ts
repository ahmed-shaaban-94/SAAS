import useSWR from "swr";
import { fetchAPI } from "@/lib/api-client";
import type { PipelineHealth } from "@/types/api";

/**
 * Composite pipeline health payload for the dashboard card (#509).
 *
 * Single call replaces three (``/pipeline/runs``, ``/quality/scorecard``,
 * scheduler next-run). Refreshes every 60s while the tab is focused so
 * the "Running..." node updates without a manual reload.
 */
export function usePipelineHealth() {
  const { data, error, isLoading } = useSWR<PipelineHealth>(
    "/api/v1/pipeline/health",
    () => fetchAPI<PipelineHealth>("/api/v1/pipeline/health"),
    { refreshInterval: 60_000 },
  );
  return { data, error, isLoading };
}
