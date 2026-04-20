import useSWR from "swr";
import { fetchAPI, swrKey } from "@/lib/api-client";
import type { ExpiryExposureTier } from "@/types/api";

/**
 * Tenant-aggregate expiry exposure per 30/60/90-day tier (#506).
 *
 * Always returns exactly three rows in fixed order so the donut has a
 * stable layout — zero-valued tiers are kept in the list by the backend.
 */
export function useExpiryExposure(siteCode?: string) {
  const params = siteCode ? { site_code: siteCode } : undefined;
  const key = swrKey("/api/v1/expiry/exposure-summary", params);

  const { data, error, isLoading } = useSWR(key, () =>
    fetchAPI<ExpiryExposureTier[]>("/api/v1/expiry/exposure-summary", params),
  );
  return { data, error, isLoading };
}
