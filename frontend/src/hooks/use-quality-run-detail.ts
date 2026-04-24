"use client";

import useSWR from "swr";
import { fetchAPI, swrKey } from "@/lib/api-client";
import type { ApiGet } from "@/lib/api-types";

export type QualityRunDetail = ApiGet<"/api/v1/pipeline/runs/{run_id}/quality">;
export type QualityCheck = QualityRunDetail["checks"][number];

export function useQualityRunDetail(runId: string | null, stage?: string) {
  const params: Record<string, string | number> = {};
  if (stage) params.stage = stage;

  const key = runId
    ? swrKey(`/api/v1/pipeline/runs/${runId}/quality`, params)
    : null;

  const { data, error, isLoading } = useSWR<QualityRunDetail>(
    key,
    () => fetchAPI<QualityRunDetail>(`/api/v1/pipeline/runs/${runId}/quality`, params),
  );

  return {
    data: data ?? null,
    error,
    isLoading,
  };
}
