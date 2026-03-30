import useSWR from "swr";
import { fetchAPI, swrKey } from "@/lib/api-client";
import type { RankingResult } from "@/types/api";
import type { FilterParams } from "@/types/filters";

export function useTopProducts(filters?: FilterParams) {
  const key = swrKey("/api/v1/analytics/products/top", filters);

  const { data, error, isLoading } = useSWR(key, () =>
    fetchAPI<RankingResult>("/api/v1/analytics/products/top", filters),
  );
  return { data, error, isLoading };
}
