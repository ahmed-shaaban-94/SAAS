"use client";

import { useEffect } from "react";
import { Printer, X } from "lucide-react";
import { FocusTrap } from "focus-trap-react";
import type {
  CheckoutResponse,
  PaymentMethod,
  PosCartItem,
  TransactionDetailResponse,
} from "@/types/pos";

/**
 * InvoiceModal — full A4 simplified tax-invoice.
 *
 * Design source: docs/design/pos-terminal/frames/pos/invoice.jsx
 * Triggered from /checkout after a successful commit.
 * Print contract: see `@media print` rules in globals.css (.pos-print-*).
 */
export interface InvoiceModalProps {
  open: boolean;
  onClose: () => void;
  transaction: TransactionDetailResponse;
  checkoutResult: CheckoutResponse;
  /** Legal company/pharmacy name shown in the invoice letterhead. */
  companyName?: string;
  branchName: string;
  branchAddress: string;
  taxNumber: string;
  cashierName: string;
  customerName?: string;
  insurance?: { name: string; coverage: number } | null;
  voucher?: string | null;
  promotion?: string | null;
}

const PAYMENT_LABEL: Record<PaymentMethod, string> = {
  cash: "Cash",
  card: "Credit card",
  insurance: "Medical insurance",
  voucher: "Voucher",
  mixed: "Mixed payment",
};

function fmtEgp(n: number): string {
  return (
    "EGP " +
    n.toLocaleString("en-US", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })
  );
}

function fmtDate(iso: string): { date: string; time: string } {
  const d = new Date(iso);
  return {
    date: d.toLocaleDateString("en-GB"),
    time: d.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" }),
  };
}

function deriveInvoiceNumber(
  receiptNumber: string | null | undefined,
  createdAt: string,
  txnId: number,
): string {
  if (receiptNumber) return receiptNumber;
  const ymd = createdAt.slice(2, 10).replaceAll("-", "");
  return `INV-${ymd}-${String(txnId).padStart(4, "0")}`;
}

export function InvoiceModal({
  open,
  onClose,
  transaction,
  checkoutResult,
  companyName = "Pharmacy",
  branchName,
  branchAddress,
  taxNumber,
  cashierName,
  customerName,
  insurance,
  voucher,
  promotion,
}: InvoiceModalProps) {
  // Esc to close (ignored while any input is focused — none exist in this modal today)
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

  const { date, time } = fmtDate(transaction.created_at);
  const invNo = deriveInvoiceNumber(
    checkoutResult.receipt_number ?? transaction.receipt_number,
    transaction.created_at,
    transaction.id,
  );
  const reference = `REF-${String(transaction.id).padStart(6, "0")}-${invNo.slice(-4)}`;
  const method = transaction.payment_method;
  const methodLabel = method ? PAYMENT_LABEL[method] : "—";

  const subtotalIncl = transaction.subtotal;
  const vat = transaction.tax_total;
  const subtotalEx = subtotalIncl - vat;
  const discount = transaction.discount_total;
  const insurerPays = insurance ? (subtotalIncl * insurance.coverage) / 100 : 0;
  const grandTotal = transaction.grand_total;
  const patientPays = insurance ? grandTotal - insurerPays : grandTotal;

  return (
    <div
      className="pos-print-root fixed inset-0 z-[200] grid place-items-center p-5"
      style={{
        background: "rgba(2,10,18,0.72)",
        backdropFilter: "blur(10px)",
      }}
      data-testid="pos-invoice-modal"
      role="dialog"
      aria-modal="true"
      aria-labelledby="pos-invoice-title"
    >
      <FocusTrap
        focusTrapOptions={{
          escapeDeactivates: false, // Escape handled by window keydown listener above
          allowOutsideClick: true, // backdrop click must reach the backdrop handler
          initialFocus: "[data-autofocus]",
        }}
      >
      {/* Trap container wrapping chrome + paper so FocusTrap has a single root */}
      <div className="contents">
      {/* Chrome (Print / Close) */}
      <div
        className="pos-print-chrome absolute right-4 top-4 z-[2] flex gap-2"
        data-testid="pos-invoice-chrome"
      >
        <button
          type="button"
          data-autofocus
          onClick={() => window.print()}
          data-testid="pos-invoice-print-button"
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
          data-testid="pos-invoice-close-button"
          className="flex items-center gap-2 rounded-lg border px-3.5 py-[9px] text-[13px] font-semibold"
          style={{
            background: "rgba(255,255,255,0.06)",
            color: "var(--pos-ink-2, #b8c0cc)",
            borderColor: "var(--pos-line, rgba(255,255,255,0.12))",
          }}
        >
          <X className="h-4 w-4" />
          Close
        </button>
      </div>

      {/* Paper */}
      <div
        className="pos-print-paper overflow-auto rounded-[6px]"
        style={{
          background: "var(--pos-paper, #fbfaf7)",
          color: "var(--pos-paper-ink, #0b1a29)",
          width: "min(880px, 100%)",
          maxHeight: "92vh",
          boxShadow: "0 30px 80px rgba(0,0,0,0.6)",
          fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif",
        }}
      >
        {/* Brand ribbon */}
        <div
          className="pos-print-ribbon relative grid items-center gap-4 overflow-hidden"
          style={{
            gridTemplateColumns: "1fr auto",
            background:
              "linear-gradient(90deg, var(--pos-paper-ribbon-from, #0b1a29), var(--pos-paper-ribbon-to, #163452))",
            color: "var(--pos-paper, #fbfaf7)",
            padding: "18px 28px",
          }}
        >
          <div
            aria-hidden="true"
            className="absolute -end-[30px] -top-[30px] h-40 w-40 rounded-full"
            style={{
              background:
                "radial-gradient(circle, rgba(0,199,242,0.35), transparent 60%)",
            }}
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
                id="pos-invoice-title"
                style={{
                  fontFamily: "var(--font-fraunces), Fraunces, serif",
                  fontStyle: "italic",
                  fontWeight: 500,
                  fontSize: 24,
                  letterSpacing: "-0.01em",
                }}
              >
                {companyName}
              </div>
              <div style={{ fontSize: 11, letterSpacing: "0.1em", opacity: 0.85 }}>
                Simplified tax invoice
              </div>
            </div>
          </div>
          <div
            className="relative text-right"
            style={{
              fontFamily: "var(--font-jetbrains-mono), JetBrains Mono, monospace",
            }}
          >
            <div style={{ fontSize: 18, fontWeight: 700 }} data-testid="pos-invoice-number">
              {invNo}
            </div>
            <div style={{ fontSize: 10.5, opacity: 0.85 }}>
              {date} · {time}
            </div>
          </div>
        </div>

        {/* Body */}
        <div style={{ padding: "24px 28px" }}>
          {/* Meta grid */}
          <div
            className="mb-4 grid gap-4"
            style={{ gridTemplateColumns: "1.2fr 1fr 1fr" }}
          >
            <MetaBlock label="Issued by">
              <div style={{ fontWeight: 700 }}>{branchName}</div>
              <div
                className="pos-print-muted"
                style={{
                  fontSize: 10.5,
                  color: "var(--pos-paper-ink-muted, #555)",
                  marginTop: 2,
                }}
              >
                {branchAddress}
              </div>
              <div
                className="pos-print-muted"
                style={{ fontSize: 10.5, color: "var(--pos-paper-ink-muted, #555)" }}
              >
                Tax no.{" "}
                <span
                  style={{
                    fontFamily:
                      "var(--font-jetbrains-mono), JetBrains Mono, monospace",
                  }}
                >
                  {taxNumber}
                </span>
              </div>
            </MetaBlock>
            <MetaBlock label="Customer">
              <div style={{ fontWeight: 700 }}>{customerName ?? "Walk-in customer"}</div>
              {insurance && (
                <>
                  <div
                    className="pos-print-muted"
                    style={{
                      fontSize: 10.5,
                      color: "var(--pos-paper-ink-muted, #555)",
                      marginTop: 2,
                    }}
                  >
                    Insurer: <b style={{ color: "var(--pos-paper-ink, #0b1a29)" }}>{insurance.name}</b>
                  </div>
                  <div
                    className="pos-print-muted"
                    style={{
                      fontSize: 10.5,
                      color: "var(--pos-paper-ink-muted, #555)",
                      fontFamily:
                        "var(--font-jetbrains-mono), JetBrains Mono, monospace",
                    }}
                  >
                    Coverage {insurance.coverage}%
                  </div>
                </>
              )}
            </MetaBlock>
            <MetaBlock label="Transaction">
              <div
                className="grid gap-y-[2px]"
                style={{ gridTemplateColumns: "auto 1fr", columnGap: 10, fontSize: 10.5 }}
              >
                <span
                  className="pos-print-muted"
                  style={{ color: "var(--pos-paper-ink-muted, #555)" }}
                >
                  Cashier
                </span>
                <span style={{ fontWeight: 600 }}>{cashierName}</span>
                <span
                  className="pos-print-muted"
                  style={{ color: "var(--pos-paper-ink-muted, #555)" }}
                >
                  Method
                </span>
                <span style={{ fontWeight: 600 }}>{methodLabel}</span>
                <span
                  className="pos-print-muted"
                  style={{ color: "var(--pos-paper-ink-muted, #555)" }}
                >
                  Ref
                </span>
                <span
                  style={{
                    fontFamily:
                      "var(--font-jetbrains-mono), JetBrains Mono, monospace",
                  }}
                >
                  {reference}
                </span>
              </div>
            </MetaBlock>
          </div>

          {/* Items table */}
          <table
            className="mb-4 w-full"
            style={{ borderCollapse: "collapse" }}
            data-testid="pos-invoice-items"
          >
            <thead>
              <tr
                style={{
                  background: "var(--pos-paper-ink, #0b1a29)",
                  color: "var(--pos-paper, #fbfaf7)",
                }}
              >
                <InvTh w={28} align="center">
                  #
                </InvTh>
                <InvTh w={100} align="start">
                  SKU
                </InvTh>
                <InvTh align="start">Description</InvTh>
                <InvTh w={48} align="end">
                  Qty
                </InvTh>
                <InvTh w={80} align="end">
                  Unit ex-VAT
                </InvTh>
                <InvTh w={68} align="end">
                  VAT 14%
                </InvTh>
                <InvTh w={90} align="end">
                  Line total
                </InvTh>
              </tr>
            </thead>
            <tbody>
              {transaction.items.map((item, i) => (
                <InvoiceRow key={`${item.drug_code}-${i}`} item={item} index={i} />
              ))}
              {transaction.items.length === 0 && (
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
            </tbody>
          </table>

          {/* Notes + Totals */}
          <div className="grid gap-4" style={{ gridTemplateColumns: "1fr 1fr" }}>
            <div>
              <div
                style={{
                  fontSize: 10,
                  letterSpacing: "0.18em",
                  textTransform: "uppercase",
                  fontWeight: 700,
                  color: "var(--pos-paper-ink-muted, #555)",
                  marginBottom: 8,
                }}
              >
                Notes
              </div>
              <ul
                className="pos-print-muted m-0"
                style={{
                  fontSize: 10.5,
                  lineHeight: 1.6,
                  paddingInlineStart: 16,
                  color: "var(--pos-paper-ink-muted, #555)",
                }}
              >
                <li>Prices are inclusive of 14% VAT.</li>
                <li>
                  No returns once the medication leaves the pharmacy, except for
                  defects or storage faults.
                </li>
                <li>Retain this invoice for insurance claims and warranty periods.</li>
                {voucher && (
                  <li
                    style={{
                      fontWeight: 600,
                      color: "var(--pos-paper-ink, #0b1a29)",
                    }}
                  >
                    Voucher applied:{" "}
                    <span
                      style={{
                        fontFamily:
                          "var(--font-jetbrains-mono), JetBrains Mono, monospace",
                      }}
                    >
                      {voucher}
                    </span>
                  </li>
                )}
                {promotion && (
                  <li
                    style={{
                      fontWeight: 600,
                      color: "var(--pos-paper-ink, #0b1a29)",
                    }}
                  >
                    Promotion: {promotion}
                  </li>
                )}
              </ul>
            </div>

            <div
              className="pos-print-totals-box rounded-[4px] border p-4"
              style={{
                background: "var(--pos-paper-totals, #f1ede4)",
                borderColor: "var(--pos-paper-ink, #0b1a29)",
              }}
            >
              <TotalRow label="Subtotal ex-VAT" value={fmtEgp(subtotalEx)} />
              <TotalRow label="VAT (14%)" value={fmtEgp(vat)} />
              {discount > 0 && (
                <TotalRow label="Discounts" value={"−" + fmtEgp(discount)} negative />
              )}
              {insurance && (
                <TotalRow
                  label={`Insurer pays (${insurance.coverage}%)`}
                  value={"−" + fmtEgp(insurerPays)}
                  negative
                />
              )}
              <div
                style={{
                  borderTop: "1.5px solid var(--pos-paper-ink, #0b1a29)",
                  margin: "10px 0 8px",
                }}
              />
              <div className="flex items-baseline justify-between">
                <span
                  style={{
                    fontSize: 10,
                    letterSpacing: "0.18em",
                    textTransform: "uppercase",
                    fontWeight: 700,
                    color: "var(--pos-paper-ink-muted, #555)",
                  }}
                >
                  {insurance ? "Patient pays" : "Amount due"}
                </span>
                <span
                  className="pos-print-grand"
                  data-testid="pos-invoice-grand-total"
                  style={{
                    fontFamily: "var(--font-fraunces), Fraunces, serif",
                    fontStyle: "italic",
                    fontSize: 26,
                    fontWeight: 500,
                    color: "var(--pos-paper-ink, #0b1a29)",
                  }}
                >
                  {fmtEgp(patientPays)}
                </span>
              </div>
            </div>
          </div>

          {/* Signatures */}
          <div
            className="mt-7 grid gap-5"
            style={{ gridTemplateColumns: "1fr 1fr 1fr" }}
          >
            <InvSig label="Cashier signature" prefilled={cashierName} />
            <InvSig label="Pharmacy stamp" />
            <InvSig label="Customer signature" />
          </div>

          {/* Footer */}
          <div
            className="pos-print-muted mt-6 flex items-center justify-between pt-2.5"
            style={{
              borderTop: "1px dashed #888",
              fontSize: 9.5,
              color: "var(--pos-paper-ink-muted, #555)",
            }}
          >
            <span>Thank you · patient hotline 19248</span>
            <span
              style={{
                fontFamily:
                  "var(--font-jetbrains-mono), JetBrains Mono, monospace",
                color: "var(--pos-paper-ink-muted, #555)",
              }}
            >
              {invNo} · p 1/1
            </span>
          </div>
        </div>
      </div>
      </div>{/* end trap container */}
      </FocusTrap>
    </div>
  );
}

function InvoiceRow({ item, index }: { item: PosCartItem; index: number }) {
  const lineIncl = item.line_total;
  const lineEx = lineIncl / 1.14;
  const vat = lineIncl - lineEx;
  return (
    <tr
      className="pos-print-zebra"
      style={{ borderBottom: "0.5px solid var(--pos-paper-rule, #bbb)" }}
    >
      <InvTd align="center" mono>
        {String(index + 1).padStart(2, "0")}
      </InvTd>
      <InvTd mono style={{ fontSize: 10 }}>
        {item.drug_code}
      </InvTd>
      <InvTd>
        <div style={{ fontWeight: 600 }}>{item.drug_name}</div>
        <div
          className="pos-print-muted"
          style={{
            fontSize: 9.5,
            color: "var(--pos-paper-ink-muted, #555)",
            fontFamily: "var(--font-jetbrains-mono), JetBrains Mono, monospace",
          }}
        >
          Unit {fmtEgp(item.unit_price)} · incl. VAT
        </div>
      </InvTd>
      <InvTd align="end" mono>
        <b>{item.quantity}</b>
      </InvTd>
      <InvTd align="end" mono>
        {fmtEgp(item.unit_price / 1.14)}
      </InvTd>
      <InvTd align="end" mono>
        {fmtEgp(vat)}
      </InvTd>
      <InvTd align="end" mono>
        <b>{fmtEgp(lineIncl)}</b>
      </InvTd>
    </tr>
  );
}

function MetaBlock({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div
      style={{
        padding: "10px 12px",
        background: "rgba(11,26,41,0.04)",
        border: "0.5px solid rgba(11,26,41,0.3)",
        borderRadius: 4,
      }}
    >
      <div
        style={{
          fontSize: 9,
          letterSpacing: "0.18em",
          textTransform: "uppercase",
          fontWeight: 700,
          color: "var(--pos-paper-ink-muted, #555)",
          marginBottom: 6,
        }}
      >
        {label}
      </div>
      <div style={{ fontSize: 12 }}>{children}</div>
    </div>
  );
}

function InvTh({
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
        padding: "7px 7px",
        width: w,
        fontSize: 9.5,
        letterSpacing: "0.16em",
        textTransform: "uppercase",
        textAlign: align ?? "center",
        fontWeight: 700,
      }}
    >
      {children}
    </th>
  );
}

function InvTd({
  children,
  align,
  mono,
  style,
  colSpan,
}: {
  children?: React.ReactNode;
  align?: "start" | "end" | "center";
  mono?: boolean;
  style?: React.CSSProperties;
  colSpan?: number;
}) {
  return (
    <td
      colSpan={colSpan}
      style={{
        padding: "7px 7px",
        textAlign: align ?? "start",
        fontFamily: mono
          ? "var(--font-jetbrains-mono), JetBrains Mono, monospace"
          : "inherit",
        fontSize: mono ? 10.5 : 11,
        verticalAlign: "middle",
        ...(style ?? {}),
      }}
    >
      {children}
    </td>
  );
}

function TotalRow({
  label,
  value,
  negative,
}: {
  label: string;
  value: string;
  negative?: boolean;
}) {
  return (
    <div
      className="flex items-baseline justify-between"
      style={{ padding: "3px 0", fontSize: 11.5 }}
    >
      <span style={{ color: "var(--pos-paper-ink-muted, #555)" }}>{label}</span>
      <span
        style={{
          fontFamily: "var(--font-jetbrains-mono), JetBrains Mono, monospace",
          fontWeight: 600,
          color: negative ? "#0b7a4b" : "var(--pos-paper-ink, #0b1a29)",
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
        className="flex items-end"
        style={{
          borderBottom: "1px solid var(--pos-paper-ink, #0b1a29)",
          minHeight: 38,
          paddingInlineStart: 4,
          fontFamily: "var(--font-fraunces), Fraunces, serif",
          fontStyle: "italic",
          fontSize: 14,
          color: "var(--pos-paper-ink, #0b1a29)",
        }}
      >
        {prefilled ?? ""}
      </div>
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
