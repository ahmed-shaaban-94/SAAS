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

export interface QuarterlyTargetVsActual {
  quarter: number;
  quarter_label: string;
  target_value: number;
  actual_value: number;
  variance: number;
  achievement_pct: number;
}

export interface QuarterlySummary {
  quarters: QuarterlyTargetVsActual[];
  ytd_target: number;
  ytd_actual: number;
  ytd_achievement_pct: number;
}

export function useQuarterlySummary(year: number = new Date().getFullYear()) {
  const { data, error, isLoading } = useSWR<QuarterlySummary>(
    ["/api/v1/targets/summary/quarterly", year],
    () => fetchAPI<QuarterlySummary>("/api/v1/targets/summary/quarterly", { year }),
  );
  return { data, error, isLoading };
}
