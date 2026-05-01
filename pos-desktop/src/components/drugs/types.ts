import type { PosProductResult } from "@pos/types/pos";

export type StockTag = "out" | "low" | "watch" | "ok" | "unknown";

export interface DrugRow extends PosProductResult {
  /** Client-side classification derived from stock_available. */
  stock_tag: StockTag;
}

export type StockFilter = "all" | "low" | "out";
export type RxFilter = "all" | "rx" | "otc";
export type SortKey = "drug_name" | "drug_code" | "stock_available" | "unit_price";
export interface SortState {
  key: SortKey;
  dir: "asc" | "desc";
}

/**
 * Classify stock_available into a pill tag. The product-search endpoint
 * currently returns 0 for everything until the catalog-stock join lands,
 * so 0 maps to "unknown" (neutral pill, row still addable) rather than
 * "out" (red, add disabled).
 */
export function classifyStock(qty: number): StockTag {
  if (qty <= 0) return "unknown";
  if (qty < 5) return "low";
  if (qty < 15) return "watch";
  return "ok";
}

export function toDrugRow(p: PosProductResult): DrugRow {
  return { ...p, stock_tag: classifyStock(p.stock_available) };
}
