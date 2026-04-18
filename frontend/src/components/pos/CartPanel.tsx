"use client";

import { ShoppingCart, Trash2 } from "lucide-react";
import { usePosCart } from "@/hooks/use-pos-cart";
import { CartItem } from "./CartItem";
import { cn } from "@/lib/utils";

function fmt(n: number): string {
  return n.toLocaleString("ar-EG", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

interface CartPanelProps {
  className?: string;
}

export function CartPanel({ className }: CartPanelProps) {
  const { items, subtotal, discountTotal, taxTotal, grandTotal, updateQuantity, removeItem, clearCart } =
    usePosCart();

  return (
    <div className={cn("flex flex-col", className)}>
      {/* Header */}
      <div className="flex items-center justify-between px-1 pb-2">
        <div className="flex items-center gap-2">
          <ShoppingCart className="h-4 w-4 text-text-secondary" />
          <span className="text-sm font-semibold text-text-primary">CART</span>
          {items.length > 0 && (
            <span className="rounded-full bg-accent/20 px-1.5 py-0.5 text-[10px] font-bold text-accent">
              {items.length}
            </span>
          )}
        </div>
        {items.length > 0 && (
          <button
            type="button"
            onClick={clearCart}
            aria-label="Clear cart"
            className="flex items-center gap-1 rounded-lg px-2 py-1 text-xs text-text-secondary hover:bg-destructive/10 hover:text-destructive"
          >
            <Trash2 className="h-3.5 w-3.5" />
            Clear
          </button>
        )}
      </div>

      {/* Items list */}
      <div className="flex-1 space-y-2 overflow-y-auto pr-1">
        {items.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-text-secondary">
            <ShoppingCart className="mb-2 h-8 w-8 opacity-30" />
            <p className="text-sm">Cart is empty</p>
            <p className="mt-1 text-xs opacity-60">Search and add items</p>
          </div>
        ) : (
          items.map((item) => (
            <CartItem
              key={item.drug_code}
              item={item}
              onQuantityChange={updateQuantity}
              onRemove={removeItem}
            />
          ))
        )}
      </div>

      {/* Totals */}
      {items.length > 0 && (
        <div className="mt-3 space-y-1 border-t border-border/50 pt-3">
          <div className="flex justify-between text-sm text-text-secondary">
            <span>Subtotal</span>
            <span className="tabular-nums">EGP {fmt(subtotal)}</span>
          </div>
          {discountTotal > 0 && (
            <div className="flex justify-between text-sm text-green-400">
              <span>Discount</span>
              <span className="tabular-nums">-EGP {fmt(discountTotal)}</span>
            </div>
          )}
          {taxTotal > 0 && (
            <div className="flex justify-between text-sm text-text-secondary">
              <span>Tax</span>
              <span className="tabular-nums">EGP {fmt(taxTotal)}</span>
            </div>
          )}
          <div className="flex justify-between border-t border-border/50 pt-2 text-base font-bold text-text-primary">
            <span>GRAND TOTAL</span>
            <span className="tabular-nums text-accent">EGP {fmt(grandTotal)}</span>
          </div>
        </div>
      )}
    </div>
  );
}
