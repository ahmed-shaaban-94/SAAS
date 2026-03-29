import useSWR from "swr";
import { fetchAPI } from "@/lib/api-client";
import type { RankingResult } from "@/types/api";
import type { FilterParams } from "@/types/filters";

export function useTopStaff(filters?: FilterParams) {
  const key = filters
    ? ["/api/v1/analytics/staff/top", JSON.stringify(filters)]
    : "/api/v1/analytics/staff/top";

  const { data, error, isLoading } = useSWR(key, () =>
    fetchAPI<RankingResult>("/api/v1/analytics/staff/top", filters),
  );
  return { data, error, isLoading };
}
