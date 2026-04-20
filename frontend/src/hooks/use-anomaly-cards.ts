import useSWR from "swr";
import { fetchAPI, swrKey } from "@/lib/api-client";
import type { AnomalyCard } from "@/types/api";

/**
 * Display-ready active anomalies for the dashboard feed widget (#508).
 *
 * The backend mapper produces ``kind`` / ``confidence`` / ``title`` /
 * ``body`` / ``time_ago`` directly so the frontend renders cards with
 * no extra transformation.
 */
export function useAnomalyCards(limit: number = 10) {
  const params = { limit };
  const key = swrKey("/api/v1/anomalies/cards", params);

  const { data, error, isLoading } = useSWR(key, () =>
    fetchAPI<AnomalyCard[]>("/api/v1/anomalies/cards", params),
  );
  return { data, error, isLoading };
}
