import useSWR from "swr";
import { fetchAPI, swrKey } from "@/lib/api-client";
import type { FilterParams } from "@/types/filters";
import type { StockMovement } from "@/types/inventory";

export function useStockMovements(filters?: FilterParams) {
  const key = swrKey("/api/v1/inventory/movements", filters);
  const { data, error, isLoading, mutate } = useSWR(key, () =>
    fetchAPI<StockMovement[]>("/api/v1/inventory/movements", filters),
  );

  return { data, error, isLoading, mutate };
}
