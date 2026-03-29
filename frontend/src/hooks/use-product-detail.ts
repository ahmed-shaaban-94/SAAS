import useSWR from "swr";
import { fetchAPI } from "@/lib/api-client";
import type { ProductPerformance } from "@/types/api";

export function useProductDetail(productKey: number) {
  const { data, error, isLoading, mutate } = useSWR(
    `/api/v1/analytics/products/${productKey}`,
    () => fetchAPI<ProductPerformance>(`/api/v1/analytics/products/${productKey}`),
  );
  return { data, error, isLoading, mutate };
}
