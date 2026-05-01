import { useEffect, useMemo } from "react";
import { Printer, X } from "lucide-react";
import type { DrugRow } from "@pos/components/drugs/types";

/**
 * StocktakingModal — printable physical-count worksheet (A4).
 *
 * Design source: docs/design/pos-terminal/frames/pos/stocktaking.jsx
 * Triggered from /drugs via F6 or the toolbar button. Renders rows blank
 * in the "Counted / Δ / ✓" columns for manual filling, then printed.
 */
export interface StocktakingModalProps {
  open: boolean;
  onClose: () => void;
  rows: DrugRow[];
  branchName: string;
  branchAddress: string;
  crNumber: string;
  shiftNumber?: string;
}

function fmtEgp(n: number): string {
  return (
    "EGP " +
    n.toLocaleString("en-US", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })
  );
}

function formatDocNo(date: Date): string {
  return "STK-" + date.toISOString().slice(2, 10).replaceAll("-", "") + "-01";
}

export function StocktakingModal({
  open,
  onClose,
  rows,
  branchName,
  branchAddress,
  crNumber,
  shiftNumber,
}: StocktakingModalProps) {
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

  const today = useMemo(() => new Date(), []);
  const todayStr = today.toLocaleDateString("en-GB");
  const docNo = useMemo(() => formatDocNo(today), [today]);

  const totals = useMemo(() => {
    const totalSystem = rows.reduce((s, r) => s + (r.stock_available ?? 0), 0);
    const totalValue = rows.reduce(
      (s, r) => s + (r.stock_available ?? 0) * r.unit_price,
      0,
    );
    return { totalSystem, totalValue };
  }, [rows]);

  if (!open) return null;

  return (
    <div
      className="pos-print-root fixed inset-0 z-[200] grid place-items-center p-5"
      style={{
        background: "rgba(2,10,18,0.72)",
        backdropFilter: "blur(10px)",
      }}
      data-testid="pos-stocktaking-modal"
      role="dialog"
      aria-modal="true"
      aria-labelledby="pos-stocktaking-title"
    >
      {/* Chrome */}
      <div
        className="pos-print-chrome absolute right-4 top-4 z-[2] flex gap-2"
        data-testid="pos-stocktaking-chrome"
      >
        <button
          type="button"
          onClick={() => window.print()}
          data-testid="pos-stocktaking-print-button"
          className="flex items-center gap-2 rounded-lg border-0 px-3.5 py-[9px] text-[13px] font-bold"
          style={{
            background: "linear-gradient(180deg, #5cdfff, #00a6cc)",
            color: "#021018",
            boxShadow: "0 0 16px rgba(0,199,242,0.35)",
          }}
        >
          <Printer className="h-4 w-4" />
          Print
        </button>
        <button
          type="button"
          onClick={onClose}
          data-testid="pos-stocktaking-close-button"
          className="flex items-center gap-2 rounded-lg border px-3.5 py-[9px] text-[13px] font-semibold"
          style={{
            background: "rgba(255,255,255,0.06)",
            color: "var(--pos-ink-2, #b8c0cc)",
            borderColor: "var(--pos-line, rgba(255,255,255,0.12))",
          }}
        >
          <X className="h-4 w-4" />
          Close (Esc)
        </button>
      </div>

      {/* Paper */}
      <div
        className="pos-print-paper overflow-auto rounded-[6px]"
        style={{
          background: "var(--pos-paper, #fbfaf7)",
          color: "var(--pos-paper-ink, #0b1a29)",
          width: "min(900px, 100%)",
          maxHeight: "92vh",
          boxShadow: "0 30px 80px rgba(0,0,0,0.6)",
          padding: "28px 32px",
          fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif",
        }}
      >
        {/* Letterhead */}
        <div
          className="mb-4 grid items-end"
          style={{
            gridTemplateColumns: "1fr auto",
            borderBottom: "2px solid var(--pos-paper-ink, #0b1a29)",
            paddingBottom: 12,
          }}
        >
          <div>
            <div
              style={{
                fontFamily: "var(--font-fraunces), Fraunces, serif",
                fontStyle: "italic",
                fontSize: 22,
                fontWeight: 600,
              }}
            >
              {branchName}
            </div>
            <div
              className="pos-print-muted"
              style={{
                fontSize: 11,
                marginTop: 2,
                color: "var(--pos-paper-ink-muted, #555)",
              }}
            >
              {branchAddress} · CR {crNumber}
            </div>
          </div>
          <div className="text-right" style={{ fontSize: 11 }}>
            <div
              data-testid="pos-stocktaking-doc-no"
              style={{
                fontFamily:
                  "var(--font-jetbrains-mono), JetBrains Mono, monospace",
                fontWeight: 700,
                fontSize: 12,
              }}
            >
              {docNo}
            </div>
            <div
              className="pos-print-muted"
              style={{ color: "var(--pos-paper-ink-muted, #555)" }}
            >
              {todayStr}
            </div>
          </div>
        </div>

        {/* Title */}
        <div className="mb-4 flex items-baseline justify-between">
          <h2
            id="pos-stocktaking-title"
            className="m-0"
            style={{
              fontFamily: "var(--font-fraunces), Fraunces, serif",
              fontStyle: "italic",
              fontWeight: 500,
              fontSize: 28,
              letterSpacing: "-0.02em",
            }}
          >
            Stocktaking Worksheet
          </h2>
          <div
            className="pos-print-muted"
            style={{ fontSize: 11, color: "var(--pos-paper-ink-muted, #555)" }}
          >
            Blank sheet for manual count · return to supervisor signed
          </div>
        </div>

        {/* Meta grid */}
        <div
          className="mb-4 grid"
          style={{
            gridTemplateColumns: "1fr 1fr 1fr",
            border: "1px solid var(--pos-paper-ink, #0b1a29)",
            fontSize: 11,
          }}
        >
          <MetaCell label="Counted by" />
          <MetaCell label="Witness" />
          <MetaCell label="Date / Time" prefilled={todayStr} />
          <MetaCell label="Aisle / Section" />
          <MetaCell label="Temperature (°C)" />
          <MetaCell label="Shift #" prefilled={shiftNumber ?? "AM-03"} />
        </div>

        {/* Table */}
        <table
          className="w-full"
          style={{ borderCollapse: "collapse", fontSize: 10.5 }}
          data-testid="pos-stocktaking-table"
        >
          <thead>
            <tr
              style={{
                background: "var(--pos-paper-ink, #0b1a29)",
                color: "var(--pos-paper, #fbfaf7)",
              }}
            >
              <StkTh w={28}>#</StkTh>
              <StkTh w={60} align="start">
                Shelf
              </StkTh>
              <StkTh w={120} align="start">
                Barcode
              </StkTh>
              <StkTh align="start">Item</StkTh>
              <StkTh w={70} align="start">
                Batch
              </StkTh>
              <StkTh w={60} align="start">
                Expiry
              </StkTh>
              <StkTh w={48} align="end">
                System
              </StkTh>
              <StkTh w={70} align="center">
                Counted
              </StkTh>
              <StkTh w={50} align="end">
                Δ
              </StkTh>
              <StkTh w={40} align="center">
                ✓
              </StkTh>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr
                key={r.drug_code}
                className="pos-print-zebra"
                style={{
                  borderBottom: "0.5px solid var(--pos-paper-rule, #bbb)",
                  background:
                    i % 2 === 1 ? "rgba(11,26,41,0.04)" : "transparent",
                }}
              >
                <StkTd align="center" mono>
                  {String(i + 1).padStart(2, "0")}
                </StkTd>
                <StkTd mono>—</StkTd>
                <StkTd mono style={{ fontSize: 10 }}>
                  {r.drug_code}
                </StkTd>
                <StkTd>
                  <div style={{ fontWeight: 600 }}>{r.drug_name}</div>
                  {r.drug_brand && (
                    <div
                      className="pos-print-muted"
                      style={{
                        fontSize: 9.5,
                        color: "var(--pos-paper-ink-muted, #555)",
                      }}
                    >
                      {r.drug_brand}
                    </div>
                  )}
                </StkTd>
                <StkTd mono>—</StkTd>
                <StkTd mono>—</StkTd>
                <StkTd align="end" mono>
                  <b>{r.stock_available ?? 0}</b>
                </StkTd>
                <StkTd
                  align="center"
                  className="pos-print-field-cell"
                  style={{
                    height: 26,
                    borderInline: "1px solid var(--pos-paper-ink, #0b1a29)",
                    background: "#fff",
                  }}
                />
                <StkTd
                  align="end"
                  className="pos-print-field-cell"
                  style={{
                    borderInline: "1px solid var(--pos-paper-ink, #0b1a29)",
                    background: "#fff",
                  }}
                />
                <StkTd
                  align="center"
                  className="pos-print-field-cell"
                  style={{
                    borderInline: "1px solid var(--pos-paper-ink, #0b1a29)",
                    background: "#fff",
                  }}
                />
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <StkTd
                  colSpan={10}
                  align="center"
                  style={{ padding: "24px 0", color: "#888" }}
                >
                  No products to count yet — load the catalog first.
                </StkTd>
              </tr>
            )}
            {/* Totals */}
            {rows.length > 0 && (
              <tr style={{ borderTop: "2px solid var(--pos-paper-ink, #0b1a29)" }}>
                <StkTd />
                <StkTd colSpan={5} style={{ fontWeight: 700 }}>
                  Totals — {rows.length} SKUs · system value{" "}
                  {fmtEgp(totals.totalValue)}
                </StkTd>
                <StkTd align="end" mono testId="pos-stocktaking-total-system">
                  <b>{totals.totalSystem}</b>
                </StkTd>
                <StkTd />
                <StkTd />
                <StkTd />
              </tr>
            )}
          </tbody>
        </table>

        {/* Instructions + signatures */}
        <div
          className="mt-6 grid gap-6"
          style={{ gridTemplateColumns: "1fr 1fr" }}
        >
          <div
            className="pos-print-muted"
            style={{ fontSize: 10, lineHeight: 1.55 }}
          >
            <div
              style={{
                fontWeight: 700,
                color: "var(--pos-paper-ink, #0b1a29)",
                marginBottom: 4,
              }}
            >
              Counting instructions
            </div>
            <div style={{ color: "var(--pos-paper-ink-muted, #555)" }}>
              1. Count each SKU aloud with witness present. 2. Record physical
              count in &quot;Counted&quot;. 3. Compute Δ (Counted − System). 4.
              Tick ✓ once reconciled. 5. Submit to supervisor at least one hour
              before shift close.
            </div>
          </div>
          <div className="grid gap-4" style={{ gridTemplateColumns: "1fr 1fr" }}>
            <SignatureLine label="Counter signature" />
            <SignatureLine label="Supervisor signature" />
          </div>
        </div>

        {/* Footer */}
        <div
          className="pos-print-muted mt-6 flex justify-between pt-2.5"
          style={{
            borderTop: "1px dashed #888",
            fontSize: 9.5,
            color: "var(--pos-paper-ink-muted, #555)",
          }}
        >
          <span>DataPulse POS · {docNo}</span>
          <span
            style={{
              fontFamily:
                "var(--font-jetbrains-mono), JetBrains Mono, monospace",
            }}
          >
            p 1/1
          </span>
        </div>
      </div>
    </div>
  );
}

function MetaCell({ label, prefilled }: { label: string; prefilled?: string }) {
  return (
    <div
      style={{
        padding: "8px 10px",
        borderInline: "0.5px solid var(--pos-paper-ink, #0b1a29)",
        borderBlock: "0.5px solid var(--pos-paper-ink, #0b1a29)",
      }}
    >
      <div
        style={{
          fontSize: 9,
          letterSpacing: "0.14em",
          textTransform: "uppercase",
          fontWeight: 700,
          color: "var(--pos-paper-ink-muted, #555)",
          marginBottom: 4,
        }}
      >
        {label}
      </div>
      <div
        style={{
          minHeight: 16,
          fontFamily: "var(--font-jetbrains-mono), JetBrains Mono, monospace",
          fontSize: 11,
          fontWeight: 600,
          borderBottom: "1px solid var(--pos-paper-ink, #0b1a29)",
        }}
      >
        {prefilled ?? ""}
      </div>
    </div>
  );
}

function StkTh({
  children,
  w,
  align,
}: {
  children: React.ReactNode;
  w?: number;
  align?: "start" | "end" | "center";
}) {
  return (
    <th
      style={{
        padding: "6px 6px",
        width: w,
        fontSize: 9.5,
        letterSpacing: "0.16em",
        textTransform: "uppercase",
        textAlign: align ?? "center",
        fontWeight: 700,
        border: "0.5px solid var(--pos-paper-ink, #0b1a29)",
      }}
    >
      {children}
    </th>
  );
}

function StkTd({
  children,
  align,
  mono,
  style,
  colSpan,
  className,
  testId,
}: {
  children?: React.ReactNode;
  align?: "start" | "end" | "center";
  mono?: boolean;
  style?: React.CSSProperties;
  colSpan?: number;
  className?: string;
  testId?: string;
}) {
  return (
    <td
      colSpan={colSpan}
      className={className}
      data-testid={testId}
      style={{
        padding: "5px 6px",
        textAlign: align ?? "start",
        fontFamily: mono
          ? "var(--font-jetbrains-mono), JetBrains Mono, monospace"
          : "inherit",
        fontSize: mono ? 10 : 10.5,
        verticalAlign: "middle",
        ...(style ?? {}),
      }}
    >
      {children}
    </td>
  );
}

function SignatureLine({ label }: { label: string }) {
  return (
    <div>
      <div
        style={{
          borderBottom: "1px solid var(--pos-paper-ink, #0b1a29)",
          minHeight: 36,
        }}
      />
      <div
        style={{
          fontSize: 9.5,
          color: "var(--pos-paper-ink-muted, #555)",
          letterSpacing: "0.12em",
          textTransform: "uppercase",
          marginTop: 4,
        }}
      >
        {label}
      </div>
    </div>
  );
}
