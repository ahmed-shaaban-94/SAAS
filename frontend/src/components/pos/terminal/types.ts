import type { PaymentMethod, PosProductResult } from "@/types/pos";

/** Terminal v2 payment methods — subset of PaymentMethod that maps to a tile. */
export type TilePaymentMethod = Exclude<PaymentMethod, "mixed">;

export interface QuickPickItem {
  drug_code: string;
  drug_name: string;
  unit_price: number;
  is_controlled: boolean;
}

export function productToQuickPick(p: PosProductResult): QuickPickItem {
  return {
    drug_code: p.drug_code,
    drug_name: p.drug_name,
    unit_price: p.unit_price,
    is_controlled: p.is_controlled,
  };
}

export function fmtEgp(n: number): string {
  return n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
