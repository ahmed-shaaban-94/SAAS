import useSWR from "swr";
import { fetchAPI, swrKey } from "@/lib/api-client";
import type { ApiGet } from "@/lib/api-types";
import type { FilterParams } from "@/types/filters";

type TopMoversResponse = ApiGet<"/api/v1/analytics/top-movers">;

export function useTopMovers(
  entityType: "product" | "customer" | "staff" = "product",
  filters?: FilterParams,
) {
  const params: FilterParams = {
    ...filters,
    entity_type: entityType,
  };
  const key = swrKey("/api/v1/analytics/top-movers", params);
  const { data, error, isLoading } = useSWR(key, () =>
    fetchAPI<TopMoversResponse>("/api/v1/analytics/top-movers", params),
  );
  return { data, error, isLoading };
}
