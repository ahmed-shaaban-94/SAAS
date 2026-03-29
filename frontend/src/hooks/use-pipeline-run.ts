import useSWR from "swr";
import { fetchAPI } from "@/lib/api-client";
import type { PipelineRun } from "@/types/api";

export function usePipelineRun(runId: string | null) {
  const key = runId ? `/api/v1/pipeline/runs/${runId}` : null;

  const { data, error, isLoading, mutate } = useSWR(key, () =>
    key ? fetchAPI<PipelineRun>(key) : null,
  );

  return { data, error, isLoading, mutate };
}
