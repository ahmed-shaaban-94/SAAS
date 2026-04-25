"use client";

import { useEffect, useRef } from "react";
import { cn } from "@/lib/utils";
import { cleanDrugName } from "@/lib/pos/format-drug-name";
import { fmtEgp, type QuickPickItem } from "./types";

interface ScanDisambigPickerProps {
  /** Non-empty = visible; [] = hidden. Show top 3. */
  candidates: QuickPickItem[];
  /** User picked a candidate (or pressed 1/2/3). */
  onPick: (item: QuickPickItem) => void;
  /** User dismissed (Esc or click-outside). */
  onCancel: () => void;
}

/**
 * Shown when a barcode-scan query matches more than one product by
 * substring. Lets the cashier pick the intended SKU with a single
 * keypress (1, 2, or 3) instead of silently landing on the first
 * catalog hit — the "ambiguous scan" footgun the audit flagged at
 * §4.2 click-path item 1.
 */
export function ScanDisambigPicker({
  candidates,
  onPick,
  onCancel,
}: ScanDisambigPickerProps) {
  const firstBtnRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (candidates.length === 0) return;
    firstBtnRef.current?.focus();
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") {
        e.preventDefault();
        onCancel();
        return;
      }
      const idx = parseInt(e.key, 10) - 1;
      if (idx >= 0 && idx < candidates.length) {
        e.preventDefault();
        onPick(candidates[idx]);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [candidates, onPick, onCancel]);

  if (candidates.length === 0) return null;

  const visible = candidates.slice(0, 3);

  return (
    <div
      role="dialog"
      aria-label="Multiple matches — pick one"
      data-testid="scan-disambig-picker"
      className="fixed inset-0 z-[200] flex items-center justify-center bg-black/60 p-6"
      onClick={onCancel}
    >
      <div
        className={cn(
          "w-full max-w-md rounded-2xl border border-cyan-400/30 p-5",
          "bg-[rgba(8,24,38,0.96)]",
          "shadow-[0_0_0_1px_rgba(0,199,242,0.12),0_20px_60px_rgba(0,0,0,0.6)]",
        )}
        onClick={(e) => e.stopPropagation()}
      >
        <div
          className="font-mono text-[10px] font-bold uppercase tracking-[0.22em] text-cyan-300"
          aria-hidden="true"
        >
          ● Multiple matches
        </div>
        <h2 className="mt-1.5 font-[family-name:var(--font-fraunces)] text-xl italic text-text-primary">
          Which one did you scan?
        </h2>
        <p className="mt-1 text-xs text-text-secondary">
          Press 1 – {visible.length} to pick, or Esc to cancel.
        </p>

        <div className="mt-4 flex flex-col gap-2">
          {visible.map((tile, idx) => {
            const n = idx + 1;
            return (
              <button
                key={tile.drug_code}
                ref={idx === 0 ? firstBtnRef : undefined}
                type="button"
                onClick={() => onPick(tile)}
                data-testid={`scan-disambig-option-${n}`}
                className={cn(
                  "flex items-center gap-3 rounded-xl p-3 text-start",
                  "border border-[var(--pos-line)] bg-black/30",
                  "transition-colors hover:border-cyan-400/50 hover:bg-cyan-400/5",
                  "focus-visible:border-cyan-400/70 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-cyan-400/40",
                )}
              >
                <kbd
                  className={cn(
                    "grid h-6 min-w-[24px] place-items-center rounded border border-border bg-surface-raised px-1.5",
                    "font-mono text-[11px] font-semibold text-cyan-300",
                  )}
                >
                  {n}
                </kbd>
                <div className="min-w-0 flex-1">
                  <div className="truncate text-sm font-semibold text-text-primary">
                    {cleanDrugName(tile.drug_name)}
                  </div>
                  <div className="mt-0.5 font-mono text-[10px] uppercase tracking-wider text-text-secondary">
                    {tile.drug_code}
                  </div>
                </div>
                <div className="font-mono text-sm font-semibold tabular-nums text-cyan-300">
                  {fmtEgp(tile.unit_price)}
                </div>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
