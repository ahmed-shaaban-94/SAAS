import useSWR from "swr";
import { fetchAPI } from "@/lib/api-client";
import type { RankingResult } from "@/types/api";
import type { FilterParams } from "@/types/filters";

export function useSites(filters?: FilterParams) {
  const key = filters
    ? ["/api/v1/analytics/sites", JSON.stringify(filters)]
    : "/api/v1/analytics/sites";

  const { data, error } = useSWR(key, () =>
    fetchAPI<RankingResult>("/api/v1/analytics/sites", filters),
  );
  return { data, error, isLoading: !data && !error };
}
