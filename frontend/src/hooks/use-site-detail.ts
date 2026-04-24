import useSWR from "swr";
import { fetchAPI } from "@/lib/api-client";
import type { ApiGet } from "@/lib/api-types";

type SiteDetailResponse = ApiGet<"/api/v1/analytics/sites/{site_key}">;

export function useSiteDetail(siteKey: number | null) {
  const key = siteKey ? `/api/v1/analytics/sites/${siteKey}` : null;
  const { data, error, isLoading } = useSWR(key, () =>
    fetchAPI<SiteDetailResponse>(`/api/v1/analytics/sites/${siteKey}`),
  );
  return { data, error, isLoading };
}
