"use client";
import useSWR from "swr";
import { fetchAPI, swrKey } from "@/lib/api-client";
import { useFilters } from "@/contexts/filter-context";
import type { ABCAnalysis } from "@/types/api";

export function useABCAnalysis(entity: "product" | "customer" = "product") {
  const { filters: filterParams } = useFilters();
  const params = { ...filterParams, entity };
  const { data, error, isLoading } = useSWR<ABCAnalysis>(
    swrKey("/api/v1/analytics/abc-analysis", params),
    () => fetchAPI<ABCAnalysis>("/api/v1/analytics/abc-analysis", params),
  );
  return { data, error, isLoading };
}
