import useSWR from "swr";
import { fetchAPI } from "@/lib/api-client";
import type { WaterfallAnalysis } from "@/types/api";
import type { FilterParams } from "@/types/filters";

function swrKey(path: string, filters?: FilterParams): string | null {
  if (!filters) return path;
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([k, v]) => {
    if (v !== undefined && v !== null) params.set(k, String(v));
  });
  const qs = params.toString();
  return qs ? `${path}?${qs}` : path;
}

export function useWhyChanged(filters?: FilterParams) {
  const key = swrKey("/api/v1/analytics/why-changed", filters);
  const { data, error, isLoading } = useSWR(key, () =>
    fetchAPI<WaterfallAnalysis>("/api/v1/analytics/why-changed", filters),
  );
  return { data, error, isLoading };
}
