"use client";

import useSWR from "swr";
import { fetchAPI } from "@/lib/api-client";

export interface ActiveShift {
  shift_id: number;
  terminal_id: number;
  staff_id: string;
  shift_date: string;
  opened_at: string;
  opening_cash: number;
  commission_earned_egp: number;
  daily_sales_target_egp: number | null;
  transactions_so_far: number;
  sales_so_far_egp: number;
}

export function useActiveShift(terminalId: number | null | undefined) {
  const { data, error, mutate } = useSWR<ActiveShift>(
    terminalId ? `/api/v1/pos/shifts/current` : null,
    (url: string) => fetchAPI<ActiveShift>(url),
    { refreshInterval: 10_000 },
  );

  return {
    shift: data ?? null,
    isLoading: !data && !error,
    error: error as Error | null,
    refresh: mutate,
  };
}
