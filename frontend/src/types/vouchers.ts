/**
 * Voucher types — mirror the Pydantic models in `src/datapulse/pos/models.py`.
 *
 * Phase 1 of the POS discount system. Financial fields arrive as JSON numbers
 * (because the backend uses `JsonDecimal`), but this module declares them as
 * `number` so components can render them without extra conversion.
 */

export type VoucherType = "amount" | "percent";

export type VoucherStatus = "active" | "redeemed" | "expired" | "void";

export interface Voucher {
  id: number;
  tenant_id: number;
  code: string;
  discount_type: VoucherType;
  value: number;
  max_uses: number;
  uses: number;
  status: VoucherStatus;
  starts_at: string | null;
  ends_at: string | null;
  min_purchase: number | null;
  redeemed_txn_id: number | null;
  created_at: string;
}

export interface VoucherCreateInput {
  code: string;
  discount_type: VoucherType;
  value: number;
  max_uses?: number;
  starts_at?: string | null;
  ends_at?: string | null;
  min_purchase?: number | null;
}

export interface VoucherValidateResponse {
  code: string;
  discount_type: VoucherType;
  value: number;
  remaining_uses: number;
  expires_at: string | null;
  min_purchase: number | null;
}
