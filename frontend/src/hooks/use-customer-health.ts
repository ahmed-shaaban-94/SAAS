import useSWR from "swr";
import { fetchAPI } from "@/lib/api-client";
import type { CustomerHealthScore, HealthDistribution } from "@/types/api";

export function useCustomerHealth(band?: string, limit = 50) {
  const params: Record<string, string> = { limit: String(limit) };
  if (band) params.band = band;
  const qs = new URLSearchParams(params).toString();
  const key = `/api/v1/analytics/customer-health?${qs}`;
  const { data, error, isLoading } = useSWR(key, () =>
    fetchAPI<CustomerHealthScore[]>(`/api/v1/analytics/customer-health?${qs}`),
  );
  return { data, error, isLoading };
}

export function useHealthDistribution() {
  const key = "/api/v1/analytics/customer-health/distribution";
  const { data, error, isLoading } = useSWR(key, () =>
    fetchAPI<HealthDistribution>(key),
  );
  return { data, error, isLoading };
}

export function useAtRiskCustomers(limit = 20) {
  const key = `/api/v1/analytics/customer-health/at-risk?limit=${limit}`;
  const { data, error, isLoading } = useSWR(key, () =>
    fetchAPI<CustomerHealthScore[]>(key),
  );
  return { data, error, isLoading };
}
