import useSWR from "swr";
import { fetchAPI } from "@/lib/api-client";
import type { ReturnAnalysis } from "@/types/api";
import type { FilterParams } from "@/types/filters";

export function useReturns(filters?: FilterParams) {
  const key = filters
    ? ["/api/v1/analytics/returns", JSON.stringify(filters)]
    : "/api/v1/analytics/returns";

  const { data, error } = useSWR(key, () =>
    fetchAPI<ReturnAnalysis[]>("/api/v1/analytics/returns", filters),
  );
  return { data, error, isLoading: !data && !error };
}
