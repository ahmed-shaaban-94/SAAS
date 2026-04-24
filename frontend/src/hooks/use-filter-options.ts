import useSWR from "swr";
import { fetchAPI } from "@/lib/api-client";
import type { ApiGet } from "@/lib/api-types";

type FilterOptionsResponse = ApiGet<"/api/v1/analytics/filters/options">;

export function useFilterOptions() {
  const { data, error, isLoading } = useSWR("/api/v1/analytics/filters/options", () =>
    fetchAPI<FilterOptionsResponse>("/api/v1/analytics/filters/options"),
  );
  return { data, error, isLoading };
}
