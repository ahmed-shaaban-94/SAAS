"use client";

import { Printer } from "lucide-react";
import { cn } from "@/lib/utils";

interface ReconcileGridProps {
  opening: number;
  cashSales: number;
  counted: string;
  onCountedChange: (v: string) => void;
  onFinalize: () => void;
  onPrint: () => void;
  isLoading?: boolean;
  canFinalize?: boolean;
}

function fmt(n: number): string {
  return n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export function ReconcileGrid({
  opening,
  cashSales,
  counted,
  onCountedChange,
  onFinalize,
  onPrint,
  isLoading = false,
  canFinalize = true,
}: ReconcileGridProps) {
  const expected = opening + cashSales;
  const countedNum = parseFloat(counted || "0");
  const variance = countedNum - expected;
  const absVar = Math.abs(variance);
  const varTone =
    absVar < 1 ? "text-green-400" : absVar < 20 ? "text-amber-400" : "text-destructive";

  return (
    <div
      className="flex flex-col gap-3 rounded-xl border border-border bg-surface/50 p-4"
      data-testid="reconcile-grid"
    >
      <ReconRow label="Opening float" value={fmt(opening)} />
      <ReconRow label="Cash sales" value={`+ ${fmt(cashSales)}`} tone="accent" />
      <div className="my-0.5 h-px bg-border" />
      <ReconRow label="Expected cash" value={fmt(expected)} bold />

      <div className="mt-1 flex flex-col gap-2 rounded-lg border border-border bg-background/50 p-3">
        <label className="flex flex-col gap-1.5">
          <span className="font-mono text-[10px] font-bold uppercase tracking-[0.2em] text-text-secondary">
            Counted cash
          </span>
          <input
            type="text"
            inputMode="decimal"
            value={counted}
            onChange={(e) => onCountedChange(e.target.value.replace(/[^0-9.]/g, ""))}
            className={cn(
              "w-full rounded-md border border-border bg-background/70 px-3 py-2.5 font-mono text-2xl font-bold tabular-nums text-text-primary",
              "focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent",
            )}
            placeholder="0.00"
            data-testid="counted-cash-input"
          />
        </label>
        <div className="flex items-center justify-between pt-1">
          <span className="font-mono text-[10px] font-bold uppercase tracking-[0.2em] text-text-secondary">
            Variance
          </span>
          <span
            className={cn("font-mono text-2xl font-bold tabular-nums", varTone)}
            data-testid="variance-display"
          >
            {variance >= 0 ? "+" : "−"}
            {fmt(absVar)}
          </span>
        </div>
      </div>

      <div className="mt-1 flex gap-2">
        <button
          type="button"
          onClick={onPrint}
          data-testid="shift-print-button"
          className={cn(
            "flex flex-1 items-center justify-center gap-2 rounded-lg border border-border bg-transparent py-3 text-xs font-semibold text-text-secondary transition-colors",
            "hover:bg-surface-raised",
          )}
        >
          <Printer className="h-3.5 w-3.5" />
          Print receipt
          <kbd className="inline-flex h-4 min-w-[14px] items-center justify-center rounded border border-border px-1 font-mono text-[9px]">
            F4
          </kbd>
        </button>
        <button
          type="button"
          onClick={onFinalize}
          disabled={!canFinalize || isLoading}
          data-testid="shift-finalize-button"
          className={cn(
            "flex flex-[2] items-center justify-center gap-2.5 rounded-lg py-3 text-sm font-bold transition-colors",
            "bg-gradient-to-b from-accent to-accent/80 text-accent-foreground",
            "shadow-[0_0_20px_rgba(0,199,242,0.35)]",
            "disabled:pointer-events-none disabled:opacity-40",
          )}
        >
          {isLoading ? "Closing…" : "Finalize shift"}
          <kbd className="inline-flex h-4 min-w-[22px] items-center justify-center rounded border border-current/30 px-1 font-mono text-[9px]">
            Enter
          </kbd>
        </button>
      </div>
    </div>
  );
}

interface ReconRowProps {
  label: string;
  value: string;
  tone?: "accent";
  bold?: boolean;
}

function ReconRow({ label, value, tone, bold }: ReconRowProps) {
  return (
    <div className="flex items-baseline justify-between">
      <span className="font-mono text-[11px] font-semibold uppercase tracking-[0.16em] text-text-secondary">
        {label}
      </span>
      <span
        className={cn(
          "font-mono tabular-nums",
          bold ? "text-[22px] font-bold" : "text-base font-semibold",
          tone === "accent" ? "text-accent" : "text-text-primary",
        )}
      >
        {value}
      </span>
    </div>
  );
}
