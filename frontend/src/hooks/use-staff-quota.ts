"use client";

import useSWR from "swr";
import { fetchAPI, swrKey } from "@/lib/api-client";
import type { ApiGet } from "@/lib/api-types";

type StaffQuotaList = ApiGet<"/api/v1/analytics/staff/quota">;
export type StaffQuota = StaffQuotaList[number];

export function useStaffQuota(year?: number, month?: number) {
  const params: Record<string, string> = {};
  if (year) params.year = String(year);
  if (month) params.month = String(month);

  const { data, error, isLoading } = useSWR<StaffQuotaList>(
    swrKey("/api/v1/analytics/staff/quota", params),
    () => fetchAPI<StaffQuotaList>("/api/v1/analytics/staff/quota", params),
  );

  return { data: data ?? [], error, isLoading };
}
