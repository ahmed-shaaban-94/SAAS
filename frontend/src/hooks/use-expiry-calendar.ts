import useSWR from "swr";
import { fetchAPI, swrKey } from "@/lib/api-client";
import type { FilterParams } from "@/types/filters";
import type { ExpiryCalendarDay } from "@/types/expiry";

interface RawExpiryCalendarDay {
  expiry_date: string;
  batch_count: number;
  total_quantity: number;
  alert_level: string;
}

export function useExpiryCalendar(filters?: FilterParams) {
  const key = swrKey("/api/v1/expiry/calendar", filters);
  const { data, error, isLoading, mutate } = useSWR(key, async () => {
    const rows = await fetchAPI<RawExpiryCalendarDay[]>("/api/v1/expiry/calendar", filters);
    return rows.map((row) => ({
      date: row.expiry_date,
      batch_count: row.batch_count,
      total_quantity: row.total_quantity,
      alert_level: row.alert_level,
    }));
  });

  return { data, error, isLoading, mutate };
}
