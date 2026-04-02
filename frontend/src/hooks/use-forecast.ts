"use client";
import useSWR from "swr";
import { fetchAPI } from "@/lib/api-client";
import type { ForecastResult, ForecastSummary } from "@/types/api";

export function useForecastSummary() {
  const { data, error, isLoading } = useSWR<ForecastSummary>(
    "/api/v1/forecasting/summary",
    () => fetchAPI<ForecastSummary>("/api/v1/forecasting/summary"),
  );
  return { data, error, isLoading };
}

export function useRevenueForecast(granularity: "daily" | "monthly" = "daily") {
  const { data, error, isLoading } = useSWR<ForecastResult>(
    ["/api/v1/forecasting/revenue", granularity],
    () => fetchAPI<ForecastResult>("/api/v1/forecasting/revenue", { granularity }),
  );
  return { data, error, isLoading };
}
