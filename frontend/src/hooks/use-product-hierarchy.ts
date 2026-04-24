import useSWR from "swr";
import { fetchAPI, swrKey } from "@/lib/api-client";
import type { ApiGet } from "@/lib/api-types";
import type { FilterParams } from "@/types/filters";

type ProductHierarchyResponse = ApiGet<"/api/v1/analytics/products/by-category">;

export function useProductHierarchy(filters?: FilterParams) {
  const key = swrKey("/api/v1/analytics/products/by-category", filters);
  const { data, error, isLoading } = useSWR(key, () =>
    fetchAPI<ProductHierarchyResponse>(
      "/api/v1/analytics/products/by-category",
      filters,
    ),
  );
  return { data, error, isLoading };
}
