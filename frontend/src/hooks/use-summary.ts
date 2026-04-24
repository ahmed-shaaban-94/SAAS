import useSWR from "swr";
import { fetchAPI, swrKey } from "@/lib/api-client";
import type { ApiGet } from "@/lib/api-types";
import type { FilterParams } from "@/types/filters";

// Response shape sourced from the OpenAPI schema (issue #658 pilot).
type SummaryResponse = ApiGet<"/api/v1/analytics/summary">;

export function useSummary(filters?: FilterParams) {
  // The /summary endpoint accepts `target_date` (not start_date/end_date).
  // Map the filter's end_date to target_date so KPIs reflect the selected range.
  const targetDate = filters?.end_date;
  const params: FilterParams | undefined = targetDate
    ? { target_date: targetDate }
    : undefined;

  const key = swrKey("/api/v1/analytics/summary", params);

  const { data, error, isLoading } = useSWR(key, () =>
    fetchAPI<SummaryResponse>("/api/v1/analytics/summary", params),
  );
  return { data, error, isLoading };
}
