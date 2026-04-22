"use client";

import { Minus, Plus } from "lucide-react";
import { cn } from "@/lib/utils";
import { StockPill } from "./StockPill";
import type { DrugRow, SortKey, SortState } from "./types";

interface Props {
  rows: DrugRow[];
  activeIdx: number;
  onActivateIdx: (idx: number) => void;
  qtyFor: (code: string) => number;
  onQtyChange: (code: string, qty: number) => void;
  onAdd: (row: DrugRow, qty?: number) => void;
  sort: SortState;
  onSortToggle: (key: SortKey) => void;
}

export function DrugsTable({
  rows,
  activeIdx,
  onActivateIdx,
  qtyFor,
  onQtyChange,
  onAdd,
  sort,
  onSortToggle,
}: Props) {
  return (
    <div
      className={cn(
        "flex min-h-0 flex-1 flex-col overflow-hidden rounded-xl",
        "border border-border bg-[rgba(8,24,38,0.5)]",
      )}
    >
      <div
        className={cn(
          "grid items-center gap-2 border-b border-border px-4 py-2.5",
          "bg-gradient-to-b from-white/[0.03] to-transparent",
          "grid-cols-[1.6fr_130px_100px_100px_132px_76px]",
        )}
      >
        <SortHeader
          label="Item"
          k="drug_name"
          sort={sort}
          onClick={() => onSortToggle("drug_name")}
        />
        <SortHeader
          label="Barcode / SKU"
          k="drug_code"
          sort={sort}
          onClick={() => onSortToggle("drug_code")}
        />
        <SortHeader
          label="On hand"
          k="stock_available"
          sort={sort}
          onClick={() => onSortToggle("stock_available")}
          align="end"
        />
        <SortHeader
          label="Price"
          k="unit_price"
          sort={sort}
          onClick={() => onSortToggle("unit_price")}
          align="end"
        />
        <div className="text-center font-mono text-[9.5px] font-bold uppercase tracking-[0.2em] text-text-secondary">
          Add qty
        </div>
        <div />
      </div>

      <div className="flex-1 overflow-y-auto" role="rowgroup" data-testid="drugs-table">
        {rows.length === 0 && (
          <div className="flex h-full min-h-[180px] flex-col items-center justify-center gap-2 text-text-secondary">
            <div className="font-serif text-lg italic text-text-primary">No matches</div>
            <div className="text-xs">Try a different query</div>
          </div>
        )}

        {rows.map((row, idx) => {
          const active = idx === activeIdx;
          const disabled = row.stock_tag === "out";
          const qty = qtyFor(row.drug_code);
          return (
            <div
              key={row.drug_code}
              role="row"
              data-testid={`drug-row-${row.drug_code}`}
              aria-selected={active}
              onClick={() => onActivateIdx(idx)}
              className={cn(
                "grid cursor-pointer items-center gap-2 border-b border-border",
                "grid-cols-[1.6fr_130px_100px_100px_132px_76px]",
                "px-4 py-2.5 transition-colors",
                active && "bg-cyan-400/5",
                active && "border-s-[3px] border-s-cyan-400 ps-[13px]",
                !active && "border-s-[3px] border-s-transparent",
                disabled && "opacity-70",
              )}
            >
              <div className="flex min-w-0 flex-col gap-0.5">
                <div className="flex min-w-0 items-center gap-1.5">
                  <span className="truncate text-sm font-semibold">{row.drug_name}</span>
                  {row.is_controlled && (
                    <span className="shrink-0 rounded bg-purple-500/20 px-1 py-[1px] font-mono text-[8.5px] font-bold uppercase tracking-[0.18em] text-purple-300">
                      Rx
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2 text-[10.5px] text-text-secondary">
                  <span className="font-mono uppercase tracking-[0.1em]">
                    {row.drug_brand ?? "—"}
                  </span>
                </div>
              </div>

              <div className="font-mono text-[11px] text-text-secondary tabular-nums">
                {row.drug_code}
              </div>

              <StockPill qty={row.stock_available} tag={row.stock_tag} />

              <div className="text-end font-mono text-[13px] font-semibold tabular-nums">
                {formatEGP(row.unit_price)}
              </div>

              <div className="flex items-center justify-center gap-1">
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    onQtyChange(row.drug_code, qty - 1);
                  }}
                  disabled={disabled}
                  aria-label={`Decrease quantity for ${row.drug_name}`}
                  className={cn(
                    "flex h-7 w-7 items-center justify-center rounded-md border border-border",
                    "bg-white/[0.05] text-text-primary",
                    "disabled:cursor-not-allowed disabled:opacity-50",
                  )}
                >
                  <Minus className="h-3.5 w-3.5" />
                </button>
                <input
                  type="number"
                  min={1}
                  max={99}
                  value={qty}
                  onChange={(e) => onQtyChange(row.drug_code, parseInt(e.target.value || "1", 10))}
                  onClick={(e) => e.stopPropagation()}
                  disabled={disabled}
                  data-testid={`qty-input-${row.drug_code}`}
                  className={cn(
                    "h-7 w-10 rounded-md border border-border bg-[rgba(8,24,38,0.7)]",
                    "text-center font-mono text-[13px] font-semibold tabular-nums text-text-primary",
                    "focus:outline-none focus:ring-1 focus:ring-cyan-400",
                    "disabled:cursor-not-allowed disabled:opacity-50",
                  )}
                />
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    onQtyChange(row.drug_code, qty + 1);
                  }}
                  disabled={disabled}
                  aria-label={`Increase quantity for ${row.drug_name}`}
                  className={cn(
                    "flex h-7 w-7 items-center justify-center rounded-md border",
                    disabled
                      ? "border-border bg-white/[0.03] text-text-secondary"
                      : "border-cyan-400/30 bg-cyan-400/10 text-cyan-300",
                    "disabled:cursor-not-allowed disabled:opacity-50",
                  )}
                >
                  <Plus className="h-3.5 w-3.5" />
                </button>
              </div>

              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  onAdd(row);
                }}
                disabled={disabled}
                data-testid={`add-button-${row.drug_code}`}
                aria-label={
                  disabled ? "Out of stock" : `Add ${qty} × ${row.drug_name} to cart`
                }
                className={cn(
                  "rounded-md px-2.5 py-1.5 text-xs font-bold",
                  "transition-transform active:scale-[0.97]",
                  disabled
                    ? "cursor-not-allowed border border-border bg-white/[0.04] text-text-secondary"
                    : "bg-gradient-to-b from-cyan-300 to-cyan-600 text-[#021018] shadow-[0_0_12px_rgba(0,199,242,0.25),inset_0_1px_0_rgba(255,255,255,0.3)]",
                )}
              >
                {disabled ? "Out" : "Add"}
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}

interface SortHeaderProps {
  label: string;
  k: SortKey;
  sort: SortState;
  onClick: () => void;
  align?: "start" | "end";
}

function SortHeader({ label, k, sort, onClick, align = "start" }: SortHeaderProps) {
  const active = sort.key === k;
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "flex items-center font-mono text-[9.5px] font-bold uppercase tracking-[0.2em]",
        "text-text-secondary hover:text-text-primary",
        align === "end" ? "justify-end text-end" : "justify-start text-start",
      )}
    >
      {label}
      {active && <span className="ms-1 text-cyan-300">{sort.dir === "asc" ? "↑" : "↓"}</span>}
    </button>
  );
}

function formatEGP(value: number): string {
  return `EGP ${value.toFixed(2)}`;
}
