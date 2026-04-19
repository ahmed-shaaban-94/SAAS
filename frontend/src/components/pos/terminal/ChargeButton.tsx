"use client";

import { cn } from "@/lib/utils";
import { fmtEgp } from "./types";

interface ChargeButtonProps {
  grandTotal: number;
  disabled: boolean;
  onCharge: () => void;
}

/**
 * Full-width charge CTA at the bottom of the right column.
 * Cyan gradient when enabled, muted border when disabled. Shows:
 *   [Charge] [total in large mono] [Enter ↵ kbd chip]
 */
export function ChargeButton({ grandTotal, disabled, onCharge }: ChargeButtonProps) {
  return (
    <button
      type="button"
      onClick={onCharge}
      disabled={disabled}
      aria-label={`Charge EGP ${fmtEgp(grandTotal)} (Enter)`}
      data-testid="charge-button"
      className={cn(
        "grid items-center gap-3 rounded-xl px-5 py-4 transition-all duration-200",
        "[grid-template-columns:auto_1fr_auto]",
        disabled
          ? "cursor-not-allowed border border-[var(--pos-line)] bg-white/[0.04] text-text-secondary"
          : cn(
              "cursor-pointer border-0 text-[#021018]",
              "bg-gradient-to-b from-[#5cdfff] to-[#00a6cc]",
              "shadow-[0_0_24px_rgba(0,199,242,0.4),0_6px_16px_rgba(0,199,242,0.25),inset_0_1px_0_rgba(255,255,255,0.35)]",
              "hover:from-[#6be5ff] hover:to-[#00b5dd]",
            ),
      )}
    >
      <span className="text-[18px] font-bold">Charge</span>
      <span className="text-center font-mono text-[22px] font-bold tabular-nums">
        EGP {fmtEgp(grandTotal)}
      </span>
      <kbd
        className={cn(
          "rounded border px-2 py-0.5 font-mono text-[10px] font-semibold",
          disabled
            ? "border-border bg-surface-raised text-text-secondary"
            : "border-[rgba(2,16,24,0.3)] bg-[rgba(2,16,24,0.22)] text-[#021018]",
        )}
      >
        Enter ↵
      </kbd>
    </button>
  );
}
