"use client";

import useSWR from "swr";
import { fetchAPI, swrKey } from "@/lib/api-client";

export interface PipelineRun {
  id: string;
  tenant_id: number;
  run_type: string;
  status: string;
  trigger_source: string | null;
  started_at: string;
  finished_at: string | null;
  duration_seconds: number | null;
  rows_loaded: number | null;
  error_message: string | null;
  metadata: Record<string, unknown>;
}

interface PipelineRunList {
  items: PipelineRun[];
  total: number;
  offset: number;
  limit: number;
}

export function usePipelineRuns(limit = 5) {
  const { data, error, isLoading, mutate } = useSWR<PipelineRunList>(
    swrKey("/api/v1/pipeline/runs", { limit, offset: 0 }),
    () => fetchAPI<PipelineRunList>("/api/v1/pipeline/runs", { limit, offset: 0 }),
  );

  return {
    runs: data?.items ?? [],
    total: data?.total ?? 0,
    error,
    isLoading,
    mutate,
  };
}
