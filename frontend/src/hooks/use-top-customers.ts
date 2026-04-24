import useSWR from "swr";
import { fetchAPI, swrKey } from "@/lib/api-client";
import type { ApiGet } from "@/lib/api-types";
import type { FilterParams } from "@/types/filters";

type TopCustomersResponse = ApiGet<"/api/v1/analytics/customers/top">;

export function useTopCustomers(filters?: FilterParams) {
  const key = swrKey("/api/v1/analytics/customers/top", filters);

  const { data, error, isLoading } = useSWR(key, () =>
    fetchAPI<TopCustomersResponse>("/api/v1/analytics/customers/top", filters),
  );
  return { data, error, isLoading };
}
