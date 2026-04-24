import useSWR from "swr";
import { fetchAPI, swrKey } from "@/lib/api-client";
import type { ReturnAnalysis } from "@/types/api";
import type { FilterParams } from "@/types/filters";

// Not migrated to ApiGet yet: the generated schema omits the optional
// `return_rate` field the returns-table test expects. Follow-up: update
// the Pydantic model to include it, then switch this hook to ApiGet.

export function useReturns(filters?: FilterParams) {
  const key = swrKey("/api/v1/analytics/returns", filters);

  const { data, error, isLoading } = useSWR(key, () =>
    fetchAPI<ReturnAnalysis[]>("/api/v1/analytics/returns", filters),
  );
  return { data, error, isLoading };
}
