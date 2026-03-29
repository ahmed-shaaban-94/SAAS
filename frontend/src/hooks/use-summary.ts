import useSWR from "swr";
import { fetchAPI } from "@/lib/api-client";
import type { KPISummary } from "@/types/api";
import type { FilterParams } from "@/types/filters";

export function useSummary(filters?: FilterParams) {
  const params = new URLSearchParams();
  if (filters) {
    for (const [key, value] of Object.entries(filters)) {
      if (value !== undefined && value !== null) {
        params.set(key, String(value));
      }
    }
  }
  const qs = params.toString();
  const key = qs
    ? `/api/v1/analytics/summary?${qs}`
    : "/api/v1/analytics/summary";

  const { data, error } = useSWR(key, () =>
    fetchAPI<KPISummary>("/api/v1/analytics/summary", filters),
  );
  return { data, error, isLoading: !data && !error };
}
