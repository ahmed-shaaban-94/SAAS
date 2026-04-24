"use client";

import useSWR from "swr";
import { fetchAPI, swrKey } from "@/lib/api-client";
import type { ApiGet } from "@/lib/api-types";

type PipelineRunList = ApiGet<"/api/v1/pipeline/runs">;
export type PipelineRun = PipelineRunList["items"][number];

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
