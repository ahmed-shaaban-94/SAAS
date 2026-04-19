"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useReducer,
  type ReactNode,
} from "react";
import type { AppliedDiscount } from "@/types/promotions";
import type { PosCartItem } from "@/types/pos";

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
  source: AppliedDiscount["source"];
  ref: string; // voucher code or stringified promotion id
  label: string; // user-friendly label ("Ramadan 2026" / voucher code)
  discountAmount: number; // preview amount in EGP; backend re-computes canonically
}

// ---- State ----

interface CartState {
  items: PosCartItem[];
  appliedDiscount: AppliedCartDiscount | null;
}

// ---- Actions ----

type CartAction =
  | { type: "ADD_ITEM"; item: PosCartItem }
  | { type: "REMOVE_ITEM"; drugCode: string }
  | { type: "UPDATE_QUANTITY"; drugCode: string; quantity: number }
  | { type: "APPLY_DISCOUNT"; discount: AppliedCartDiscount }
  | { type: "CLEAR_DISCOUNT" }
  | { type: "CLEAR" };

function cartReducer(state: CartState, action: CartAction): CartState {
  switch (action.type) {
    case "ADD_ITEM": {
      const exists = state.items.findIndex((i) => i.drug_code === action.item.drug_code);
      if (exists >= 0) {
        return {
          ...state,
          items: state.items.map((item, idx) =>
            idx === exists
              ? {
                  ...item,
                  quantity: item.quantity + action.item.quantity,
                  line_total:
                    (item.quantity + action.item.quantity) * item.unit_price - item.discount,
                }
              : item,
          ),
        };
      }
      return { ...state, items: [...state.items, action.item] };
    }

    case "REMOVE_ITEM": {
      const items = state.items.filter((i) => i.drug_code !== action.drugCode);
      // If the cart is empty, the applied discount is no longer meaningful.
      return {
        items,
        appliedDiscount: items.length === 0 ? null : state.appliedDiscount,
      };
    }

    case "UPDATE_QUANTITY": {
      if (action.quantity <= 0) {
        const items = state.items.filter((i) => i.drug_code !== action.drugCode);
        return {
          items,
          appliedDiscount: items.length === 0 ? null : state.appliedDiscount,
        };
      }
      return {
        ...state,
        items: state.items.map((item) =>
          item.drug_code === action.drugCode
            ? {
                ...item,
                quantity: action.quantity,
                line_total: action.quantity * item.unit_price - item.discount,
              }
            : item,
        ),
      };
    }

    case "APPLY_DISCOUNT":
      return { ...state, appliedDiscount: action.discount };

    case "CLEAR_DISCOUNT":
      return { ...state, appliedDiscount: null };

    case "CLEAR":
      return { items: [], appliedDiscount: null };
  }
}

// ---- Context ----

interface PosCartContextValue {
  items: PosCartItem[];
  appliedDiscount: AppliedCartDiscount | null;
  addItem: (item: PosCartItem) => void;
  removeItem: (drugCode: string) => void;
  updateQuantity: (drugCode: string, quantity: number) => void;
  applyDiscount: (discount: AppliedCartDiscount) => void;
  clearDiscount: () => void;
  clearCart: () => void;
  // Derived totals (number-based — final canonical math happens on the backend)
  subtotal: number;
  itemDiscountTotal: number;
  cartDiscountTotal: number;
  discountTotal: number;
  /** Voucher-only projection of `cartDiscountTotal`; 0 when the applied
   * discount is a promotion or nothing is applied. Kept for the Terminal v2
   * payment tiles which still render vouchers distinctly from promotions. */
  voucherDiscount: number;
  taxTotal: number;
  grandTotal: number;
  itemCount: number;
  hasControlledSubstance: boolean;
}

const PosCartContext = createContext<PosCartContextValue | null>(null);

export function PosCartProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(cartReducer, {
    items: [],
    appliedDiscount: null,
  });

  const addItem = useCallback((item: PosCartItem) => dispatch({ type: "ADD_ITEM", item }), []);
  const removeItem = useCallback(
    (drugCode: string) => dispatch({ type: "REMOVE_ITEM", drugCode }),
    [],
  );
  const updateQuantity = useCallback(
    (drugCode: string, quantity: number) =>
      dispatch({ type: "UPDATE_QUANTITY", drugCode, quantity }),
    [],
  );
  const applyDiscount = useCallback(
    (discount: AppliedCartDiscount) => dispatch({ type: "APPLY_DISCOUNT", discount }),
    [],
  );
  const clearDiscount = useCallback(() => dispatch({ type: "CLEAR_DISCOUNT" }), []);
  const clearCart = useCallback(() => dispatch({ type: "CLEAR" }), []);

  const subtotal = useMemo(
    () => state.items.reduce((sum, i) => sum + i.quantity * i.unit_price, 0),
    [state.items],
  );

  const itemDiscountTotal = useMemo(
    () => state.items.reduce((sum, i) => sum + i.discount, 0),
    [state.items],
  );

  const cartDiscountTotal = state.appliedDiscount?.discountAmount ?? 0;

  const voucherDiscount =
    state.appliedDiscount?.source === "voucher" ? state.appliedDiscount.discountAmount : 0;

  const discountTotal = itemDiscountTotal + cartDiscountTotal;

  const taxTotal = 0; // Pharmacy items: typically zero-rated; extend if needed

  const grandTotal = useMemo(
    () => Math.max(0, subtotal - discountTotal + taxTotal),
    [subtotal, discountTotal],
  );

  const itemCount = useMemo(
    () => state.items.reduce((n, i) => n + i.quantity, 0),
    [state.items],
  );

  const hasControlledSubstance = useMemo(
    () => state.items.some((i) => i.is_controlled),
    [state.items],
  );

  const value = useMemo<PosCartContextValue>(
    () => ({
      items: state.items,
      appliedDiscount: state.appliedDiscount,
      addItem,
      removeItem,
      updateQuantity,
      applyDiscount,
      clearDiscount,
      clearCart,
      subtotal,
      itemDiscountTotal,
      cartDiscountTotal,
      discountTotal,
      voucherDiscount,
      taxTotal,
      grandTotal,
      itemCount,
      hasControlledSubstance,
    }),
    [
      state.items,
      state.appliedDiscount,
      addItem,
      removeItem,
      updateQuantity,
      applyDiscount,
      clearDiscount,
      clearCart,
      subtotal,
      itemDiscountTotal,
      cartDiscountTotal,
      discountTotal,
      voucherDiscount,
      grandTotal,
      itemCount,
      hasControlledSubstance,
    ],
  );

  return <PosCartContext.Provider value={value}>{children}</PosCartContext.Provider>;
}

export function usePosCart(): PosCartContextValue {
  const ctx = useContext(PosCartContext);
  if (!ctx) throw new Error("usePosCart must be used within PosCartProvider");
  return ctx;
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
