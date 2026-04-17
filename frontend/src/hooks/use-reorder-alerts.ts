import useSWR from "swr";
import { fetchAPI, swrKey } from "@/lib/api-client";
import type { FilterParams } from "@/types/filters";
import type { ReorderAlert } from "@/types/inventory";

interface RawReorderAlert {
  product_key: number;
  drug_code: string;
  drug_name: string;
  site_code: string;
  current_quantity: number;
  reorder_point: number;
  reorder_quantity: number;
}

function toRiskLevel(currentQuantity: number, reorderPoint: number): ReorderAlert["risk_level"] {
  if (currentQuantity <= 0) return "stockout";
  if (currentQuantity <= reorderPoint * 0.5) return "critical";
  return "at_risk";
}

export function useReorderAlerts(filters?: FilterParams) {
  const key = swrKey("/api/v1/inventory/alerts/reorder", filters);
  const { data, error, isLoading, mutate } = useSWR(key, async () => {
    const rows = await fetchAPI<RawReorderAlert[]>("/api/v1/inventory/alerts/reorder", filters);
    return rows.map((row) => ({
      product_key: row.product_key,
      drug_code: row.drug_code,
      drug_name: row.drug_name,
      site_code: row.site_code,
      site_name: row.site_code,
      current_quantity: row.current_quantity,
      reorder_point: row.reorder_point,
      risk_level: toRiskLevel(row.current_quantity, row.reorder_point),
      suggested_reorder_qty: row.reorder_quantity,
      days_of_stock: null,
    }));
  });

  return { data, error, isLoading, mutate };
}
