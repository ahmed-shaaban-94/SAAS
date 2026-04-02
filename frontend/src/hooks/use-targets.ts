"use client";
import useSWR from "swr";
import { fetchAPI } from "@/lib/api-client";
import type { TargetSummary } from "@/types/api";

export function useTargetSummary(year: number = new Date().getFullYear()) {
  const { data, error, isLoading, mutate } = useSWR<TargetSummary>(
    ["/api/v1/targets/summary", year],
    () => fetchAPI<TargetSummary>("/api/v1/targets/summary", { year }),
  );
  return { data, error, isLoading, mutate };
}
