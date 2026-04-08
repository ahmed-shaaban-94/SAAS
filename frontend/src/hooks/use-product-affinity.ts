"use client";

import useSWR from "swr";
import { fetchAPI, swrKey } from "@/lib/api-client";

export interface AffinityPair {
  related_key: number;
  related_name: string;
  co_occurrence_count: number;
  support_pct: number;
  confidence: number;
}

export function useProductAffinity(productKey: number | undefined) {
  const { data, error, isLoading } = useSWR<AffinityPair[]>(
    productKey ? swrKey(`/api/v1/analytics/products/${productKey}/affinity`, {}) : null,
    () => fetchAPI<AffinityPair[]>(`/api/v1/analytics/products/${productKey}/affinity`),
  );

  return { data: data ?? [], error, isLoading };
}
