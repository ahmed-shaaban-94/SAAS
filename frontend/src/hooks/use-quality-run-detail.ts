"use client";

import useSWR from "swr";
import { fetchAPI, swrKey } from "@/lib/api-client";

export interface QualityCheck {
  check_name: string;
  stage: string;
  severity: "error" | "warn";
  passed: boolean;
  message: string;
  details: Record<string, unknown> | null;
}

export interface QualityRunDetail {
  run_id: string;
  checks: QualityCheck[];
  total_checks: number;
  passed: number;
  failed: number;
  warned: number;
}

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
