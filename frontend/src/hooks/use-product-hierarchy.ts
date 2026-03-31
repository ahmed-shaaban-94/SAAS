import useSWR from "swr";
import { fetchAPI, swrKey } from "@/lib/api-client";
import type { ProductHierarchy } from "@/types/api";
import type { FilterParams } from "@/types/filters";

export function useProductHierarchy(filters?: FilterParams) {
  const key = swrKey("/api/v1/analytics/products/by-category", filters);
  const { data, error, isLoading } = useSWR(key, () =>
    fetchAPI<ProductHierarchy>(
      "/api/v1/analytics/products/by-category",
      filters,
    ),
  );
  return { data, error, isLoading };
}
