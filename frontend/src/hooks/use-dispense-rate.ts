"use client";
import useSWR from "swr";
import { fetchAPI, swrKey } from "@/lib/api-client";
import type { DispenseRate } from "@/types/dispensing";
import type { FilterParams } from "@/types/filters";

export function useDispenseRate(params?: FilterParams) {
  const { data, error, isLoading } = useSWR<DispenseRate[]>(
    swrKey("/api/v1/dispensing/rates", params),
    () => fetchAPI<DispenseRate[]>("/api/v1/dispensing/rates", params),
  );
  return { data: data ?? [], error, isLoading };
}
