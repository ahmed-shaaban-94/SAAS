"use client";
import useSWR from "swr";
import { fetchAPI, swrKey } from "@/lib/api-client";
import { useFilters } from "@/contexts/filter-context";
import type { ReturnsTrend } from "@/types/api";

export function useReturnsTrend() {
  const { filterParams } = useFilters();
  const { data, error, isLoading } = useSWR<ReturnsTrend>(
    swrKey("/api/v1/analytics/returns/trend", filterParams),
    () => fetchAPI<ReturnsTrend>("/api/v1/analytics/returns/trend", filterParams),
  );
  return { data, error, isLoading };
}
