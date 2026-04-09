import useSWR from "swr";
import { fetchAPI, swrKey } from "@/lib/api-client";
import type { FilterParams } from "@/types/filters";
import type { KPISummary, TrendResult, RankingResult, FilterOptions } from "@/types/api";

/**
 * Composite dashboard data — KPI + trends + rankings + filter options
 * in a single API call via GET /api/v1/analytics/dashboard.
 *
 * Reuses shared types from types/api.ts for consistency.
 */
export interface DashboardData {
  kpi: KPISummary;
  daily_trend: TrendResult;
  monthly_trend: TrendResult;
  top_products: RankingResult;
  top_customers: RankingResult;
  top_staff: RankingResult;
  filter_options: FilterOptions;
}

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
