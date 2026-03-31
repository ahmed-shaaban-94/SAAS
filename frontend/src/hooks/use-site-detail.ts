import useSWR from "swr";
import { fetchAPI } from "@/lib/api-client";
import type { SiteDetail } from "@/types/api";

export function useSiteDetail(siteKey: number | null) {
  const key = siteKey ? `/api/v1/analytics/sites/${siteKey}` : null;
  const { data, error, isLoading } = useSWR(key, () =>
    fetchAPI<SiteDetail>(`/api/v1/analytics/sites/${siteKey}`),
  );
  return { data, error, isLoading };
}
