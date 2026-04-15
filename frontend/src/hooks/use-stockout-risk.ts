"use client";
import useSWR from "swr";
import { fetchAPI } from "@/lib/api-client";
import type { StockoutRisk } from "@/types/dispensing";

export function useStockoutRisk() {
  const { data, error, isLoading } = useSWR<StockoutRisk[]>(
    "/api/v1/dispensing/stockout-risk",
    () => fetchAPI<StockoutRisk[]>("/api/v1/dispensing/stockout-risk"),
  );
  return { data: data ?? [], error, isLoading };
}
