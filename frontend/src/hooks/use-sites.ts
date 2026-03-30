import useSWR from "swr";
import { fetchAPI, swrKey } from "@/lib/api-client";
import type { RankingResult } from "@/types/api";
import type { FilterParams } from "@/types/filters";

export function useSites(filters?: FilterParams) {
  const key = swrKey("/api/v1/analytics/sites", filters);

  const { data, error, isLoading } = useSWR(key, () =>
    fetchAPI<RankingResult>("/api/v1/analytics/sites", filters),
  );
  return { data, error, isLoading };
}
