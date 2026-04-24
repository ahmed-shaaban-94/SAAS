import useSWR from "swr";
import { fetchAPI, swrKey } from "@/lib/api-client";
import type { FilterParams } from "@/types/filters";

// Not migrated to ApiGet yet: the backend route declares the response as a
// plain `list[dict]` (no Pydantic response_model), so the generated schema
// resolves to `{ [key: string]: unknown }[]`. Follow-up: type the Python
// side, then flip this hook to ApiGet.
interface OriginBreakdownItem {
  origin: string;
  value: number;
  product_count: number;
  pct: number;
}

export function useOriginBreakdown(filters?: FilterParams) {
  const key = swrKey("/api/v1/analytics/origin-breakdown", filters);
  const { data, error, isLoading } = useSWR(key, () =>
    fetchAPI<OriginBreakdownItem[]>(
      "/api/v1/analytics/origin-breakdown",
      filters,
    ),
  );
  return { data, error, isLoading };
}
