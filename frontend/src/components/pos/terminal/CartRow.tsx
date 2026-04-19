"use client";

import { Minus, Plus, X } from "lucide-react";
import type { PosCartItem } from "@/types/pos";
import { cn } from "@/lib/utils";
import { fmtEgp } from "./types";

interface CartRowProps {
  index: number;
  item: PosCartItem;
  /** True when this line is synced to the server (false => amber queued rail). */
  synced: boolean;
  onIncrement: (drugCode: string) => void;
  onDecrement: (drugCode: string) => void;
  onRemove: (drugCode: string) => void;
}

/**
 * A single line in the Terminal v2 cart table. Six-column grid:
 *   [#] [Item + SKU + queued badge] [Qty stepper] [Unit] [Line total] [×]
 *
 * Unsynced rows get an amber 3px rail on the leading edge + QUEUED badge,
 * and the whole row fades up 220ms on mount via the dpRowEnter keyframe.
 */
export function CartRow({
  index,
  item,
  synced,
  onIncrement,
  onDecrement,
  onRemove,
}: CartRowProps) {
  return (
    <div
      data-testid={`cart-row-${item.drug_code}`}
      data-synced={synced ? "true" : "false"}
      style={{ animation: "dpRowEnter 220ms ease-out" }}
      className={cn(
        "relative grid items-center gap-1.5 border-b border-[var(--pos-line)] px-3.5 py-2.5",
        "[grid-template-columns:28px_1fr_96px_88px_110px_28px]",
        !synced && "pl-5",
      )}
    >
      {/* Amber rail for unsynced lines */}
      {!synced && (
        <span
          aria-hidden="true"
          className="absolute inset-y-0 left-0 w-[3px] bg-amber-400"
        />
      )}

      <div className="font-mono text-[11px] font-semibold tabular-nums text-text-secondary">
        {String(index).padStart(2, "0")}
      </div>

      <div className="flex min-w-0 flex-col gap-0.5">
        <div className="truncate text-sm font-semibold text-text-primary">{item.drug_name}</div>
        <div className="flex items-center gap-2.5">
          <span className="font-mono text-[10px] text-text-secondary">{item.drug_code}</span>
          {!synced && (
            <span
              data-testid="queued-badge"
              className={cn(
                "rounded px-1.5 py-px font-mono text-[9px] font-bold uppercase tracking-wider",
                "border border-amber-400/40 bg-amber-400/15 text-amber-400",
              )}
            >
              Queued
            </span>
          )}
          {item.is_controlled && (
            <span
              className={cn(
                "rounded px-1.5 py-px font-mono text-[9px] font-bold uppercase tracking-wider",
                "border border-rose-400/30 bg-rose-400/10 text-rose-300",
              )}
            >
              Rx
            </span>
          )}
        </div>
      </div>

      <div className="flex items-center justify-end gap-1">
        <button
          type="button"
          onClick={() => onDecrement(item.drug_code)}
          aria-label={`Decrease quantity of ${item.drug_name}`}
          className="grid h-6 w-6 place-items-center rounded border border-border bg-surface-raised text-text-primary hover:border-cyan-400/40"
        >
          <Minus className="h-3 w-3" />
        </button>
        <span className="min-w-[24px] text-center font-mono text-sm font-semibold tabular-nums text-text-primary">
          {item.quantity}
        </span>
        <button
          type="button"
          onClick={() => onIncrement(item.drug_code)}
          aria-label={`Increase quantity of ${item.drug_name}`}
          className="grid h-6 w-6 place-items-center rounded border border-cyan-400/30 bg-cyan-400/10 text-cyan-300 hover:border-cyan-400/60"
        >
          <Plus className="h-3 w-3" />
        </button>
      </div>

      <div className="text-right font-mono text-[13px] tabular-nums text-text-secondary">
        {fmtEgp(item.unit_price)}
      </div>

      <div className="text-right font-mono text-sm font-semibold tabular-nums text-text-primary">
        {fmtEgp(item.line_total)}
      </div>

      <button
        type="button"
        onClick={() => onRemove(item.drug_code)}
        aria-label={`Remove ${item.drug_name}`}
        className="grid h-6 w-6 place-items-center rounded text-text-secondary hover:text-rose-300"
      >
        <X className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}
