import useSWR from "swr";
import { fetchAPI, swrKey } from "@/lib/api-client";
import type { FilterParams } from "@/types/filters";
import type { StockValuation } from "@/types/inventory";

export function useStockValuation(filters?: FilterParams) {
  const key = swrKey("/api/v1/inventory/valuation", filters);
  const { data, error, isLoading, mutate } = useSWR(key, () =>
    fetchAPI<StockValuation[]>("/api/v1/inventory/valuation", filters),
  );

  return { data, error, isLoading, mutate };
}
