"use client";

import { useEffect, useMemo, useRef } from "react";
import { Printer, X } from "lucide-react";
import { cn } from "@/lib/utils";
import type { PaymentMethod, PosCartItem } from "@/types/pos";

export interface InvoiceInsurance {
  name: string;
  coveragePct: number;
}

export interface InvoiceModalProps {
  open: boolean;
  onClose: () => void;
  items: PosCartItem[];
  /** Grand total inclusive of VAT — used to derive the VAT breakdown. */
  grandTotal: number;
  /** Already-computed item+voucher discount in EGP (display only). */
  discountTotal: number;
  /** Cart-level discount source ("voucher" or "promotion") for the Notes block. */
  discountSource?: "voucher" | "promotion" | null;
  /** Voucher code or promotion label to echo into the Notes block. */
  discountLabel?: string | null;
  insurance?: InvoiceInsurance | null;
  paymentMethod: PaymentMethod;
  cashierName?: string | null;
  branchName?: string | null;
  /** Invoice number from the backend (receipt_number). If missing we mint one. */
  receiptNumber?: string | null;
  createdAt?: string | null;
}

const PAYMENT_LABELS: Record<PaymentMethod, string> = {
  cash: "Cash",
  card: "Credit card",
  insurance: "Medical insurance",
  voucher: "Voucher",
  mixed: "Split payment",
};

function fmtEGP(n: number): string {
  return (
    "EGP " +
    n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  );
}

function mintInvoiceNumber(createdAt?: string | null): string {
  const d = createdAt ? new Date(createdAt) : new Date();
  const yymmdd = d.toISOString().slice(2, 10).replace(/-/g, "");
  const seq = String(Math.floor(Math.random() * 9000) + 1000);
  return `INV-${yymmdd}-${seq}`;
}

function fmtDate(d: Date): string {
  return d.toLocaleDateString("en-GB");
}
function fmtTime(d: Date): string {
  return d.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
}

/**
 * InvoiceModal — printable A4 tax invoice per POS design PR 4 (#468).
 *
 * VAT breakdown is computed inclusively from each line total (14% of the
 * EGP pharmacy VAT convention, regardless of the backend `tax_total` which
 * is currently 0 because pharmacy SKUs are zero-rated in the cart math).
 * The paper is always rendered in English/LTR — the Arabic variant in the
 * design frame was cosmetic only.
 */
export function InvoiceModal({
  open,
  onClose,
  items,
  grandTotal,
  discountTotal,
  discountSource = null,
  discountLabel = null,
  insurance = null,
  paymentMethod,
  cashierName,
  branchName,
  receiptNumber,
  createdAt,
}: InvoiceModalProps) {
  const dialogRef = useRef<HTMLDivElement>(null);

  const now = useMemo(() => (createdAt ? new Date(createdAt) : new Date()), [createdAt]);
  const invNo = useMemo(
    () => receiptNumber ?? mintInvoiceNumber(createdAt),
    [receiptNumber, createdAt],
  );
  const ref = useMemo(() => `REF-${Math.random().toString(36).slice(2, 10).toUpperCase()}`, []);

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

  const vatTotal = items.reduce((s, l) => {
    const lineIncl = l.line_total;
    return s + (lineIncl - lineIncl / 1.14);
  }, 0);
  const subtotalEx = items.reduce((s, l) => s + l.line_total / 1.14, 0);
  const insurerPays = insurance ? (grandTotal * insurance.coveragePct) / 100 : 0;
  const patientPays = insurance ? Math.max(0, grandTotal - insurerPays) : grandTotal;

  return (
    <div
      ref={dialogRef}
      role="dialog"
      aria-modal="true"
      aria-label="Tax invoice"
      data-testid="invoice-modal"
      className="pos-invoice-root fixed inset-0 z-[200] grid place-items-center bg-black/70 p-5 backdrop-blur-md"
      onClick={(e) => {
        if (e.target === dialogRef.current) onClose();
      }}
    >
      <style
        dangerouslySetInnerHTML={{
          __html: `
            @media print {
              html, body { background: #fff !important; }
              body > *:not(.pos-invoice-root) { display: none !important; }
              .pos-invoice-root { position: static !important; background: #fff !important; padding: 0 !important; backdrop-filter: none !important; }
              .pos-invoice-chrome { display: none !important; }
              .pos-invoice-paper { box-shadow: none !important; max-width: none !important; width: 100% !important; max-height: none !important; overflow: visible !important; }
              .pos-invoice-paper * { color: #000 !important; border-color: #000 !important; }
              .pos-invoice-paper .ink-muted { color: #555 !important; }
              .pos-invoice-paper .brand-ribbon { background: #0b1a29 !important; color: #fff !important; }
              .pos-invoice-paper .brand-ribbon * { color: #fff !important; }
              .pos-invoice-paper .row-alt:nth-child(even) { background: #f4f4f4 !important; }
              .pos-invoice-paper .totals-box { background: #f1ede4 !important; }
              .pos-invoice-paper .totals-box .grand { color: #0b1a29 !important; }
              @page { size: A4; margin: 12mm; }
            }
          `,
        }}
      />

      <div
        className="pos-invoice-chrome absolute end-4 top-4 z-[2] flex gap-2"
        data-testid="invoice-chrome"
      >
        <button
          type="button"
          onClick={() => window.print()}
          data-testid="invoice-print-button"
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
          data-testid="invoice-close-button"
          aria-label="Close invoice"
          className={cn(
            "flex items-center gap-1.5 rounded-lg border border-border bg-white/[0.06] px-3.5 py-2",
            "text-xs font-semibold text-text-secondary",
          )}
        >
          <X className="h-3.5 w-3.5" />
          Close
        </button>
      </div>

      <div
        className="pos-invoice-paper w-[min(880px,100%)] max-h-[92vh] overflow-auto rounded-md shadow-[0_30px_80px_rgba(0,0,0,0.6)]"
        style={{ background: "#fbfaf7", color: "#0b1a29", fontFamily: "Inter, sans-serif" }}
      >
        <div
          className="brand-ribbon relative grid grid-cols-[1fr_auto] items-center gap-4 overflow-hidden px-7 py-[18px]"
          style={{ background: "linear-gradient(90deg, #0b1a29, #163452)", color: "#fbfaf7" }}
        >
          <div
            aria-hidden="true"
            className="absolute -top-8 end-[-30px] h-40 w-40 rounded-full"
            style={{ background: "radial-gradient(circle, rgba(0,199,242,0.35), transparent 60%)" }}
          />
          <div className="relative flex items-center gap-3.5">
            <div
              className="h-[42px] w-[42px] rounded-[10px]"
              style={{
                background:
                  "radial-gradient(circle at 30% 30%, #5cdfff, #00c7f2 60%, #7467f8)",
                boxShadow: "0 0 20px rgba(0,199,242,0.6)",
              }}
            />
            <div>
              <div
                className="text-2xl font-medium italic"
                style={{ fontFamily: "Fraunces, serif", letterSpacing: "-0.01em" }}
              >
                DataPulse Pharmacy
              </div>
              <div className="text-[11px] tracking-[0.1em] opacity-85">
                Simplified tax invoice
              </div>
            </div>
          </div>
          <div
            className="relative text-right"
            style={{ fontFamily: "JetBrains Mono, monospace" }}
          >
            <div className="text-lg font-bold" data-testid="invoice-number">
              {invNo}
            </div>
            <div className="text-[10.5px] opacity-85">
              {fmtDate(now)} · {fmtTime(now)}
            </div>
          </div>
        </div>

        <div className="px-7 py-6">
          <div className="mb-[18px] grid grid-cols-[1.2fr_1fr_1fr] gap-[18px]">
            <MetaBlock label="Issued by">
              <div className="font-bold">{branchName ?? "Maadi branch · POS-03"}</div>
              <div className="ink-muted mt-0.5 text-[10.5px]" style={{ color: "#555" }}>
                12 Sobhi Saleh St · Cairo
              </div>
              <div className="ink-muted text-[10.5px]" style={{ color: "#555" }}>
                Tax no.{" "}
                <span style={{ fontFamily: "JetBrains Mono, monospace" }}>428-893-011</span>
              </div>
            </MetaBlock>
            <MetaBlock label="Customer">
              <div className="font-bold">Walk-in customer</div>
              {insurance && (
                <>
                  <div className="ink-muted mt-0.5 text-[10.5px]" style={{ color: "#555" }}>
                    Insurer: <b style={{ color: "#0b1a29" }}>{insurance.name}</b>
                  </div>
                  <div
                    className="ink-muted text-[10.5px]"
                    style={{ color: "#555", fontFamily: "JetBrains Mono, monospace" }}
                  >
                    Coverage {insurance.coveragePct}%
                  </div>
                </>
              )}
            </MetaBlock>
            <MetaBlock label="Transaction">
              <div className="grid grid-cols-[auto_1fr] gap-x-2.5 gap-y-0.5 text-[10.5px]">
                <span className="ink-muted" style={{ color: "#555" }}>
                  Cashier
                </span>
                <span className="font-semibold">{cashierName ?? "Nour Mohamed"}</span>
                <span className="ink-muted" style={{ color: "#555" }}>
                  Method
                </span>
                <span className="font-semibold">{PAYMENT_LABELS[paymentMethod]}</span>
                <span className="ink-muted" style={{ color: "#555" }}>
                  Ref
                </span>
                <span style={{ fontFamily: "JetBrains Mono, monospace" }}>{ref}</span>
              </div>
            </MetaBlock>
          </div>

          <table className="mb-4 w-full border-collapse">
            <thead>
              <tr style={{ background: "#0b1a29", color: "#fbfaf7" }}>
                <InvTh width={28} align="center">
                  #
                </InvTh>
                <InvTh width={100} align="start">
                  SKU
                </InvTh>
                <InvTh align="start">Description</InvTh>
                <InvTh width={48} align="end">
                  Qty
                </InvTh>
                <InvTh width={80} align="end">
                  Unit ex-VAT
                </InvTh>
                <InvTh width={68} align="end">
                  VAT 14%
                </InvTh>
                <InvTh width={90} align="end">
                  Line total
                </InvTh>
              </tr>
            </thead>
            <tbody>
              {items.length === 0 && (
                <tr>
                  <InvTd
                    colSpan={7}
                    align="center"
                    style={{ padding: "14px 0", color: "#888" }}
                  >
                    —
                  </InvTd>
                </tr>
              )}
              {items.map((l, i) => {
                const lineIncl = l.line_total;
                const unitIncl = l.unit_price;
                const vat = lineIncl - lineIncl / 1.14;
                return (
                  <tr
                    key={l.drug_code}
                    className="row-alt"
                    data-testid={`invoice-row-${l.drug_code}`}
                    style={{ borderBottom: "0.5px solid #bbb" }}
                  >
                    <InvTd align="center" mono>
                      {String(i + 1).padStart(2, "0")}
                    </InvTd>
                    <InvTd mono style={{ fontSize: 10 }}>
                      {l.drug_code}
                    </InvTd>
                    <InvTd>
                      <div className="font-semibold">{l.drug_name}</div>
                      <div
                        className="ink-muted text-[9.5px]"
                        style={{ color: "#555", fontFamily: "JetBrains Mono, monospace" }}
                      >
                        Unit {fmtEGP(unitIncl)} · incl. VAT
                      </div>
                    </InvTd>
                    <InvTd align="end" mono>
                      <b>{l.quantity}</b>
                    </InvTd>
                    <InvTd align="end" mono>
                      {fmtEGP(unitIncl / 1.14)}
                    </InvTd>
                    <InvTd align="end" mono>
                      {fmtEGP(vat)}
                    </InvTd>
                    <InvTd align="end" mono>
                      <b>{fmtEGP(lineIncl)}</b>
                    </InvTd>
                  </tr>
                );
              })}
            </tbody>
          </table>

          <div className="grid grid-cols-[1fr_1fr] gap-[18px]">
            <div>
              <div
                className="mb-2 text-[10px] font-bold uppercase tracking-[0.18em]"
                style={{ color: "#555" }}
              >
                Notes
              </div>
              <ul
                className="ink-muted m-0 list-disc ps-4 text-[10.5px] leading-[1.6]"
                style={{ color: "#555" }}
              >
                <li>Prices are inclusive of 14% VAT.</li>
                <li>
                  No returns once the medication leaves the pharmacy, except for defects.
                </li>
                <li>Retain this invoice for insurance claims and warranty periods.</li>
                {discountSource === "voucher" && discountLabel && (
                  <li className="font-semibold" style={{ color: "#0b1a29" }}>
                    Voucher applied:{" "}
                    <span style={{ fontFamily: "JetBrains Mono, monospace" }}>
                      {discountLabel}
                    </span>
                  </li>
                )}
                {discountSource === "promotion" && discountLabel && (
                  <li className="font-semibold" style={{ color: "#0b1a29" }}>
                    Promotion: {discountLabel}
                  </li>
                )}
              </ul>
            </div>

            <div
              className="totals-box rounded-[4px] border px-4 py-3.5"
              style={{ background: "#f1ede4", borderColor: "#0b1a29" }}
              data-testid="invoice-totals-box"
            >
              <TotalRow label="Subtotal ex-VAT" value={fmtEGP(subtotalEx)} />
              <TotalRow label="VAT (14%)" value={fmtEGP(vatTotal)} />
              {discountTotal > 0 && (
                <TotalRow label="Discounts" value={`−${fmtEGP(discountTotal)}`} negative />
              )}
              {insurance && (
                <TotalRow
                  label={`Insurer pays (${insurance.coveragePct}%)`}
                  value={`−${fmtEGP(insurerPays)}`}
                  negative
                />
              )}
              <div
                className="my-2.5 mb-2"
                style={{ borderTop: "1.5px solid #0b1a29" }}
              />
              <div className="flex items-baseline justify-between">
                <span
                  className="text-[10px] font-bold uppercase tracking-[0.18em]"
                  style={{ color: "#555" }}
                >
                  {insurance ? "Patient pays" : "Amount due"}
                </span>
                <span
                  className="grand font-medium italic"
                  style={{
                    fontFamily: "Fraunces, serif",
                    fontSize: 26,
                    color: "#0b1a29",
                  }}
                  data-testid="invoice-grand-total"
                >
                  {fmtEGP(patientPays)}
                </span>
              </div>
            </div>
          </div>

          <div className="mt-7 grid grid-cols-3 gap-5">
            <InvSig label="Cashier signature" prefilled={cashierName ?? "Nour Mohamed"} />
            <InvSig label="Pharmacy stamp" />
            <InvSig label="Customer signature" />
          </div>

          <div
            className="ink-muted mt-6 flex items-center justify-between border-t pt-2.5 text-[9.5px]"
            style={{ borderTopStyle: "dashed", borderTopColor: "#888", color: "#555" }}
          >
            <span style={{ color: "#555" }}>
              Thank you · patient hotline 19248
            </span>
            <span style={{ color: "#555", fontFamily: "JetBrains Mono, monospace" }}>
              {invNo} · p 1/1
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

interface MetaBlockProps {
  label: string;
  children: React.ReactNode;
}
function MetaBlock({ label, children }: MetaBlockProps) {
  return (
    <div
      className="rounded-[4px] px-3 py-2.5"
      style={{
        background: "rgba(11,26,41,0.04)",
        border: "0.5px solid rgba(11,26,41,0.3)",
      }}
    >
      <div
        className="mb-1.5 text-[9px] font-bold uppercase tracking-[0.18em]"
        style={{ color: "#555" }}
      >
        {label}
      </div>
      <div className="text-[12px]">{children}</div>
    </div>
  );
}

interface InvThProps {
  children: React.ReactNode;
  width?: number;
  align?: "start" | "center" | "end";
}
function InvTh({ children, width, align = "center" }: InvThProps) {
  return (
    <th
      className="text-[9.5px] font-bold uppercase tracking-[0.16em]"
      style={{
        padding: "7px 7px",
        width,
        textAlign: align,
      }}
    >
      {children}
    </th>
  );
}

interface InvTdProps {
  children: React.ReactNode;
  align?: "start" | "center" | "end";
  mono?: boolean;
  style?: React.CSSProperties;
  colSpan?: number;
}
function InvTd({ children, align = "start", mono, style, colSpan }: InvTdProps) {
  return (
    <td
      colSpan={colSpan}
      style={{
        padding: "7px 7px",
        textAlign: align,
        fontFamily: mono ? "JetBrains Mono, monospace" : "inherit",
        fontSize: mono ? 10.5 : 11,
        verticalAlign: "middle",
        ...style,
      }}
    >
      {children}
    </td>
  );
}

interface TotalRowProps {
  label: string;
  value: string;
  negative?: boolean;
}
function TotalRow({ label, value, negative }: TotalRowProps) {
  return (
    <div className="flex items-baseline justify-between py-[3px] text-[11.5px]">
      <span style={{ color: "#555" }}>{label}</span>
      <span
        className="font-semibold"
        style={{
          fontFamily: "JetBrains Mono, monospace",
          color: negative ? "#0b7a4b" : "#0b1a29",
        }}
      >
        {value}
      </span>
    </div>
  );
}

function InvSig({ label, prefilled }: { label: string; prefilled?: string }) {
  return (
    <div>
      <div
        className="flex items-end ps-1 italic"
        style={{
          borderBottom: "1px solid #0b1a29",
          minHeight: 38,
          fontFamily: "Fraunces, serif",
          fontSize: 14,
          color: "#0b1a29",
        }}
      >
        {prefilled ?? ""}
      </div>
      <div
        className="mt-1 text-[9.5px] uppercase tracking-[0.12em]"
        style={{ color: "#555" }}
      >
        {label}
      </div>
    </div>
  );
}
