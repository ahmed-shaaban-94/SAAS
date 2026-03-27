import useSWR from "swr";
import { fetchAPI } from "@/lib/api-client";
import type { KPISummary } from "@/types/api";

export function useSummary(targetDate?: string) {
  const key = targetDate
    ? `/api/v1/analytics/summary?target_date=${targetDate}`
    : "/api/v1/analytics/summary";

  const { data, error } = useSWR(key, () =>
    fetchAPI<KPISummary>(
      `/api/v1/analytics/summary${targetDate ? `?target_date=${targetDate}` : ""}`,
    ),
  );
  return { data, error, isLoading: !data && !error };
}
