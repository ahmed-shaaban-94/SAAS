import useSWR from "swr";
import { fetchAPI, swrKey } from "@/lib/api-client";
import type { TrendResult } from "@/types/api";
import type { FilterParams } from "@/types/filters";

/**
 * Hook that fetches current + previous period trend data for comparison.
 * Previous period = same duration, shifted back by that duration.
 */
export function useComparisonTrend(
  endpoint: string,
  filters?: FilterParams,
  compare: boolean = false,
) {
  // Current period
  const currentKey = swrKey(endpoint, filters);
  const current = useSWR(currentKey, () =>
    fetchAPI<TrendResult>(endpoint, filters),
  );

  // Compute previous period dates
  let prevFilters: FilterParams | undefined;
  if (compare && filters?.start_date && filters?.end_date) {
    const start = new Date(filters.start_date);
    const end = new Date(filters.end_date);
    const durationMs = end.getTime() - start.getTime();
    const prevEnd = new Date(start.getTime() - 86400000); // day before start
    const prevStart = new Date(prevEnd.getTime() - durationMs);
    prevFilters = {
      ...filters,
      start_date: prevStart.toISOString().split("T")[0],
      end_date: prevEnd.toISOString().split("T")[0],
    };
  }

  const prevKey = compare && prevFilters ? swrKey(endpoint, prevFilters) : null;
  const previous = useSWR(
    prevKey,
    prevKey
      ? () => fetchAPI<TrendResult>(endpoint, prevFilters)
      : null,
    {
      revalidateOnFocus: false,
      revalidateIfStale: false,
      dedupingInterval: 600_000,
    },
  );

  return {
    current: current.data ?? null,
    previous: compare ? (previous.data ?? null) : null,
    isLoading: current.isLoading || (compare && previous.isLoading),
    error: current.error || previous.error,
  };
}
