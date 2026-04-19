"use client";

import { useEffect, useMemo, useRef } from "react";
import { Printer, X } from "lucide-react";
import { cn } from "@/lib/utils";

/** Drug row used by the stocktaking worksheet. Narrow subset of
 * `DrugRow` so the modal can be reused from any page that knows an
 * inventory slice (currently only `/drugs`). */
export interface StocktakingRow {
  drug_code: string;
  drug_name: string;
  drug_brand?: string | null;
  stock_available: number;
  unit_price: number;
  /** Optional — empty string renders as "—". */
  shelf?: string | null;
  batch_number?: string | null;
  expiry_date?: string | null;
}

export interface StocktakingModalProps {
  open: boolean;
  onClose: () => void;
  rows: StocktakingRow[];
  /** Document number — STK-YYMMDD-NN. Minted from today if omitted. */
  docNumber?: string | null;
  /** Branch name for the letterhead. */
  branchName?: string | null;
  /** Counter/witness names to prefill. Optional. */
  prefilledCounter?: string | null;
  prefilledShift?: string | null;
}

function fmtEGP(n: number): string {
  return (
    "EGP " +
    n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  );
}

function mintDocNumber(): string {
  const d = new Date();
  const yymmdd = d.toISOString().slice(2, 10).replace(/-/g, "");
  return `STK-${yymmdd}-01`;
}

function fmtDate(d: Date): string {
  return d.toLocaleDateString("en-GB");
}

/**
 * StocktakingModal — printable A4 blank count worksheet per POS design PR 4.
 *
 * Rows come from the caller's current inventory slice. Counted / Δ / ✓
 * columns are intentionally blank for hand-filling (the whole point of
 * this sheet is that the cashier counts shelves by hand and reconciles
 * against the system qty).
 */
export function StocktakingModal({
  open,
  onClose,
  rows,
  docNumber,
  branchName,
  prefilledCounter,
  prefilledShift,
}: StocktakingModalProps) {
  const dialogRef = useRef<HTMLDivElement>(null);

  const today = useMemo(() => fmtDate(new Date()), []);
  const doc = useMemo(() => docNumber ?? mintDocNumber(), [docNumber]);

  const sortedRows = useMemo(
    () =>
      [...rows].sort((a, b) =>
        (a.shelf ?? "").localeCompare(b.shelf ?? "", undefined, { sensitivity: "base" }),
      ),
    [rows],
  );

  const totals = useMemo(() => {
    const skuCount = sortedRows.length;
    const systemQty = sortedRows.reduce((s, r) => s + (r.stock_available || 0), 0);
    const systemValue = sortedRows.reduce(
      (s, r) => s + (r.stock_available || 0) * r.unit_price,
      0,
    );
    return { skuCount, systemQty, systemValue };
  }, [sortedRows]);

  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      ref={dialogRef}
      role="dialog"
      aria-modal="true"
      aria-label="Stocktaking worksheet"
      data-testid="stocktaking-modal"
      className="pos-stk-root fixed inset-0 z-[200] grid place-items-center bg-black/70 p-5 backdrop-blur-md"
      onClick={(e) => {
        if (e.target === dialogRef.current) onClose();
      }}
    >
      <style
        dangerouslySetInnerHTML={{
          __html: `
            @media print {
              html, body { background: #fff !important; }
              body > *:not(.pos-stk-root) { display: none !important; }
              .pos-stk-root { position: static !important; background: #fff !important; padding: 0 !important; backdrop-filter: none !important; }
              .pos-stk-chrome { display: none !important; }
              .pos-stk-paper { box-shadow: none !important; border: none !important; max-width: none !important; width: 100% !important; max-height: none !important; overflow: visible !important; color: #000 !important; background: #fff !important; }
              .pos-stk-paper * { color: #000 !important; border-color: #000 !important; }
              .pos-stk-paper .ink-muted { color: #555 !important; }
              .pos-stk-paper .box { background: #fff !important; border: 1px solid #000 !important; }
              .pos-stk-paper .row-alt:nth-child(even) { background: #f4f4f4 !important; }
              @page { size: A4; margin: 12mm; }
            }
          `,
        }}
      />

      <div
        className="pos-stk-chrome absolute end-4 top-4 z-[2] flex gap-2"
        data-testid="stocktaking-chrome"
      >
        <button
          type="button"
          onClick={() => window.print()}
          data-testid="stocktaking-print-button"
          className={cn(
            "flex items-center gap-2 rounded-lg px-3.5 py-2 text-xs font-bold",
            "bg-gradient-to-b from-cyan-300 to-cyan-600 text-[#021018]",
            "shadow-[0_0_16px_rgba(0,199,242,0.35)]",
          )}
        >
          <Printer className="h-4 w-4" />
          Print
        </button>
        <button
          type="button"
          onClick={onClose}
          data-testid="stocktaking-close-button"
          aria-label="Close stocktaking sheet"
          className={cn(
            "flex items-center gap-1.5 rounded-lg border border-border bg-white/[0.06] px-3.5 py-2",
            "text-xs font-semibold text-text-secondary",
          )}
        >
          <X className="h-3.5 w-3.5" />
          Close (Esc)
        </button>
      </div>

      <div
        className="pos-stk-paper w-[min(900px,100%)] max-h-[92vh] overflow-auto rounded-md px-8 py-7 shadow-[0_30px_80px_rgba(0,0,0,0.6)]"
        style={{ background: "#fbfaf7", color: "#0b1a29", fontFamily: "Inter, sans-serif" }}
      >
        <div
          className="mb-4 grid grid-cols-[1fr_auto] items-end pb-3"
          style={{ borderBottom: "2px solid #0b1a29" }}
        >
          <div>
            <div
              className="text-[22px] font-semibold italic"
              style={{ fontFamily: "Fraunces, serif" }}
              data-testid="stocktaking-letterhead"
            >
              {branchName ?? "DataPulse Pharmacy — Maadi"}
            </div>
            <div className="ink-muted mt-0.5 text-[11px]" style={{ color: "#555" }}>
              12 Sobhi Saleh St · Maadi · Cairo · CR 428893
            </div>
          </div>
          <div className="text-right text-[11px]">
            <div
              className="text-[12px] font-bold"
              style={{ fontFamily: "JetBrains Mono, monospace" }}
              data-testid="stocktaking-doc-number"
            >
              {doc}
            </div>
            <div className="ink-muted" style={{ color: "#555" }}>
              {today}
            </div>
          </div>
        </div>

        <div className="mb-4 flex items-baseline justify-between">
          <h2
            className="m-0 text-[28px] font-medium italic"
            style={{ fontFamily: "Fraunces, serif", letterSpacing: "-0.02em" }}
          >
            Stocktaking Worksheet
          </h2>
          <div className="ink-muted text-[11px]" style={{ color: "#555" }}>
            Blank sheet for manual count · return to supervisor signed
          </div>
        </div>

        <div
          className="box mb-[18px] grid grid-cols-3 text-[11px]"
          style={{ border: "1px solid #0b1a29" }}
        >
          <MetaCell label="Counted by" prefilled={prefilledCounter ?? ""} />
          <MetaCell label="Witness" />
          <MetaCell label="Date / Time" prefilled={today} />
          <MetaCell label="Aisle / Section" />
          <MetaCell label="Temperature (°C)" />
          <MetaCell label="Shift #" prefilled={prefilledShift ?? "AM-03"} />
        </div>

        <table className="w-full border-collapse text-[10.5px]">
          <thead>
            <tr style={{ background: "#0b1a29", color: "#fbfaf7" }}>
              <StkTh width={28}>#</StkTh>
              <StkTh width={60} align="start">
                Shelf
              </StkTh>
              <StkTh width={120} align="start">
                Barcode
              </StkTh>
              <StkTh align="start">Item</StkTh>
              <StkTh width={70} align="start">
                Batch
              </StkTh>
              <StkTh width={60} align="start">
                Expiry
              </StkTh>
              <StkTh width={48} align="end">
                System
              </StkTh>
              <StkTh width={70} align="center">
                Counted
              </StkTh>
              <StkTh width={50} align="end">
                Δ
              </StkTh>
              <StkTh width={40} align="center">
                ✓
              </StkTh>
            </tr>
          </thead>
          <tbody data-testid="stocktaking-body">
            {sortedRows.length === 0 && (
              <tr>
                <StkTd colSpan={10} align="center" style={{ padding: "14px 0", color: "#888" }}>
                  No items to count — catalog is empty.
                </StkTd>
              </tr>
            )}
            {sortedRows.map((r, i) => (
              <tr
                key={r.drug_code}
                className="row-alt"
                data-testid={`stocktaking-row-${r.drug_code}`}
                style={{
                  borderBottom: "0.5px solid #bbb",
                  background: i % 2 === 1 ? "rgba(11,26,41,0.04)" : "transparent",
                }}
              >
                <StkTd align="center" mono>
                  {String(i + 1).padStart(2, "0")}
                </StkTd>
                <StkTd mono>{r.shelf || "—"}</StkTd>
                <StkTd mono style={{ fontSize: 10 }}>
                  {r.drug_code}
                </StkTd>
                <StkTd>
                  <div className="font-semibold">{r.drug_name}</div>
                  {r.drug_brand && (
                    <div
                      className="ink-muted text-[9.5px]"
                      style={{ color: "#555" }}
                    >
                      {r.drug_brand}
                    </div>
                  )}
                </StkTd>
                <StkTd mono>{r.batch_number || "—"}</StkTd>
                <StkTd mono>{r.expiry_date || "—"}</StkTd>
                <StkTd align="end" mono>
                  <b>{r.stock_available}</b>
                </StkTd>
                <StkTd
                  align="center"
                  style={{
                    height: 26,
                    borderInline: "1px solid #0b1a29",
                    background: "#fff",
                  }}
                />
                <StkTd
                  align="end"
                  style={{ borderInline: "1px solid #0b1a29", background: "#fff" }}
                />
                <StkTd
                  align="center"
                  style={{ borderInline: "1px solid #0b1a29", background: "#fff" }}
                />
              </tr>
            ))}
            <tr style={{ borderTop: "2px solid #0b1a29" }}>
              <StkTd />
              <StkTd colSpan={5} style={{ fontWeight: 700 }}>
                Totals — {totals.skuCount} SKUs · system value {fmtEGP(totals.systemValue)}
              </StkTd>
              <StkTd align="end" mono>
                <b>{totals.systemQty}</b>
              </StkTd>
              <StkTd />
              <StkTd />
              <StkTd />
            </tr>
          </tbody>
        </table>

        <div className="mt-6 grid grid-cols-[1fr_1fr] gap-6">
          <div className="text-[10px] leading-[1.55]">
            <div
              className="mb-1 font-bold"
              style={{ color: "#0b1a29" }}
            >
              Counting instructions
            </div>
            <div style={{ color: "#555" }}>
              1. Count each SKU aloud with witness present. 2. Record physical count in
              &quot;Counted&quot;. 3. Compute Δ (Counted − System). 4. Tick ✓ once reconciled.
              5. Submit to supervisor at least one hour before shift close.
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <SignatureLine label="Counter signature" />
            <SignatureLine label="Supervisor signature" />
          </div>
        </div>

        <div
          className="ink-muted mt-6 flex justify-between border-t pt-2.5 text-[9.5px]"
          style={{ borderTopStyle: "dashed", borderTopColor: "#888" }}
        >
          <span style={{ color: "#555" }}>DataPulse POS · {doc}</span>
          <span style={{ color: "#555", fontFamily: "JetBrains Mono, monospace" }}>p 1/1</span>
        </div>
      </div>
    </div>
  );
}

function MetaCell({ label, prefilled }: { label: string; prefilled?: string }) {
  return (
    <div
      className="px-2.5 py-2"
      style={{
        borderInline: "0.5px solid #0b1a29",
        borderBlock: "0.5px solid #0b1a29",
      }}
    >
      <div
        className="mb-1 text-[9px] font-bold uppercase tracking-[0.14em]"
        style={{ color: "#555" }}
      >
        {label}
      </div>
      <div
        className="text-[11px] font-semibold"
        style={{
          minHeight: 16,
          fontFamily: "JetBrains Mono, monospace",
          borderBottom: "1px solid #0b1a29",
        }}
      >
        {prefilled || ""}
      </div>
    </div>
  );
}

interface StkThProps {
  children: React.ReactNode;
  width?: number;
  align?: "start" | "center" | "end";
}
function StkTh({ children, width, align = "center" }: StkThProps) {
  return (
    <th
      className="text-[9.5px] font-bold uppercase tracking-[0.16em]"
      style={{
        padding: "6px 6px",
        width,
        textAlign: align,
        border: "0.5px solid #0b1a29",
      }}
    >
      {children}
    </th>
  );
}

interface StkTdProps {
  children?: React.ReactNode;
  align?: "start" | "center" | "end";
  mono?: boolean;
  style?: React.CSSProperties;
  colSpan?: number;
}
function StkTd({ children, align = "start", mono, style, colSpan }: StkTdProps) {
  return (
    <td
      colSpan={colSpan}
      style={{
        padding: "5px 6px",
        textAlign: align,
        fontFamily: mono ? "JetBrains Mono, monospace" : "inherit",
        fontSize: mono ? 10 : 10.5,
        verticalAlign: "middle",
        ...style,
      }}
    >
      {children}
    </td>
  );
}

function SignatureLine({ label }: { label: string }) {
  return (
    <div>
      <div style={{ borderBottom: "1px solid #0b1a29", minHeight: 36 }} />
      <div
        className="mt-1 text-[9.5px] uppercase tracking-[0.12em]"
        style={{ color: "#555" }}
      >
        {label}
      </div>
    </div>
  );
}
