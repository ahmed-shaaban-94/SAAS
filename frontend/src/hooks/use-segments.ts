"use client";
import useSWR from "swr";
import { fetchAPI } from "@/lib/api-client";
import type { ApiGet } from "@/lib/api-types";
import type { CustomerSegment } from "@/types/api";

type SegmentSummaryList = ApiGet<"/api/v1/analytics/segments/summary">;

export function useSegmentSummary() {
  const { data, error, isLoading } = useSWR<SegmentSummaryList>(
    "/api/v1/analytics/segments/summary",
    () => fetchAPI<SegmentSummaryList>("/api/v1/analytics/segments/summary"),
  );
  return { data, error, isLoading };
}

export function useCustomerSegments(segment?: string, limit: number = 50) {
  const params: Record<string, string | number> = { limit };
  if (segment) params.segment = segment;
  // /forecasting endpoint — out of scope for the analytics-domain migration;
  // will move to ApiGet in the forecasting-domain PR.
  const { data, error, isLoading } = useSWR<CustomerSegment[]>(
    ["/api/v1/forecasting/customers/segments", segment, limit],
    () => fetchAPI<CustomerSegment[]>("/api/v1/forecasting/customers/segments", params),
  );
  return { data, error, isLoading };
}
