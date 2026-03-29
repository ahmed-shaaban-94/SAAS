import useSWR from "swr";
import { fetchAPI } from "@/lib/api-client";
import type { PipelineRunList } from "@/types/api";

interface PipelineRunsParams {
  status?: string;
  offset?: number;
  limit?: number;
}

export function usePipelineRuns(params?: PipelineRunsParams) {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set("status", params.status);
  if (params?.offset !== undefined) searchParams.set("offset", String(params.offset));
  if (params?.limit !== undefined) searchParams.set("limit", String(params.limit));

  const qs = searchParams.toString();
  // Query params are embedded in the path so SWR uses the full URL (with params) as cache key
  const key = `/api/v1/pipeline/runs${qs ? `?${qs}` : ""}`;

  const { data, error, isLoading, mutate } = useSWR(key, () =>
    fetchAPI<PipelineRunList>(key),
  );

  return { data, error, isLoading, mutate };
}
