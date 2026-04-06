import useSWR from "swr";
import { fetchAPI } from "@/lib/api-client";
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

export function useDashboard(filters?: FilterParams) {
  const qp = new URLSearchParams();
  if (filters?.start_date) qp.set("start_date", filters.start_date);
  if (filters?.end_date) qp.set("end_date", filters.end_date);
  if (filters?.category) qp.set("category", filters.category);
  if (filters?.brand) qp.set("brand", filters.brand);
  if (filters?.site_key) qp.set("site_key", String(filters.site_key));
  if (filters?.staff_key) qp.set("staff_key", String(filters.staff_key));
  const qs = qp.toString();
  const key = `/api/v1/analytics/dashboard${qs ? `?${qs}` : ""}`;

  const { data, error, isLoading, mutate } = useSWR(
    key,
    () => fetchAPI<DashboardData>(key),
    { refreshInterval: 300000 },
  );

  return { data, error, isLoading, mutate };
}
