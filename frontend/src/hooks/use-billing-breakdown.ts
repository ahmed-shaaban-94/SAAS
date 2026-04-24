import useSWR from "swr";
import { fetchAPI, swrKey } from "@/lib/api-client";
import type { ApiGet } from "@/lib/api-types";
import type { FilterParams } from "@/types/filters";

type BillingBreakdownResponse = ApiGet<"/api/v1/analytics/billing-breakdown">;

export function useBillingBreakdown(filters?: FilterParams) {
  const key = swrKey("/api/v1/analytics/billing-breakdown", filters);
  const { data, error, isLoading } = useSWR(key, () =>
    fetchAPI<BillingBreakdownResponse>("/api/v1/analytics/billing-breakdown", filters),
  );
  return { data, error, isLoading };
}
