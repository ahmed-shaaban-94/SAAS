"use client";
import useSWR from "swr";
import { fetchAPI } from "@/lib/api-client";
import type { BudgetSummary } from "@/types/api";

export function useBudgetSummary(year: number = 2025) {
  const { data, error, isLoading, mutate } = useSWR<BudgetSummary>(
    ["/api/v1/targets/budget", year],
    () => fetchAPI<BudgetSummary>("/api/v1/targets/budget", { year }),
  );
  return { data, error, isLoading, mutate };
}
