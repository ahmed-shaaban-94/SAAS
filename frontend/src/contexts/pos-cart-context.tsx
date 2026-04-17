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

// ---- State ----

interface CartState {
  items: PosCartItem[];
}

// ---- Actions ----

type CartAction =
  | { type: "ADD_ITEM"; item: PosCartItem }
  | { type: "REMOVE_ITEM"; drugCode: string }
  | { type: "UPDATE_QUANTITY"; drugCode: string; quantity: number }
  | { type: "CLEAR" };

function cartReducer(state: CartState, action: CartAction): CartState {
  switch (action.type) {
    case "ADD_ITEM": {
      const exists = state.items.findIndex((i) => i.drug_code === action.item.drug_code);
      if (exists >= 0) {
        // Increment quantity, recalculate line_total
        return {
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
      return { items: [...state.items, action.item] };
    }

    case "REMOVE_ITEM":
      return { items: state.items.filter((i) => i.drug_code !== action.drugCode) };

    case "UPDATE_QUANTITY": {
      if (action.quantity <= 0) {
        return { items: state.items.filter((i) => i.drug_code !== action.drugCode) };
      }
      return {
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
      return { items: [] };
  }
}

// ---- Context ----

interface PosCartContextValue {
  items: PosCartItem[];
  addItem: (item: PosCartItem) => void;
  removeItem: (drugCode: string) => void;
  updateQuantity: (drugCode: string, quantity: number) => void;
  clearCart: () => void;
  // Derived totals (string-based: no JS float arithmetic on money)
  subtotal: number;
  discountTotal: number;
  taxTotal: number;
  grandTotal: number;
  itemCount: number;
  hasControlledSubstance: boolean;
}

const PosCartContext = createContext<PosCartContextValue | null>(null);

export function PosCartProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(cartReducer, { items: [] });

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

  // All derived values computed here — no money arithmetic in components
  const subtotal = useMemo(
    () => state.items.reduce((sum, i) => sum + i.quantity * i.unit_price, 0),
    [state.items],
  );

  const discountTotal = useMemo(
    () => state.items.reduce((sum, i) => sum + i.discount, 0),
    [state.items],
  );

  const taxTotal = 0; // Pharmacy items: typically zero-rated; extend if needed

  const grandTotal = useMemo(
    () => subtotal - discountTotal + taxTotal,
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
      addItem,
      removeItem,
      updateQuantity,
      clearCart,
      subtotal,
      discountTotal,
      taxTotal,
      grandTotal,
      itemCount,
      hasControlledSubstance,
    }),
    [
      state.items,
      addItem,
      removeItem,
      updateQuantity,
      clearCart,
      subtotal,
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
