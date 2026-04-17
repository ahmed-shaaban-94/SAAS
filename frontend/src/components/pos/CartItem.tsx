"use client";

import { Minus, Plus, Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";
import type { PosCartItem as CartItemType } from "@/types/pos";

interface CartItemProps {
  item: CartItemType;
  onQuantityChange: (drugCode: string, quantity: number) => void;
  onRemove: (drugCode: string) => void;
}

function fmt(n: number): string {
  return n.toLocaleString("ar-EG", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export function CartItem({ item, onQuantityChange, onRemove }: CartItemProps) {
  return (
    <div
      className={cn(
        "rounded-xl border border-border/50 bg-surface p-3 transition-colors",
        item.is_controlled && "border-amber-500/30 bg-amber-500/5",
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium text-text-primary">{item.drug_name}</p>
          {item.batch_number && (
            <p className="mt-0.5 text-xs text-text-secondary">
              Batch: {item.batch_number}
              {item.expiry_date && <span> · Exp: {item.expiry_date}</span>}
            </p>
          )}
          {item.is_controlled && (
            <span className="mt-1 inline-block rounded bg-amber-500/20 px-1.5 py-0.5 text-[10px] font-semibold text-amber-400">
              CONTROLLED
            </span>
          )}
        </div>
        <button
          type="button"
          onClick={() => onRemove(item.drug_code)}
          aria-label={`Remove ${item.drug_name}`}
          className="flex-shrink-0 rounded-lg p-1.5 text-text-secondary hover:bg-destructive/10 hover:text-destructive"
        >
          <Trash2 className="h-3.5 w-3.5" />
        </button>
      </div>

      <div className="mt-2 flex items-center justify-between">
        {/* Quantity controls — 48px minimum touch targets */}
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => onQuantityChange(item.drug_code, item.quantity - 1)}
            aria-label="Decrease quantity"
            className="flex h-8 w-8 items-center justify-center rounded-lg bg-surface-raised hover:bg-surface-raised/80 active:scale-95"
          >
            <Minus className="h-3.5 w-3.5" />
          </button>
          <span className="w-8 text-center text-sm font-semibold tabular-nums">
            {item.quantity}
          </span>
          <button
            type="button"
            onClick={() => onQuantityChange(item.drug_code, item.quantity + 1)}
            aria-label="Increase quantity"
            className="flex h-8 w-8 items-center justify-center rounded-lg bg-surface-raised hover:bg-surface-raised/80 active:scale-95"
          >
            <Plus className="h-3.5 w-3.5" />
          </button>
        </div>

        <div className="text-right">
          <p className="text-sm font-semibold tabular-nums text-text-primary">
            EGP {fmt(item.line_total)}
          </p>
          {item.discount > 0 && (
            <p className="text-xs text-text-secondary">
              -{fmt(item.discount)} discount
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
