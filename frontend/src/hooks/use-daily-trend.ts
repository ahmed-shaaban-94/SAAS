import useSWR from "swr";
import { fetchAPI, swrKey } from "@/lib/api-client";
import type { ApiGet } from "@/lib/api-types";
import type { FilterParams } from "@/types/filters";

// Response shape sourced from the OpenAPI schema (issue #658 pilot).
type DailyTrendResponse = ApiGet<"/api/v1/analytics/trends/daily">;

export function useDailyTrend(filters?: FilterParams) {
  const key = swrKey("/api/v1/analytics/trends/daily", filters);

  const { data, error, isLoading } = useSWR(key, () =>
    fetchAPI<DailyTrendResponse>("/api/v1/analytics/trends/daily", filters),
  );
  return { data, error, isLoading };
}
