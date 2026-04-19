import { cn } from "@/lib/utils";
import type { DrugRow } from "./types";

interface Props {
  row: DrugRow | null;
  qty: number;
  onAdd: (row: DrugRow, qty: number) => void;
}

export function FocusedDrug({ row, qty, onAdd }: Props) {
  if (!row) {
    return (
      <div className="rounded-xl border border-border bg-[rgba(8,24,38,0.6)] px-3.5 py-3 text-xs text-text-secondary">
        Select a row to preview details.
      </div>
    );
  }

  const disabled = row.stock_tag === "out";
  return (
    <div
      className={cn(
        "flex flex-col gap-2 rounded-xl border border-border",
        "bg-[rgba(8,24,38,0.6)] px-3.5 py-3",
      )}
      data-testid="focused-drug"
    >
      <div className="font-mono text-[9.5px] font-bold uppercase tracking-[0.22em] text-text-secondary">
        Selected
      </div>
      <div className="text-sm font-semibold leading-tight">{row.drug_name}</div>
      <div className="grid grid-cols-2 gap-1.5 text-[11px]">
        <Detail label="SKU" value={row.drug_code} mono />
        <Detail label="Brand" value={row.drug_brand ?? "—"} />
        <Detail label="On hand" value={row.stock_tag === "unknown" ? "—" : String(row.stock_available)} mono />
        <Detail label="Price" value={formatEGP(row.unit_price)} mono />
      </div>

      <button
        type="button"
        onClick={() => onAdd(row, qty)}
        disabled={disabled}
        data-testid="focused-add-button"
        aria-label={
          disabled ? "Unavailable — out of stock" : `Add ${qty} × ${row.drug_name} to cart`
        }
        className={cn(
          "mt-1 grid grid-cols-[auto_1fr_auto] items-center gap-2.5 rounded-lg px-3 py-2.5",
          "text-sm font-bold",
          disabled
            ? "cursor-not-allowed border border-border bg-white/[0.04] text-text-secondary"
            : "bg-gradient-to-b from-cyan-300 to-cyan-600 text-[#021018] shadow-[0_0_18px_rgba(0,199,242,0.25),inset_0_1px_0_rgba(255,255,255,0.3)]",
        )}
      >
        <span>{disabled ? "Unavailable" : "Add to cart"}</span>
        <span className="font-mono text-sm tabular-nums">×{qty}</span>
        <span className="font-mono text-[13px] tabular-nums">
          {formatEGP(row.unit_price * qty)}
        </span>
      </button>
    </div>
  );
}

function Detail({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div>
      <div className="font-mono text-[9px] uppercase tracking-[0.16em] text-text-secondary">
        {label}
      </div>
      <div
        className={cn(
          "mt-0.5 text-[12px] font-semibold text-text-primary",
          mono && "font-mono tabular-nums",
        )}
      >
        {value}
      </div>
    </div>
  );
}

function formatEGP(value: number): string {
  return `EGP ${value.toFixed(2)}`;
}
