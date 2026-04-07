"use client";

import useSWR from "swr";
import { fetchAPI, swrKey } from "@/lib/api-client";

export interface RunScore {
  run_id: string;
  run_type: string;
  status: string;
  started_at: string;
  total_checks: number;
  passed: number;
  failed: number;
  warned: number;
  pass_rate: number;
}

export interface QualityScorecard {
  runs: RunScore[];
  overall_pass_rate: number;
  total_runs: number;
}

export function useQualityScorecard(limit = 20) {
  const { data, error, isLoading } = useSWR<QualityScorecard>(
    swrKey("/api/v1/pipeline/quality/scorecard", { limit }),
    () => fetchAPI<QualityScorecard>("/api/v1/pipeline/quality/scorecard", { limit }),
  );

  return {
    data: data ?? { runs: [], overall_pass_rate: 0, total_runs: 0 },
    error,
    isLoading,
  };
}
