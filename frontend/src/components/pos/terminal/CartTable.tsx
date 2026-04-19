"use client";

import { Barcode } from "lucide-react";
import type { PosCartItem } from "@/types/pos";
import { cn } from "@/lib/utils";
import { CartRow } from "./CartRow";
import { fmtEgp } from "./types";

interface CartTableProps {
  items: PosCartItem[];
  /** Set of drug_codes that have not yet been synced to the server. */
  unsyncedCodes: Set<string>;
  itemCount: number;
  averageItem: number;
  onIncrement: (drugCode: string) => void;
  onDecrement: (drugCode: string) => void;
  onRemove: (drugCode: string) => void;
}

/**
 * Terminal v2 cart table — numbered rows, hairline dividers, empty state.
 * Delegates row rendering to CartRow; handles empty state + header strip.
 */
export function CartTable({
  items,
  unsyncedCodes,
  itemCount,
  averageItem,
  onIncrement,
  onDecrement,
  onRemove,
}: CartTableProps) {
  const isEmpty = items.length === 0;

  return (
    <div
      className={cn(
        "flex min-h-0 flex-1 flex-col overflow-hidden rounded-xl",
        "border border-[var(--pos-line)] bg-[rgba(8,24,38,0.5)]",
      )}
    >
      {/* Header strip */}
      <div
        className={cn(
          "grid items-center gap-1.5 border-b border-[var(--pos-line)] px-3.5 py-2.5",
          "bg-gradient-to-b from-white/5 to-transparent",
          "[grid-template-columns:28px_1fr_96px_88px_110px_28px]",
        )}
      >
        <div className="font-mono text-[10px] font-bold uppercase tracking-wider text-text-secondary">
          #
        </div>
        <div className="font-mono text-[10px] font-bold uppercase tracking-wider text-text-secondary">
          Cart{" "}
          {!isEmpty && (
            <span className="font-normal text-text-secondary/70">
              · <span className="tabular-nums">{itemCount}</span>{" "}
              {itemCount === 1 ? "item" : "items"}
              {itemCount > 0 && (
                <>
                  {" "}
                  · avg <span className="tabular-nums">{fmtEgp(averageItem)}</span>
                </>
              )}
            </span>
          )}
        </div>
        <div className="text-right font-mono text-[10px] font-bold uppercase tracking-wider text-text-secondary">
          Qty
        </div>
        <div className="text-right font-mono text-[10px] font-bold uppercase tracking-wider text-text-secondary">
          Price
        </div>
        <div className="text-right font-mono text-[10px] font-bold uppercase tracking-wider text-text-secondary">
          Line
        </div>
        <div />
      </div>

      <div className="flex-1 overflow-y-auto">
        {isEmpty ? (
          <div
            data-testid="cart-empty"
            className="flex h-full min-h-[180px] flex-col items-center justify-center gap-2 p-5 text-text-secondary"
          >
            <div className="grid h-14 w-14 place-items-center rounded-full border border-dashed border-cyan-400/30 bg-cyan-400/5 text-cyan-300">
              <Barcode className="h-6 w-6" />
            </div>
            <div className="pos-display text-[18px] text-text-primary">Cart is empty</div>
            <div className="text-[12.5px]">Start by scanning a drug</div>
          </div>
        ) : (
          items.map((item, idx) => (
            <CartRow
              key={item.drug_code}
              index={idx + 1}
              item={item}
              synced={!unsyncedCodes.has(item.drug_code)}
              onIncrement={onIncrement}
              onDecrement={onDecrement}
              onRemove={onRemove}
            />
          ))
        )}
      </div>
    </div>
  );
}
