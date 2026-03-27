import useSWR from "swr";
import { fetchAPI } from "@/lib/api-client";
import type { RankingResult } from "@/types/api";
import type { FilterParams } from "@/types/filters";

export function useTopCustomers(filters?: FilterParams) {
  const key = filters
    ? ["/api/v1/analytics/customers/top", JSON.stringify(filters)]
    : "/api/v1/analytics/customers/top";

  const { data, error } = useSWR(key, () =>
    fetchAPI<RankingResult>("/api/v1/analytics/customers/top", filters),
  );
  return { data, error, isLoading: !data && !error };
}
