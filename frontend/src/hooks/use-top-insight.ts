import useSWR from "swr";
import { fetchAPIOrNull } from "@/lib/api-client";
import type { TopInsight } from "@/types/api";

/**
 * Single actionable insight for the dashboard alert banner (#510).
 *
 * The backend returns **204 No Content** when nothing currently demands
 * attention — this hook surfaces that as ``data === null`` so the
 * banner hides silently rather than showing a stale insight.
 */
export function useTopInsight() {
  const { data, error, isLoading } = useSWR<TopInsight | null>(
    "/api/v1/ai-light/top-insight",
    () => fetchAPIOrNull<TopInsight>("/api/v1/ai-light/top-insight"),
  );
  return { data, error, isLoading };
}
