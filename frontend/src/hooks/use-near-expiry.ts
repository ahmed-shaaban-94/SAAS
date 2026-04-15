import useSWR from "swr";
import { fetchAPI, swrKey } from "@/lib/api-client";
import type { ExpiryAlert } from "@/types/expiry";
import type { FilterParams } from "@/types/filters";

export function useNearExpiry(filters?: FilterParams) {
  const key = swrKey("/api/v1/expiry/alerts", filters);
  const { data, error, isLoading, mutate } = useSWR(key, () =>
    fetchAPI<ExpiryAlert[]>("/api/v1/expiry/alerts", filters),
  );

  return { data, error, isLoading, mutate };
}
