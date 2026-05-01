// Voucher preview shape + discount calculation. Lifted verbatim from the
// passthrough pos-cart-context.tsx (Sub-PR 3 cleanup) — the cart store
// owns cart state, vouchers are a discount *source* and live separately.

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

/**
 * Compute the resolved EGP discount for a voucher against a given subtotal.
 * - 'amount' vouchers: cap at subtotal (never go negative)
 * - 'percent' vouchers: subtotal × value / 100, rounded to 2dp
 * - subtotal <= 0: returns 0 (no discount on empty cart)
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
