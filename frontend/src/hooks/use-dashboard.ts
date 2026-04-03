import useSWR from "swr";
import { fetchAPI } from "@/lib/api-client";
import type { FilterParams } from "@/types/filters";

/**
 * Composite dashboard data — KPI + trends + rankings + filter options
 * in a single API call via GET /api/v1/analytics/dashboard.
 */
export interface DashboardData {
  kpi: {
    today_net: number;
    mtd_net: number;
    ytd_net: number;
    mom_growth_pct: number | null;
    yoy_growth_pct: number | null;
    daily_transactions: number;
    daily_customers: number;
    avg_basket_size: number;
    daily_returns: number;
    mtd_transactions: number;
    ytd_transactions: number;
    sparkline?: Array<{ period: string; value: number }>;
  };
  daily_trend: {
    points: Array<{ period: string; value: number }>;
    total: number;
    average: number;
    minimum: number;
    maximum: number;
    growth_pct: number | null;
  };
  monthly_trend: {
    points: Array<{ period: string; value: number }>;
    total: number;
    average: number;
    minimum: number;
    maximum: number;
    growth_pct: number | null;
  };
  top_products: {
    items: Array<{
      rank: number;
      key: number;
      name: string;
      value: number;
      pct_of_total: number;
    }>;
    total: number;
  };
  top_customers: {
    items: Array<{
      rank: number;
      key: number;
      name: string;
      value: number;
      pct_of_total: number;
    }>;
    total: number;
  };
  top_staff: {
    items: Array<{
      rank: number;
      key: number;
      name: string;
      value: number;
      pct_of_total: number;
    }>;
    total: number;
  };
  filter_options: {
    categories: string[];
    brands: string[];
    sites: Array<{ key: number; label: string }>;
    staff: Array<{ key: number; label: string }>;
  };
}

export function useDashboard(filters?: FilterParams) {
  const qp = new URLSearchParams();
  if (filters?.start_date) qp.set("start_date", filters.start_date);
  if (filters?.end_date) qp.set("end_date", filters.end_date);
  const qs = qp.toString();
  const key = `/api/v1/analytics/dashboard${qs ? `?${qs}` : ""}`;

  const { data, error, isLoading, mutate } = useSWR(
    key,
    () => fetchAPI<DashboardData>(key),
    { refreshInterval: 60000, revalidateOnFocus: true },
  );

  return { data, error, isLoading, mutate };
}
