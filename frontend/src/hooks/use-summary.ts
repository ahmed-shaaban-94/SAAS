import useSWR from "swr";
import { fetchAPI } from "@/lib/api-client";
import type { KPISummary } from "@/types/api";
import type { FilterParams } from "@/types/filters";

export function useSummary(filters?: FilterParams) {
  // The /summary endpoint accepts `target_date` (not start_date/end_date).
  // Map the filter's end_date to target_date so KPIs reflect the selected range.
  const targetDate = filters?.end_date;

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
