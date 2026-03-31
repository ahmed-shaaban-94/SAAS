import useSWR from "swr";
import { fetchAPI, swrKey } from "@/lib/api-client";
import type { CustomerTypeBreakdown } from "@/types/api";
import type { FilterParams } from "@/types/filters";

export function useCustomerTypeBreakdown(filters?: FilterParams) {
  const key = swrKey("/api/v1/analytics/customer-type-breakdown", filters);
  const { data, error, isLoading } = useSWR(key, () =>
    fetchAPI<CustomerTypeBreakdown>(
      "/api/v1/analytics/customer-type-breakdown",
      filters,
    ),
  );
  return { data, error, isLoading };
}
