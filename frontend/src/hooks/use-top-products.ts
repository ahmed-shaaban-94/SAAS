import useSWR from "swr";
import { fetchAPI, swrKey } from "@/lib/api-client";
import type { ApiGet } from "@/lib/api-types";
import type { FilterParams } from "@/types/filters";

// Response shape sourced from the OpenAPI schema (issue #658 pilot).
type TopProductsResponse = ApiGet<"/api/v1/analytics/products/top">;

export function useTopProducts(filters?: FilterParams) {
  const key = swrKey("/api/v1/analytics/products/top", filters);

  const { data, error, isLoading } = useSWR(key, () =>
    fetchAPI<TopProductsResponse>("/api/v1/analytics/products/top", filters),
  );
  return { data, error, isLoading };
}
