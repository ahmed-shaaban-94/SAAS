import useSWR from "swr";
import { fetchAPI } from "@/lib/api-client";
import type { ApiGet } from "@/lib/api-types";

type ProductDetailResponse = ApiGet<"/api/v1/analytics/products/{product_key}">;

export function useProductDetail(productKey: number) {
  const { data, error, isLoading, mutate } = useSWR(
    `/api/v1/analytics/products/${productKey}`,
    () => fetchAPI<ProductDetailResponse>(`/api/v1/analytics/products/${productKey}`),
  );
  return { data, error, isLoading, mutate };
}
