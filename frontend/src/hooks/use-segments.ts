"use client";
import useSWR from "swr";
import { fetchAPI } from "@/lib/api-client";
import type { SegmentSummary, CustomerSegment } from "@/types/api";

export function useSegmentSummary() {
  const { data, error, isLoading } = useSWR<SegmentSummary[]>(
    "/api/v1/analytics/segments/summary",
    () => fetchAPI<SegmentSummary[]>("/api/v1/analytics/segments/summary"),
  );
  return { data, error, isLoading };
}

export function useCustomerSegments(segment?: string, limit: number = 50) {
  const params: Record<string, string | number> = { limit };
  if (segment) params.segment = segment;
  const { data, error, isLoading } = useSWR<CustomerSegment[]>(
    ["/api/v1/forecasting/customers/segments", segment, limit],
    () => fetchAPI<CustomerSegment[]>("/api/v1/forecasting/customers/segments", params),
  );
  return { data, error, isLoading };
}
