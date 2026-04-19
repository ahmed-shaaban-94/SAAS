"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useReducer,
  type ReactNode,
} from "react";
import type { PosCartItem } from "@/types/pos";

// ---- Voucher (Phase 1b) ----

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

// ---- State ----

interface CartState {
  items: PosCartItem[];
  voucher: CartVoucher | null;
}

// ---- Actions ----

type CartAction =
  | { type: "ADD_ITEM"; item: PosCartItem }
  | { type: "REMOVE_ITEM"; drugCode: string }
  | { type: "UPDATE_QUANTITY"; drugCode: string; quantity: number }
  | { type: "CLEAR" }
  | { type: "APPLY_VOUCHER"; voucher: CartVoucher }
  | { type: "REMOVE_VOUCHER" };

function cartReducer(state: CartState, action: CartAction): CartState {
  switch (action.type) {
    case "ADD_ITEM": {
      const exists = state.items.findIndex((i) => i.drug_code === action.item.drug_code);
      if (exists >= 0) {
        // Increment quantity, recalculate line_total
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

    case "REMOVE_ITEM":
      return { ...state, items: state.items.filter((i) => i.drug_code !== action.drugCode) };

    case "UPDATE_QUANTITY": {
      if (action.quantity <= 0) {
        return { ...state, items: state.items.filter((i) => i.drug_code !== action.drugCode) };
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

    case "CLEAR":
      return { items: [], voucher: null };

    case "APPLY_VOUCHER":
      return { ...state, voucher: action.voucher };

    case "REMOVE_VOUCHER":
      return { ...state, voucher: null };
  }
}

// ---- Context ----

interface PosCartContextValue {
  items: PosCartItem[];
  voucher: CartVoucher | null;
  addItem: (item: PosCartItem) => void;
  removeItem: (drugCode: string) => void;
  updateQuantity: (drugCode: string, quantity: number) => void;
  clearCart: () => void;
  applyVoucher: (voucher: CartVoucher) => void;
  removeVoucher: () => void;
  // Derived totals (string-based: no JS float arithmetic on money)
  subtotal: number;
  discountTotal: number;
  voucherDiscount: number;
  taxTotal: number;
  grandTotal: number;
  itemCount: number;
  hasControlledSubstance: boolean;
}

const PosCartContext = createContext<PosCartContextValue | null>(null);

export function PosCartProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(cartReducer, { items: [], voucher: null });

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
  const clearCart = useCallback(() => dispatch({ type: "CLEAR" }), []);
  const applyVoucher = useCallback(
    (voucher: CartVoucher) => dispatch({ type: "APPLY_VOUCHER", voucher }),
    [],
  );
  const removeVoucher = useCallback(() => dispatch({ type: "REMOVE_VOUCHER" }), []);

  // All derived values computed here — no money arithmetic in components
  const subtotal = useMemo(
    () => state.items.reduce((sum, i) => sum + i.quantity * i.unit_price, 0),
    [state.items],
  );

  const itemDiscountTotal = useMemo(
    () => state.items.reduce((sum, i) => sum + i.discount, 0),
    [state.items],
  );

  const voucherDiscount = state.voucher?.discount ?? 0;

  const discountTotal = useMemo(
    () => itemDiscountTotal + voucherDiscount,
    [itemDiscountTotal, voucherDiscount],
  );

  const taxTotal = 0; // Pharmacy items: typically zero-rated; extend if needed

  const grandTotal = useMemo(
    () => Math.max(0, subtotal - discountTotal + taxTotal),
    [subtotal, discountTotal],
  );

  const itemCount = useMemo(() => state.items.reduce((n, i) => n + i.quantity, 0), [state.items]);

  const hasControlledSubstance = useMemo(
    () => state.items.some((i) => i.is_controlled),
    [state.items],
  );

  const value = useMemo<PosCartContextValue>(
    () => ({
      items: state.items,
      voucher: state.voucher,
      addItem,
      removeItem,
      updateQuantity,
      clearCart,
      applyVoucher,
      removeVoucher,
      subtotal,
      discountTotal,
      voucherDiscount,
      taxTotal,
      grandTotal,
      itemCount,
      hasControlledSubstance,
    }),
    [
      state.items,
      state.voucher,
      addItem,
      removeItem,
      updateQuantity,
      clearCart,
      applyVoucher,
      removeVoucher,
      subtotal,
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
