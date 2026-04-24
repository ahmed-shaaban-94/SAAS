"use client";
import useSWR from "swr";
import { fetchAPI, swrKey } from "@/lib/api-client";
import { useFilters } from "@/contexts/filter-context";
import type { ApiGet } from "@/lib/api-types";

type ABCAnalysisResponse = ApiGet<"/api/v1/analytics/abc-analysis">;

export function useABCAnalysis(entity: "product" | "customer" = "product") {
  const { filters: filterParams } = useFilters();
  const params = { ...filterParams, entity };
  const { data, error, isLoading } = useSWR<ABCAnalysisResponse>(
    swrKey("/api/v1/analytics/abc-analysis", params),
    () => fetchAPI<ABCAnalysisResponse>("/api/v1/analytics/abc-analysis", params),
  );
  return { data, error, isLoading };
}
