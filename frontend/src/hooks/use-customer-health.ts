import useSWR from "swr";
import { fetchAPI } from "@/lib/api-client";
import type { ApiGet } from "@/lib/api-types";

type CustomerHealthList = ApiGet<"/api/v1/analytics/customer-health">;
type HealthDistributionResponse = ApiGet<"/api/v1/analytics/customer-health/distribution">;
type AtRiskList = ApiGet<"/api/v1/analytics/customer-health/at-risk">;

export function useCustomerHealth(band?: string, limit = 50) {
  const params: Record<string, string> = { limit: String(limit) };
  if (band) params.band = band;
  const qs = new URLSearchParams(params).toString();
  const key = `/api/v1/analytics/customer-health?${qs}`;
  const { data, error, isLoading } = useSWR(key, () =>
    fetchAPI<CustomerHealthList>(`/api/v1/analytics/customer-health?${qs}`),
  );
  return { data, error, isLoading };
}

export function useHealthDistribution() {
  const key = "/api/v1/analytics/customer-health/distribution";
  const { data, error, isLoading } = useSWR(key, () =>
    fetchAPI<HealthDistributionResponse>(key),
  );
  return { data, error, isLoading };
}

export function useAtRiskCustomers(limit = 20) {
  const key = `/api/v1/analytics/customer-health/at-risk?limit=${limit}`;
  const { data, error, isLoading } = useSWR(key, () =>
    fetchAPI<AtRiskList>(key),
  );
  return { data, error, isLoading };
}
