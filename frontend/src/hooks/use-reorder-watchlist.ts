import useSWR from "swr";
import { fetchAPI, swrKey } from "@/lib/api-client";
import type { FilterParams } from "@/types/filters";
import type { ReorderWatchlistItem } from "@/types/api";

/**
 * Reorder watchlist for the new dashboard inventory widget (#502 / #507).
 *
 * Consumes the enriched backend shape directly (daily_velocity,
 * days_of_stock, status) — no adapter mapping. The legacy
 * ``useReorderAlerts`` hook remains for pages that still expect the
 * pre-#507 ``risk_level`` shape.
 */
export function useReorderWatchlist(filters?: FilterParams) {
  const key = swrKey("/api/v1/inventory/alerts/reorder", filters);

  const { data, error, isLoading } = useSWR(key, () =>
    fetchAPI<ReorderWatchlistItem[]>(
      "/api/v1/inventory/alerts/reorder",
      filters,
    ),
  );
  return { data, error, isLoading };
}
