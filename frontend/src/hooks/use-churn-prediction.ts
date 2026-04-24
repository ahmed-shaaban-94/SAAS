"use client";

import useSWR from "swr";
import { fetchAPI, swrKey } from "@/lib/api-client";
import type { ApiGet } from "@/lib/api-types";

type ChurnPredictionList = ApiGet<"/api/v1/analytics/customers/churn">;

export function useChurnPredictions(riskLevel?: string, limit = 50) {
  const params: Record<string, string> = { limit: String(limit) };
  if (riskLevel) params.risk_level = riskLevel;

  const { data, error, isLoading } = useSWR<ChurnPredictionList>(
    swrKey("/api/v1/analytics/customers/churn", params),
    () => fetchAPI<ChurnPredictionList>("/api/v1/analytics/customers/churn", params),
  );

  return { data: data ?? [], error, isLoading };
}
