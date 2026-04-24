import useSWR from "swr";
import { fetchAPI } from "@/lib/api-client";
import type { ApiGet } from "@/lib/api-types";

type DataDateRange = ApiGet<"/api/v1/analytics/date-range">;

export function useDateRange() {
  const { data, error, isLoading } = useSWR(
    "/api/v1/analytics/date-range",
    () => fetchAPI<DataDateRange>("/api/v1/analytics/date-range"),
  );
  return { data, error, isLoading };
}
