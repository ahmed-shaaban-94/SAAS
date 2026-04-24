import useSWR from "swr";
import { fetchAPI, swrKey } from "@/lib/api-client";
import type { ApiGet } from "@/lib/api-types";

export type RevenueForecastPeriod =
  | "day"
  | "week"
  | "month"
  | "quarter"
  | "ytd";

type RevenueForecastResponse = ApiGet<"/api/v1/analytics/revenue-forecast">;

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
    fetchAPI<RevenueForecastResponse>("/api/v1/analytics/revenue-forecast", params),
  );
  return { data, error, isLoading };
}
