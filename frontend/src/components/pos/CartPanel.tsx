"use client";

import { ShoppingCart, Trash2, X } from "lucide-react";
import { usePosCart } from "@/hooks/use-pos-cart";
import { CartItem } from "./CartItem";
import { cn } from "@/lib/utils";
import { EmptyState } from "@/components/empty-state";

function fmt(n: number): string {
  return n.toLocaleString("ar-EG", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

interface CartPanelProps {
  className?: string;
}

export function CartPanel({ className }: CartPanelProps) {
  const {
    items,
    subtotal,
    itemDiscountTotal,
    cartDiscountTotal,
    taxTotal,
    grandTotal,
    appliedDiscount,
    updateQuantity,
    removeItem,
    clearDiscount,
    clearCart,
  } = usePosCart();

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
      <div className="flex-1 space-y-2 overflow-y-auto pe-1">
        {items.length === 0 ? (
          <div className="flex flex-col items-center justify-center gap-3 py-10 text-center">
            <div className="font-mono text-[22px] text-text-secondary/30">▬▬▬</div>
            <p
              dir="rtl"
              style={{ fontFamily: "var(--font-plex-arabic, sans-serif)", fontWeight: 700, fontSize: 15 }}
              className="text-text-secondary"
            >
              ابدأ بمسح الصنف أو اختيار من الأصناف السريعة
            </p>
            <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-text-secondary/50">
              Scan barcode · F1 to search · press 1–8 to quick-pick
            </p>
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
          {itemDiscountTotal > 0 && (
            <div className="flex justify-between text-sm text-green-400">
              <span>Item discount</span>
              <span className="tabular-nums">-EGP {fmt(itemDiscountTotal)}</span>
            </div>
          )}
          {appliedDiscount && (
            <div className="flex items-center justify-between text-sm text-green-400">
              <span className="flex items-center gap-1.5">
                <span className="inline-block rounded bg-green-500/10 px-1.5 py-0.5 text-[10px] uppercase tracking-wider">
                  {appliedDiscount.source}
                </span>
                <span className="truncate">{appliedDiscount.label}</span>
                <button
                  type="button"
                  onClick={clearDiscount}
                  aria-label={`Remove ${appliedDiscount.source} ${appliedDiscount.label}`}
                  className="rounded p-0.5 text-text-secondary hover:bg-destructive/10 hover:text-destructive"
                >
                  <X className="h-3 w-3" />
                </button>
              </span>
              <span className="tabular-nums">-EGP {fmt(cartDiscountTotal)}</span>
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
