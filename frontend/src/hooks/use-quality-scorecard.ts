"use client";

import useSWR from "swr";
import { fetchAPI, swrKey } from "@/lib/api-client";
import type { ApiGet } from "@/lib/api-types";

export type QualityScorecard = ApiGet<"/api/v1/pipeline/quality/scorecard">;
export type RunScore = QualityScorecard["runs"][number];

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
