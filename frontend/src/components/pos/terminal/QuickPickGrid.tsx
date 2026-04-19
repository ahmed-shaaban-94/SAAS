"use client";

import { cn } from "@/lib/utils";
import { fmtEgp, type QuickPickItem } from "./types";

interface QuickPickGridProps {
  items: QuickPickItem[];
  onPick: (item: QuickPickItem) => void;
  /** Shown as a hint; does not affect behavior. */
  label?: string;
}

/**
 * 3x3 Quick Pick grid — first 9 favorite SKUs for this terminal.
 * Keyboard: pressing 1-9 activates the matching tile (wired in the page).
 * Each tile shows its numeric shortcut in the corner + price + name.
 */
export function QuickPickGrid({ items, onPick, label }: QuickPickGridProps) {
  // Pad to 9 so the grid keeps its shape even when catalog is short.
  const tiles: (QuickPickItem | null)[] = [...items.slice(0, 9)];
  while (tiles.length < 9) tiles.push(null);

  return (
    <div className="rounded-xl border border-[var(--pos-line)] bg-[rgba(8,24,38,0.35)] p-3">
      <div className="mb-2.5 flex items-center justify-between">
        <span className="font-mono text-[10px] font-bold uppercase tracking-[0.2em] text-text-secondary">
          {label ?? "Quick pick"}{" "}
          <span className="font-normal text-text-secondary/70">· press 1–9</span>
        </span>
      </div>
      <div role="grid" aria-label="Quick pick favorites" className="grid grid-cols-3 gap-1.5">
        {tiles.map((tile, idx) => {
          const n = idx + 1;
          if (!tile) {
            return (
              <div
                key={`empty-${n}`}
                role="gridcell"
                className={cn(
                  "flex min-h-[58px] flex-col gap-1 rounded-lg p-2.5",
                  "border border-dashed border-[var(--pos-line)] opacity-40",
                )}
              >
                <span className="font-mono text-[10px] text-text-secondary">{n}</span>
                <span className="text-xs text-text-secondary">—</span>
              </div>
            );
          }
          return (
            <button
              key={tile.drug_code}
              type="button"
              role="gridcell"
              onClick={() => onPick(tile)}
              aria-label={`Quick pick ${n}: ${tile.drug_name} at EGP ${fmtEgp(tile.unit_price)}`}
              data-testid={`quick-pick-${n}`}
              className={cn(
                "group flex min-h-[58px] flex-col gap-1 rounded-lg p-2.5 text-start",
                "border border-[var(--pos-line)] bg-[rgba(8,24,38,0.7)]",
                "transition-colors duration-150",
                "hover:border-cyan-400/50 hover:bg-cyan-400/5",
                "focus-visible:border-cyan-400/70 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-cyan-400/40",
              )}
            >
              <div className="flex items-center justify-between gap-1.5">
                <kbd
                  className={cn(
                    "grid h-[18px] min-w-[18px] place-items-center rounded border border-border bg-surface-raised px-1",
                    "font-mono text-[10px] font-semibold text-text-primary",
                  )}
                >
                  {n}
                </kbd>
                <span className="font-mono text-[11px] font-semibold tabular-nums text-cyan-300">
                  {fmtEgp(tile.unit_price)}
                </span>
              </div>
              <span className="truncate text-[12px] font-semibold leading-tight text-text-primary">
                {tile.drug_name}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
