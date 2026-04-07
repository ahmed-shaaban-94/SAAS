"use client";

import useSWR from "swr";
import { fetchAPI, swrKey } from "@/lib/api-client";

export interface ChurnPrediction {
  customer_key: number;
  customer_name: string;
  health_score: number;
  health_band: string;
  recency_days: number;
  frequency_3m: number;
  monetary_3m: number;
  trend: string;
  rfm_segment: string;
  churn_probability: number;
  risk_level: string;
}

export function useChurnPredictions(riskLevel?: string, limit = 50) {
  const params: Record<string, string> = { limit: String(limit) };
  if (riskLevel) params.risk_level = riskLevel;

  const { data, error, isLoading } = useSWR<ChurnPrediction[]>(
    swrKey("/api/v1/analytics/customers/churn", params),
    () => fetchAPI<ChurnPrediction[]>("/api/v1/analytics/customers/churn", params),
  );

  return { data: data ?? [], error, isLoading };
}
