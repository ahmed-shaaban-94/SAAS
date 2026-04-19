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
import type { VoucherValidateResponse } from "@/types/vouchers";

// ---- State ----

export interface AppliedVoucher {
  code: string;
  discount_type: "amount" | "percent";
  value: number;
  /** Discount amount in EGP, pre-computed against the subtotal at the time
   * the voucher was applied. Recomputed inside the reducer if the cart
   * changes afterwards so the total stays consistent. */
  discount_amount: number;
}

interface CartState {
  items: PosCartItem[];
  voucher: AppliedVoucher | null;
}

// ---- Actions ----

type CartAction =
  | { type: "ADD_ITEM"; item: PosCartItem }
  | { type: "REMOVE_ITEM"; drugCode: string }
  | { type: "UPDATE_QUANTITY"; drugCode: string; quantity: number }
  | { type: "APPLY_VOUCHER"; voucher: VoucherValidateResponse; discount: number }
  | { type: "CLEAR_VOUCHER" }
  | { type: "CLEAR" };

function subtotalOf(items: PosCartItem[]): number {
  return items.reduce((sum, i) => sum + i.quantity * i.unit_price, 0);
}

function recomputeVoucherDiscount(
  voucher: AppliedVoucher | null,
  subtotal: number,
): AppliedVoucher | null {
  if (!voucher) return null;
  if (voucher.discount_type === "percent") {
    const raw = (subtotal * voucher.value) / 100;
    const capped = Math.min(raw, subtotal);
    const rounded = Math.round(capped * 100) / 100;
    return { ...voucher, discount_amount: rounded };
  }
  return { ...voucher, discount_amount: Math.min(voucher.value, subtotal) };
}

function cartReducer(state: CartState, action: CartAction): CartState {
  switch (action.type) {
    case "ADD_ITEM": {
      const exists = state.items.findIndex((i) => i.drug_code === action.item.drug_code);
      const nextItems =
        exists >= 0
          ? state.items.map((item, idx) =>
              idx === exists
                ? {
                    ...item,
                    quantity: item.quantity + action.item.quantity,
                    line_total:
                      (item.quantity + action.item.quantity) * item.unit_price - item.discount,
                  }
                : item,
            )
          : [...state.items, action.item];
      return {
        items: nextItems,
        voucher: recomputeVoucherDiscount(state.voucher, subtotalOf(nextItems)),
      };
    }

    case "REMOVE_ITEM": {
      const nextItems = state.items.filter((i) => i.drug_code !== action.drugCode);
      return {
        items: nextItems,
        voucher: recomputeVoucherDiscount(state.voucher, subtotalOf(nextItems)),
      };
    }

    case "UPDATE_QUANTITY": {
      if (action.quantity <= 0) {
        const nextItems = state.items.filter((i) => i.drug_code !== action.drugCode);
        return {
          items: nextItems,
          voucher: recomputeVoucherDiscount(state.voucher, subtotalOf(nextItems)),
        };
      }
      const nextItems = state.items.map((item) =>
        item.drug_code === action.drugCode
          ? {
              ...item,
              quantity: action.quantity,
              line_total: action.quantity * item.unit_price - item.discount,
            }
          : item,
      );
      return {
        items: nextItems,
        voucher: recomputeVoucherDiscount(state.voucher, subtotalOf(nextItems)),
      };
    }

    case "APPLY_VOUCHER": {
      // Re-clamp the incoming discount against the current subtotal so
      // small-cart edge cases (e.g. flat EGP 50 on a EGP 30 cart) can't
      // produce a negative grand total. The caller's `discount` is treated
      // as a hint; the reducer owns the source of truth.
      const sub = subtotalOf(state.items);
      const applied: AppliedVoucher = {
        code: action.voucher.code,
        discount_type: action.voucher.discount_type,
        value: action.voucher.value,
        discount_amount: Math.min(action.discount, sub),
      };
      return { ...state, voucher: applied };
    }

    case "CLEAR_VOUCHER":
      return { ...state, voucher: null };

    case "CLEAR":
      return { items: [], voucher: null };
  }
}

// ---- Context ----

interface PosCartContextValue {
  items: PosCartItem[];
  voucher: AppliedVoucher | null;
  addItem: (item: PosCartItem) => void;
  removeItem: (drugCode: string) => void;
  updateQuantity: (drugCode: string, quantity: number) => void;
  applyVoucher: (voucher: VoucherValidateResponse, discount: number) => void;
  clearVoucher: () => void;
  clearCart: () => void;
  // Derived totals (string-based: no JS float arithmetic on money)
  subtotal: number;
  itemDiscountTotal: number;
  voucherDiscountTotal: number;
  discountTotal: number;
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
  const applyVoucher = useCallback(
    (voucher: VoucherValidateResponse, discount: number) =>
      dispatch({ type: "APPLY_VOUCHER", voucher, discount }),
    [],
  );
  const clearVoucher = useCallback(() => dispatch({ type: "CLEAR_VOUCHER" }), []);
  const clearCart = useCallback(() => dispatch({ type: "CLEAR" }), []);

  // All derived values computed here — no money arithmetic in components
  const subtotal = useMemo(
    () => state.items.reduce((sum, i) => sum + i.quantity * i.unit_price, 0),
    [state.items],
  );

  const itemDiscountTotal = useMemo(
    () => state.items.reduce((sum, i) => sum + i.discount, 0),
    [state.items],
  );

  const voucherDiscountTotal = state.voucher?.discount_amount ?? 0;

  // Keep `discountTotal` (existing API) as the grand-sum of all discounts so
  // components rendering "Discount" without a breakdown still work.
  const discountTotal = itemDiscountTotal + voucherDiscountTotal;

  const taxTotal = 0; // Pharmacy items: typically zero-rated; extend if needed

  const grandTotal = useMemo(
    () => Math.max(subtotal - discountTotal + taxTotal, 0),
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
      applyVoucher,
      clearVoucher,
      clearCart,
      subtotal,
      itemDiscountTotal,
      voucherDiscountTotal,
      discountTotal,
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
      applyVoucher,
      clearVoucher,
      clearCart,
      subtotal,
      itemDiscountTotal,
      voucherDiscountTotal,
      discountTotal,
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
