"use client";

import { type ReactNode } from "react";
import type { AppliedDiscount } from "@/types/promotions";

// ---- Voucher preview shape ----
//
// Retained as an exported preview/DTO type for `VoucherCodeModal` — the cart
// no longer stores voucher-specific state. Vouchers are applied through the
// unified `applyDiscount` pathway with `source: "voucher"`.
export interface CartVoucher {
  /** Server voucher code — exactly as entered by the cashier (uppercased). */
  code: string;
  /** 'amount' = flat EGP off, 'percent' = % of subtotal (after item discounts). */
  discount_type: "amount" | "percent";
  /** Raw server value: EGP when 'amount', percentage when 'percent'. */
  value: number;
  /** Resolved discount in EGP — computed at apply time against the then-current cart. */
  discount: number;
}

// ---- Applied cart-level discount ----
//
// A cart-level discount is EITHER a voucher (by code) or a promotion (by id),
// carrying a human label for UI display and the computed discount amount in
// EGP. This matches the backend union type on ``CommitRequest.applied_discount``
// / ``CheckoutRequest.applied_discount``.
export interface AppliedCartDiscount {
  source: AppliedDiscount["source"]; // "voucher" | "promotion"
  ref: string; // voucher code or stringified promotion id
  label: string; // user-friendly label ("Ramadan 2026" / voucher code)
  discountAmount: number; // preview amount in EGP; backend re-computes canonically
}

/**
 * Compute the resolved EGP discount for a voucher against a given subtotal.
 * - 'amount' vouchers: cap at subtotal (never go negative)
 * - 'percent' vouchers: subtotal × value / 100, rounded to 2dp
 */
export function computeVoucherDiscount(
  discount_type: "amount" | "percent",
  value: number,
  subtotal: number,
): number {
  if (subtotal <= 0) return 0;
  if (discount_type === "amount") return Math.min(value, subtotal);
  const pct = (subtotal * value) / 100;
  return Math.round(pct * 100) / 100;
}

/**
 * PosCartProvider — kept for layout compatibility.
 * State now lives in the Zustand store (src/store/pos-cart-store.ts).
 */
export function PosCartProvider({ children }: { children: ReactNode }) {
  return <>{children}</>;
}
