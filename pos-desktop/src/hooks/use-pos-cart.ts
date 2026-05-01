import { usePosCartStore } from "@pos/store/cart-store";
import type { AppliedCartDiscount } from "@pos/store/cart-store";
import type { PosCartItem } from "@pos/types/pos";

// Re-export types that consumers may import from this file
export type { AppliedCartDiscount };

/**
 * usePosCart — thin selector hook over the Zustand pos-cart store.
 *
 * Return shape is identical to the previous Context-based implementation so
 * all existing consumers compile without modification.
 *
 * Each field subscribes to only the slice it needs, eliminating the cascading
 * re-renders that occurred when any cart action re-rendered every Context consumer.
 */
export function usePosCart() {
  const items = usePosCartStore((s) => s.items);
  const appliedDiscount = usePosCartStore((s) => s.appliedDiscount);

  const addItem = usePosCartStore((s) => s.addItem);
  const removeItem = usePosCartStore((s) => s.removeItem);
  const updateQuantity = usePosCartStore((s) => s.updateQuantity);
  const applyDiscount = usePosCartStore((s) => s.applyDiscount);
  const clearDiscount = usePosCartStore((s) => s.clearDiscount);

  // Aliased as clearCart to match the previous context API surface
  const clearCart = usePosCartStore((s) => s.clear);

  // Derived values — each re-evaluates only when store state changes
  const subtotal = usePosCartStore((s) => s.subtotal());
  const itemDiscountTotal = usePosCartStore((s) => s.itemDiscountTotal());
  /** Applied cart-level discount in EGP (separate from per-item discounts). */
  const cartDiscountTotal = usePosCartStore((s) => s.cartDiscountTotal());
  const voucherDiscount = usePosCartStore((s) => s.voucherDiscount());
  const discountTotal = usePosCartStore((s) => s.discountTotal());
  const itemCount = usePosCartStore((s) => s.itemCount());
  const hasControlledSubstance = usePosCartStore((s) => s.hasControlledSubstance());
  /** Pharmacy items are zero-rated; taxTotal is always 0. Kept for API symmetry. */
  const taxTotal = 0;
  const grandTotal = usePosCartStore((s) => s.grandTotal());

  return {
    // State
    items,
    appliedDiscount,

    // Actions
    addItem,
    removeItem,
    updateQuantity,
    applyDiscount,
    clearDiscount,
    clearCart,

    // Derived totals
    subtotal,
    itemDiscountTotal,
    cartDiscountTotal,
    voucherDiscount,
    discountTotal,
    taxTotal,
    grandTotal,
    itemCount,
    hasControlledSubstance,
  } satisfies {
    items: PosCartItem[];
    appliedDiscount: AppliedCartDiscount | null;
    addItem: (item: PosCartItem) => void;
    removeItem: (drugCode: string) => void;
    updateQuantity: (drugCode: string, quantity: number) => void;
    applyDiscount: (discount: AppliedCartDiscount) => void;
    clearDiscount: () => void;
    clearCart: () => void;
    subtotal: number;
    itemDiscountTotal: number;
    cartDiscountTotal: number;
    voucherDiscount: number;
    discountTotal: number;
    taxTotal: number;
    grandTotal: number;
    itemCount: number;
    hasControlledSubstance: boolean;
  };
}
