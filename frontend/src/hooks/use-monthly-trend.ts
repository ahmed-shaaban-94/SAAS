import useSWR from "swr";
import { fetchAPI } from "@/lib/api-client";
import type { TrendResult } from "@/types/api";
import type { FilterParams } from "@/types/filters";

export function useMonthlyTrend(filters?: FilterParams) {
  const key = filters
    ? ["/api/v1/analytics/trends/monthly", JSON.stringify(filters)]
    : "/api/v1/analytics/trends/monthly";

  const { data, error } = useSWR(key, () =>
    fetchAPI<TrendResult>("/api/v1/analytics/trends/monthly", filters),
  );
  return { data, error, isLoading: !data && !error };
}
