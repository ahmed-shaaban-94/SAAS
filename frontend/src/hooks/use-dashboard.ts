import useSWR from "swr";
import { fetchAPI, swrKey } from "@/lib/api-client";
import type { ApiGet } from "@/lib/api-types";
import type { FilterParams } from "@/types/filters";

/**
 * Composite dashboard data — KPI + trends + rankings + filter options
 * in a single API call via GET /api/v1/analytics/dashboard.
 *
 * Shape is sourced from the OpenAPI schema (issue #658).
 */
export type DashboardData = ApiGet<"/api/v1/analytics/dashboard">;

const DASHBOARD_PATH = "/api/v1/analytics/dashboard";

export function useDashboard(filters?: FilterParams) {
  const key = swrKey(DASHBOARD_PATH, filters);

  const { data, error, isLoading, mutate } = useSWR(
    key,
    () => fetchAPI<DashboardData>(DASHBOARD_PATH, filters),
    { refreshInterval: 300000 },
  );

  return { data, error, isLoading, mutate };
}
