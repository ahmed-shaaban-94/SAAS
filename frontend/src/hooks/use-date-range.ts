import useSWR from "swr";
import { fetchAPI } from "@/lib/api-client";

interface DataDateRange {
  min_date: string; // "YYYY-MM-DD"
  max_date: string; // "YYYY-MM-DD"
}

export function useDateRange() {
  const { data, error, isLoading } = useSWR(
    "/api/v1/analytics/date-range",
    () => fetchAPI<DataDateRange>("/api/v1/analytics/date-range"),
  );
  return { data, error, isLoading };
}
