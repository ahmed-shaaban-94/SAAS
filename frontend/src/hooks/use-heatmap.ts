"use client";
import useSWR from "swr";
import { fetchAPI, swrKey } from "@/lib/api-client";
import type { ApiGet } from "@/lib/api-types";

type HeatmapResponse = ApiGet<"/api/v1/analytics/heatmap">;

export function useHeatmap(year: number = new Date().getFullYear()) {
  const { data, error, isLoading, mutate } = useSWR<HeatmapResponse>(
    swrKey("/api/v1/analytics/heatmap", { year }),
    () => fetchAPI<HeatmapResponse>("/api/v1/analytics/heatmap", { year }),
  );
  return { data, error, isLoading, mutate };
}
