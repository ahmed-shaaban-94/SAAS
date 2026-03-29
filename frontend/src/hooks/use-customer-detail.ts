import useSWR from "swr";
import { fetchAPI } from "@/lib/api-client";
import type { CustomerAnalytics } from "@/types/api";

export function useCustomerDetail(customerKey: number) {
  const { data, error, isLoading, mutate } = useSWR(
    `/api/v1/analytics/customers/${customerKey}`,
    () => fetchAPI<CustomerAnalytics>(`/api/v1/analytics/customers/${customerKey}`),
  );
  return { data, error, isLoading, mutate };
}
