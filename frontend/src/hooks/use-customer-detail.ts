import useSWR from "swr";
import { fetchAPI } from "@/lib/api-client";
import type { ApiGet } from "@/lib/api-types";

type CustomerDetailResponse = ApiGet<"/api/v1/analytics/customers/{customer_key}">;

export function useCustomerDetail(customerKey: number) {
  const { data, error, isLoading, mutate } = useSWR(
    `/api/v1/analytics/customers/${customerKey}`,
    () => fetchAPI<CustomerDetailResponse>(`/api/v1/analytics/customers/${customerKey}`),
  );
  return { data, error, isLoading, mutate };
}
