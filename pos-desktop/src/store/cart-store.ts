import { create } from "zustand";
import type { PosCartItem } from "@pos/types/pos";
import type { AppliedCartDiscount } from "@pos/contexts/pos-cart-context";

// ---- State shape ----

interface PosCartState {
  items: PosCartItem[];
  appliedDiscount: AppliedCartDiscount | null;

  // Actions
  addItem: (item: PosCartItem) => void;
  removeItem: (drugCode: string) => void;
  updateQuantity: (drugCode: string, quantity: number) => void;
  applyDiscount: (discount: AppliedCartDiscount) => void;
  clearDiscount: () => void;
  clear: () => void;

  // Derived selectors (called as functions — snapshot-safe in tests, reactive in hooks)
  /** Gross sum: quantity × unit_price (before item-level discounts). */
  subtotal: () => number;
  /** Sum of per-line `discount` field (flat EGP amounts). */
  itemDiscountTotal: () => number;
  /** Applied cart-level discount amount in EGP (0 when no discount applied). */
  cartDiscountTotal: () => number;
  /** Voucher-sourced discount only; 0 when source is 'promotion' or nothing applied. */
  voucherDiscount: () => number;
  /** itemDiscountTotal + cartDiscountTotal. */
  discountTotal: () => number;
  /** Total item quantity across all lines. */
  itemCount: () => number;
  /** True when any item in the cart is a controlled substance. */
  hasControlledSubstance: () => boolean;
  /** max(0, subtotal - discountTotal). Pharmacy items are zero-rated (taxTotal = 0). */
  grandTotal: () => number;
}

// ---- Helpers ----

/** Re-compute line_total when quantity changes. Preserves the flat EGP discount. */
function recalcLine(item: PosCartItem, newQty: number): PosCartItem {
  return {
    ...item,
    quantity: newQty,
    line_total: newQty * item.unit_price - item.discount,
  };
}

/** When a cart is empty, clear the applied discount — it's no longer meaningful. */
function maybeClearDiscount(
  items: PosCartItem[],
  current: AppliedCartDiscount | null,
): AppliedCartDiscount | null {
  return items.length === 0 ? null : current;
}

// ---- Store ----

export const usePosCartStore = create<PosCartState>((set, get) => ({
  items: [],
  appliedDiscount: null,

  addItem: (incoming) =>
    set((state) => {
      const existingIdx = state.items.findIndex((i) => i.drug_code === incoming.drug_code);
      if (existingIdx >= 0) {
        const existing = state.items[existingIdx];
        const newQty = existing.quantity + incoming.quantity;
        return {
          items: state.items.map((item, idx) =>
            idx === existingIdx ? recalcLine(item, newQty) : item,
          ),
        };
      }
      return { items: [...state.items, incoming] };
    }),

  removeItem: (drugCode) =>
    set((state) => {
      const items = state.items.filter((i) => i.drug_code !== drugCode);
      return { items, appliedDiscount: maybeClearDiscount(items, state.appliedDiscount) };
    }),

  updateQuantity: (drugCode, quantity) =>
    set((state) => {
      if (quantity <= 0) {
        const items = state.items.filter((i) => i.drug_code !== drugCode);
        return { items, appliedDiscount: maybeClearDiscount(items, state.appliedDiscount) };
      }
      return {
        items: state.items.map((item) =>
          item.drug_code === drugCode ? recalcLine(item, quantity) : item,
        ),
      };
    }),

  applyDiscount: (discount) => set({ appliedDiscount: discount }),
  clearDiscount: () => set({ appliedDiscount: null }),
  clear: () => set({ items: [], appliedDiscount: null }),

  // --- Derived selectors ---

  subtotal: () => get().items.reduce((sum, i) => sum + i.quantity * i.unit_price, 0),

  itemDiscountTotal: () => get().items.reduce((sum, i) => sum + i.discount, 0),

  cartDiscountTotal: () => get().appliedDiscount?.discountAmount ?? 0,

  voucherDiscount: () => {
    const d = get().appliedDiscount;
    return d?.source === "voucher" ? d.discountAmount : 0;
  },

  discountTotal: () => {
    const s = get();
    return s.itemDiscountTotal() + s.cartDiscountTotal();
  },

  itemCount: () => get().items.reduce((sum, i) => sum + i.quantity, 0),

  hasControlledSubstance: () => get().items.some((i) => i.is_controlled),

  grandTotal: () => {
    const s = get();
    return Math.max(0, s.subtotal() - s.discountTotal());
  },
}));
