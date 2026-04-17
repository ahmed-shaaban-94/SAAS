import useSWR from "swr";
import { fetchAPI, swrKey } from "@/lib/api-client";
import type { FilterParams } from "@/types/filters";
import type { StockLevel } from "@/types/inventory";

export function useStockLevels(filters?: FilterParams) {
  const key = swrKey("/api/v1/inventory/stock-levels", filters);
  const { data, error, isLoading, mutate } = useSWR(key, () =>
    fetchAPI<StockLevel[]>("/api/v1/inventory/stock-levels", filters),
  );

  return { data, error, isLoading, mutate };
}
