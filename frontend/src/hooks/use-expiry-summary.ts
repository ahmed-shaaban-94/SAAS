import useSWR from "swr";
import { fetchAPI, swrKey } from "@/lib/api-client";
import type { ExpirySummary } from "@/types/expiry";
import type { FilterParams } from "@/types/filters";

interface RawExpirySummaryRow {
  site_code: string;
  site_name: string;
  expiry_bucket: string;
  batch_count: number;
  total_value: number;
}

function normalizeBucket(bucket: string): keyof Omit<ExpirySummary, "site_code" | "site_name" | "total_expired_value"> | null {
  const value = bucket.toLowerCase();
  if (value.includes("expired")) return "expired_count";
  if (value.includes("critical")) return "critical_count";
  if (value.includes("warning")) return "warning_count";
  if (value.includes("caution") || value.includes("near")) return "caution_count";
  return null;
}

export function useExpirySummary(filters?: FilterParams) {
  const key = swrKey("/api/v1/expiry/summary", filters);
  const { data, error, isLoading, mutate } = useSWR(key, async () => {
    const rows = await fetchAPI<RawExpirySummaryRow[]>("/api/v1/expiry/summary", filters);
    const grouped = new Map<string, ExpirySummary>();

    for (const row of rows) {
      const current = grouped.get(row.site_code) ?? {
        site_code: row.site_code,
        site_name: row.site_name,
        expired_count: 0,
        critical_count: 0,
        warning_count: 0,
        caution_count: 0,
        total_expired_value: 0,
      };

      const bucket = normalizeBucket(row.expiry_bucket);
      if (bucket) {
        current[bucket] += row.batch_count;
      }
      if (bucket === "expired_count") {
        current.total_expired_value += row.total_value;
      }

      grouped.set(row.site_code, current);
    }

    return Array.from(grouped.values());
  });

  return { data, error, isLoading, mutate };
}
