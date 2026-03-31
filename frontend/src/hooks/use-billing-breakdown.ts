import useSWR from "swr";
import { fetchAPI, swrKey } from "@/lib/api-client";
import type { BillingBreakdown } from "@/types/api";
import type { FilterParams } from "@/types/filters";

export function useBillingBreakdown(filters?: FilterParams) {
  const key = swrKey("/api/v1/analytics/billing-breakdown", filters);
  const { data, error, isLoading } = useSWR(key, () =>
    fetchAPI<BillingBreakdown>("/api/v1/analytics/billing-breakdown", filters),
  );
  return { data, error, isLoading };
}
