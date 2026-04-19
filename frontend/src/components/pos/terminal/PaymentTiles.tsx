"use client";

import { Banknote, CreditCard, Shield, Ticket, Check } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import type { TilePaymentMethod } from "./types";
import { fmtEgp } from "./types";

interface PaymentTilesProps {
  active: TilePaymentMethod;
  onSelect: (method: TilePaymentMethod) => void;
  /** Currently-applied voucher code, if any — shows a green check on the tile. */
  voucherCode: string | null;
  voucherDiscount: number;
  /** Insurance coverage % if active, else null. */
  insuranceCoveragePct: number | null;
  disabled?: boolean;
}

interface TileConfig {
  method: TilePaymentMethod;
  label: string;
  fkey: string;
  icon: LucideIcon;
  /** Hex rgb string used as the accent for this tile. */
  accent: string;
  tone: "cyan" | "green" | "amber" | "purple";
}

const TILES: TileConfig[] = [
  { method: "cash", label: "Cash", fkey: "F9", icon: Banknote, accent: "#1dd48b", tone: "green" },
  { method: "card", label: "Card", fkey: "F10", icon: CreditCard, accent: "#00c7f2", tone: "cyan" },
  {
    method: "insurance",
    label: "Insurance",
    fkey: "F11",
    icon: Shield,
    accent: "#7467f8",
    tone: "purple",
  },
  {
    method: "voucher",
    label: "Voucher",
    fkey: "F7",
    icon: Ticket,
    accent: "#ffab3d",
    tone: "amber",
  },
];

const ACTIVE_RING: Record<TileConfig["tone"], string> = {
  cyan: "border-cyan-400 shadow-[0_0_0_1px_rgba(0,199,242,0.3),0_0_24px_rgba(0,199,242,0.25)]",
  green:
    "border-emerald-400 shadow-[0_0_0_1px_rgba(29,212,139,0.3),0_0_24px_rgba(29,212,139,0.25)]",
  amber:
    "border-amber-400 shadow-[0_0_0_1px_rgba(255,171,61,0.3),0_0_24px_rgba(255,171,61,0.25)]",
  purple:
    "border-violet-400 shadow-[0_0_0_1px_rgba(116,103,248,0.3),0_0_24px_rgba(116,103,248,0.25)]",
};

const RAIL_BG: Record<TileConfig["tone"], string> = {
  cyan: "bg-cyan-400",
  green: "bg-emerald-400",
  amber: "bg-amber-400",
  purple: "bg-violet-400",
};

/**
 * 2x2 payment method tiles — cash / card / insurance / voucher.
 * Active tile gets a 3px accent rail on the inside leading edge and a
 * glowing ring. Voucher tile renders an extra green check + discount
 * amount when a voucher is already attached to the cart.
 */
export function PaymentTiles({
  active,
  onSelect,
  voucherCode,
  voucherDiscount,
  insuranceCoveragePct,
  disabled,
}: PaymentTilesProps) {
  return (
    <div role="group" aria-label="Payment methods" className="grid grid-cols-2 gap-2">
      {TILES.map((tile) => {
        const Icon = tile.icon;
        const isActive = active === tile.method;
        const hasVoucher = tile.method === "voucher" && !!voucherCode;
        const hasInsurance = tile.method === "insurance" && !!insuranceCoveragePct;
        return (
          <button
            key={tile.method}
            type="button"
            aria-pressed={isActive}
            aria-label={`Pay with ${tile.label} (${tile.fkey})`}
            disabled={disabled}
            onClick={() => onSelect(tile.method)}
            data-testid={`pay-tile-${tile.method}`}
            className={cn(
              "relative flex flex-col items-start gap-1.5 overflow-hidden rounded-xl border-2 p-3 text-start",
              "transition-all duration-150",
              isActive
                ? ACTIVE_RING[tile.tone]
                : "border-[var(--pos-line)] bg-[rgba(8,24,38,0.5)] hover:border-[var(--pos-line-strong)]",
              disabled && "pointer-events-none opacity-40",
            )}
            style={
              isActive
                ? {
                    background: `color-mix(in oklab, ${tile.accent} 12%, rgba(8,24,38,0.7))`,
                  }
                : undefined
            }
          >
            {/* Active accent rail on the inside leading edge */}
            {isActive && (
              <span
                aria-hidden="true"
                className={cn("absolute inset-y-0 left-0 w-[3px]", RAIL_BG[tile.tone])}
              />
            )}

            <div className="flex w-full items-center justify-between">
              <Icon
                className="h-5 w-5"
                style={{ color: isActive ? tile.accent : "var(--pos-ink-2)" }}
                aria-hidden="true"
              />
              <kbd
                className={cn(
                  "rounded border px-1.5 py-0.5 font-mono text-[10px] font-semibold",
                  isActive
                    ? "border-white/20 bg-white/10 text-text-primary"
                    : "border-border bg-surface-raised text-text-secondary",
                )}
              >
                {tile.fkey}
              </kbd>
            </div>

            <div className="text-sm font-semibold text-text-primary">{tile.label}</div>

            {hasVoucher ? (
              <div className="flex items-center gap-1.5 text-[10.5px]">
                <Check className="h-3 w-3 text-emerald-400" aria-hidden="true" />
                <span className="font-mono text-amber-300">−EGP {fmtEgp(voucherDiscount)}</span>
              </div>
            ) : hasInsurance ? (
              <div className="font-mono text-[10.5px] text-violet-300">
                {insuranceCoveragePct}% covered
              </div>
            ) : (
              <div
                className={cn(
                  "font-mono text-[9px] font-medium uppercase tracking-[0.14em]",
                  "text-text-secondary/80",
                )}
              >
                {tile.method === "cash" && "Enter amount"}
                {tile.method === "card" && "Pinpad ready"}
                {tile.method === "insurance" && "Pick insurer"}
                {tile.method === "voucher" && "Enter code"}
              </div>
            )}
          </button>
        );
      })}
    </div>
  );
}
