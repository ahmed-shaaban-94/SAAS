"use client";
import useSWR from "swr";
import { fetchAPI, swrKey } from "@/lib/api-client";
import type { DaysOfStock } from "@/types/dispensing";
import type { FilterParams } from "@/types/filters";

export function useDaysOfStock(params?: FilterParams) {
  const { data, error, isLoading } = useSWR<DaysOfStock[]>(
    swrKey("/api/v1/dispensing/days-of-stock", params),
    () => fetchAPI<DaysOfStock[]>("/api/v1/dispensing/days-of-stock", params),
  );
  return { data: data ?? [], error, isLoading };
}
