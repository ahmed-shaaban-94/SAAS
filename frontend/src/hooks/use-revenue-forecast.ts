import useSWR from "swr";
import { fetchAPI, swrKey } from "@/lib/api-client";
import type { RevenueForecast } from "@/types/api";

export type RevenueForecastPeriod =
  | "day"
  | "week"
  | "month"
  | "quarter"
  | "ytd";

/**
 * Composite actual + forecast + target + stats for the dashboard
 * revenue chart (#504).
 *
 * Replaces three separate hooks (``/trends/daily``, ``/forecasting``,
 * ``/targets``) — eliminates loading-state flicker from parallel fetches.
 */
export function useRevenueForecast(period: RevenueForecastPeriod = "month") {
  const params = { period };
  const key = swrKey("/api/v1/analytics/revenue-forecast", params);

  const { data, error, isLoading } = useSWR(key, () =>
    fetchAPI<RevenueForecast>("/api/v1/analytics/revenue-forecast", params),
  );
  return { data, error, isLoading };
}
