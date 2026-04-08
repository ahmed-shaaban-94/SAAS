"use client";

import useSWR from "swr";
import { fetchAPI, swrKey } from "@/lib/api-client";

export interface StaffQuota {
  staff_key: number;
  staff_name: string;
  staff_position: string | null;
  year: number;
  month: number;
  actual_revenue: number;
  actual_transactions: number | null;
  target_revenue: number | null;
  target_transactions: number | null;
  revenue_achievement_pct: number | null;
  transactions_achievement_pct: number | null;
  revenue_variance: number | null;
}

export function useStaffQuota(year?: number, month?: number) {
  const params: Record<string, string> = {};
  if (year) params.year = String(year);
  if (month) params.month = String(month);

  const { data, error, isLoading } = useSWR<StaffQuota[]>(
    swrKey("/api/v1/analytics/staff/quota", params),
    () => fetchAPI<StaffQuota[]>("/api/v1/analytics/staff/quota", params),
  );

  return { data: data ?? [], error, isLoading };
}
