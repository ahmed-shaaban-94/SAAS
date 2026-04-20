import useSWR from "swr";
import { fetchAPI, swrKey } from "@/lib/api-client";
import type { FilterParams } from "@/types/filters";
import type { ReorderAlert } from "@/types/inventory";

interface RawReorderAlert {
  product_key: number;
  drug_code: string;
  drug_name: string;
  site_code: string;
  site_name?: string;
  current_quantity: number;
  reorder_point: number;
  reorder_quantity?: number;
  suggested_reorder_qty?: number;
  /** #507 — trailing-30d velocity, status, days_of_stock shipped by backend. */
  daily_velocity?: number | string | null;
  days_of_stock?: number | string | null;
  status?: "critical" | "low" | "healthy";
}

function toRiskLevel(
  currentQuantity: number,
  reorderPoint: number,
): ReorderAlert["risk_level"] {
  if (currentQuantity <= 0) return "stockout";
  if (currentQuantity <= reorderPoint * 0.5) return "critical";
  return "at_risk";
}

function toNumberOrNull(value: number | string | null | undefined): number | null {
  if (value == null) return null;
  const n = typeof value === "string" ? Number(value) : value;
  return Number.isFinite(n) ? n : null;
}

export function useReorderAlerts(filters?: FilterParams) {
  const key = swrKey("/api/v1/inventory/alerts/reorder", filters);
  const { data, error, isLoading, mutate } = useSWR(key, async () => {
    const rows = await fetchAPI<RawReorderAlert[]>(
      "/api/v1/inventory/alerts/reorder",
      filters,
    );
    return rows.map<ReorderAlert>((row) => ({
      product_key: row.product_key,
      drug_code: row.drug_code,
      drug_name: row.drug_name,
      site_code: row.site_code,
      site_name: row.site_name ?? row.site_code,
      current_quantity: row.current_quantity,
      reorder_point: row.reorder_point,
      risk_level: toRiskLevel(row.current_quantity, row.reorder_point),
      suggested_reorder_qty:
        row.suggested_reorder_qty ?? row.reorder_quantity ?? 0,
      days_of_stock: toNumberOrNull(row.days_of_stock),
      velocity: toNumberOrNull(row.daily_velocity),
      status: row.status,
    }));
  });

  return { data, error, isLoading, mutate };
}
