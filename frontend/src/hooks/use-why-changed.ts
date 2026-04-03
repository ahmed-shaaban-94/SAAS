import useSWR from "swr";
import { fetchAPI } from "@/lib/api-client";
import { swrKey } from "@/lib/swr-config";
import type { WaterfallAnalysis } from "@/types/api";
import type { FilterParams } from "@/types/filters";

export function useWhyChanged(filters?: FilterParams) {
  const key = swrKey("/api/v1/analytics/why-changed", filters);
  const { data, error, isLoading } = useSWR(key, () =>
    fetchAPI<WaterfallAnalysis>("/api/v1/analytics/why-changed", filters),
  );
  return { data, error, isLoading };
}
