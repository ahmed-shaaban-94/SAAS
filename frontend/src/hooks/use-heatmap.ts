"use client";
import useSWR from "swr";
import { fetchAPI, swrKey } from "@/lib/api-client";
import type { HeatmapData } from "@/types/api";

export function useHeatmap(year: number = new Date().getFullYear()) {
  const { data, error, isLoading, mutate } = useSWR<HeatmapData>(
    swrKey("/api/v1/analytics/heatmap", { year }),
    () => fetchAPI<HeatmapData>("/api/v1/analytics/heatmap", { year }),
  );
  return { data, error, isLoading, mutate };
}
