import useSWR from "swr";
import { fetchAPI, swrKey } from "@/lib/api-client";
import type { ReturnAnalysis } from "@/types/api";
import type { FilterParams } from "@/types/filters";

export function useReturns(filters?: FilterParams) {
  const key = swrKey("/api/v1/analytics/returns", filters);

  const { data, error, isLoading } = useSWR(key, () =>
    fetchAPI<ReturnAnalysis[]>("/api/v1/analytics/returns", filters),
  );
  return { data, error, isLoading };
}
