"use client";

import useSWR from "swr";
import { fetchAPI, swrKey } from "@/lib/api-client";
import type { ApiGet } from "@/lib/api-types";

type AffinityResponse = ApiGet<"/api/v1/analytics/products/{product_key}/affinity">;

export function useProductAffinity(productKey: number | undefined) {
  const { data, error, isLoading } = useSWR<AffinityResponse>(
    productKey ? swrKey(`/api/v1/analytics/products/${productKey}/affinity`, {}) : null,
    () => fetchAPI<AffinityResponse>(`/api/v1/analytics/products/${productKey}/affinity`),
  );

  return { data: data ?? [], error, isLoading };
}
