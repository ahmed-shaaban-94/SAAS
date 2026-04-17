import useSWR from "swr";
import { fetchAPI, swrKey } from "@/lib/api-client";
import type { FilterParams } from "@/types/filters";
import type { StockMovement } from "@/types/inventory";

export function useProductMovements(drugCode?: string, filters?: FilterParams) {
  const key = drugCode ? swrKey(`/api/v1/inventory/movements/${drugCode}`, filters) : null;
  const { data, error, isLoading, mutate } = useSWR(key, () =>
    fetchAPI<StockMovement[]>(`/api/v1/inventory/movements/${drugCode}`, filters),
  );

  return { data, error, isLoading, mutate };
}
