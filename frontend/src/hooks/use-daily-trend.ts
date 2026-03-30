import useSWR from "swr";
import { fetchAPI, swrKey } from "@/lib/api-client";
import type { TrendResult } from "@/types/api";
import type { FilterParams } from "@/types/filters";

export function useDailyTrend(filters?: FilterParams) {
  const key = swrKey("/api/v1/analytics/trends/daily", filters);

  const { data, error, isLoading } = useSWR(key, () =>
    fetchAPI<TrendResult>("/api/v1/analytics/trends/daily", filters),
  );
  return { data, error, isLoading };
}
