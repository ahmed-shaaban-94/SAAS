import useSWR from "swr";
import { fetchAPI, swrKey } from "@/lib/api-client";
import type { ApiGet } from "@/lib/api-types";
import type { FilterParams } from "@/types/filters";

type SitesResponse = ApiGet<"/api/v1/analytics/sites">;

export function useSites(filters?: FilterParams) {
  const key = swrKey("/api/v1/analytics/sites", filters);

  const { data, error, isLoading, mutate } = useSWR(key, () =>
    fetchAPI<SitesResponse>("/api/v1/analytics/sites", filters),
  );
  return { data, error, isLoading, mutate };
}
