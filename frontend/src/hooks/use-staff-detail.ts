import useSWR from "swr";
import { fetchAPI } from "@/lib/api-client";
import type { ApiGet } from "@/lib/api-types";

type StaffDetailResponse = ApiGet<"/api/v1/analytics/staff/{staff_key}">;

export function useStaffDetail(staffKey: number) {
  const { data, error, isLoading, mutate } = useSWR(
    `/api/v1/analytics/staff/${staffKey}`,
    () => fetchAPI<StaffDetailResponse>(`/api/v1/analytics/staff/${staffKey}`),
  );
  return { data, error, isLoading, mutate };
}
