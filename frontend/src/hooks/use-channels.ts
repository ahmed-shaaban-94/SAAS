import useSWR from "swr";
import { fetchAPI, swrKey } from "@/lib/api-client";
import type { ChannelsBreakdown } from "@/types/api";
import type { FilterParams } from "@/types/filters";

/**
 * Sales-channel distribution for the dashboard donut (#505).
 *
 * Backend returns a fixed four-segment response (retail / wholesale /
 * institution / online). Segments without a data source are tagged
 * ``source === "unavailable"`` and ``data_coverage === "partial"``.
 */
export function useChannels(filters?: FilterParams) {
  const key = swrKey("/api/v1/analytics/channels", filters);

  const { data, error, isLoading } = useSWR(key, () =>
    fetchAPI<ChannelsBreakdown>("/api/v1/analytics/channels", filters),
  );
  return { data, error, isLoading };
}
