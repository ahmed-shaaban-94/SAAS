import useSWR from "swr";
import { fetchAPI } from "@/lib/api-client";
import type { TrendResult } from "@/types/api";
import type { FilterParams } from "@/types/filters";

export function useDailyTrend(filters?: FilterParams) {
  const key = filters
    ? ["/api/v1/analytics/trends/daily", JSON.stringify(filters)]
    : "/api/v1/analytics/trends/daily";

  const { data, error } = useSWR(key, () =>
    fetchAPI<TrendResult>("/api/v1/analytics/trends/daily", filters),
  );
  return { data, error, isLoading: !data && !error };
}
