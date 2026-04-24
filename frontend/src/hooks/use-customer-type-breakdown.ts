import useSWR from "swr";
import { fetchAPI, swrKey } from "@/lib/api-client";
import type { ApiGet } from "@/lib/api-types";
import type { FilterParams } from "@/types/filters";

type CustomerTypeBreakdownResponse = ApiGet<"/api/v1/analytics/customer-type-breakdown">;

export function useCustomerTypeBreakdown(filters?: FilterParams) {
  const key = swrKey("/api/v1/analytics/customer-type-breakdown", filters);
  const { data, error, isLoading } = useSWR(key, () =>
    fetchAPI<CustomerTypeBreakdownResponse>(
      "/api/v1/analytics/customer-type-breakdown",
      filters,
    ),
  );
  return { data, error, isLoading };
}
