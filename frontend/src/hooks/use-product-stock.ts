import useSWR from "swr";
import { fetchAPI, swrKey } from "@/lib/api-client";
import type { FilterParams } from "@/types/filters";
import type { StockLevel } from "@/types/inventory";

export function useProductStock(drugCode?: string, filters?: FilterParams) {
  const key = drugCode ? swrKey(`/api/v1/inventory/stock-levels/${drugCode}`, filters) : null;
  const { data, error, isLoading, mutate } = useSWR(key, () =>
    fetchAPI<StockLevel[]>(`/api/v1/inventory/stock-levels/${drugCode}`, filters),
  );

  return { data, error, isLoading, mutate };
}
