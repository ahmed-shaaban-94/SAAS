"use client";
import useSWR from "swr";
import { fetchAPI, swrKey } from "@/lib/api-client";
import { useFilters } from "@/contexts/filter-context";
import type { ApiGet } from "@/lib/api-types";

type ReturnsTrendResponse = ApiGet<"/api/v1/analytics/returns/trend">;

export function useReturnsTrend() {
  const { filters: filterParams } = useFilters();
  const { data, error, isLoading } = useSWR<ReturnsTrendResponse>(
    swrKey("/api/v1/analytics/returns/trend", filterParams),
    () => fetchAPI<ReturnsTrendResponse>("/api/v1/analytics/returns/trend", filterParams),
  );
  return { data, error, isLoading };
}
