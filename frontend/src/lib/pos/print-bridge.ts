/**
 * Bridge between renderer-side checkout state and the Electron native
 * thermal printer adapter (issue #711).
 *
 * The Next.js renderer used to call `window.print()` unconditionally,
 * which sends the page to whatever Windows printer is selected via the
 * print dialog. On the POS desktop with a real ESC/POS thermal printer
 * this produced a "huge gray blank page" — Chromium rasterised the
 * receipt-paper texture and `@media print` rules wiped the content.
 *
 * Now: when running inside Electron and `printer_interface` is set, we
 * dispatch to `window.electronAPI.printer.print(payload)` which forwards
 * to `RealPrinter` (node-thermal-printer). On any failure or in the web
 * build we fall back to `window.print()` so existing behaviour is
 * preserved for non-thermal environments.
 *
 * Keep this file framework-agnostic — no React imports.
 */

import { hasElectron, printer } from "@/lib/pos/ipc";
import type { TransactionDetailResponse, CheckoutResponse } from "@/types/pos";

type DecimalString = string;
type Confirmation = "provisional" | "confirmed" | "reconciled";

export interface ReceiptPayload {
  storeName: string;
  storeAddress: string;
  storePhone: string;
  logoPath: string | null;
  transactionId: number | null;
  receiptNumber: string;
  createdAt: string;
  staffName: string;
  customerName: string | null;
  items: Array<{
    name: string;
    qty: DecimalString;
    unitPrice: DecimalString;
    lineTotal: DecimalString;
    batch: string | null;
    expiry: string | null;
  }>;
  subtotal: DecimalString;
  discount: DecimalString;
  tax: DecimalString;
  total: DecimalString;
  paymentMethod: "cash" | "card" | "insurance" | "mixed";
  cashTendered: DecimalString | null;
  changeDue: DecimalString | null;
  languages: Array<"ar" | "en">;
  currency: "EGP";
  confirmation: Confirmation;
}

interface BuildArgs {
  txn: TransactionDetailResponse;
  result: CheckoutResponse;
  staffName: string;
  storeName: string;
  storeAddress: string;
  storePhone?: string;
  cashTendered?: DecimalString | null;
  changeDue?: DecimalString | null;
  confirmation?: Confirmation;
}

const ALLOWED_METHODS = new Set(["cash", "card", "insurance", "mixed"]);

function normaliseMethod(raw: string | null | undefined): ReceiptPayload["paymentMethod"] {
  if (raw && ALLOWED_METHODS.has(raw)) return raw as ReceiptPayload["paymentMethod"];
  return "cash";
}

export function buildReceiptPayload(args: BuildArgs): ReceiptPayload {
  const { txn, result, staffName, storeName, storeAddress } = args;
  return {
    storeName,
    storeAddress,
    storePhone: args.storePhone ?? "",
    logoPath: null,
    transactionId: txn.id ?? null,
    receiptNumber: result.receipt_number ?? `TXN-${txn.id}`,
    createdAt: typeof txn.created_at === "string" ? txn.created_at : new Date().toISOString(),
    staffName: staffName || "Staff",
    customerName: txn.customer_id ?? null,
    items: txn.items.map((i) => ({
      name: i.drug_name,
      qty: String(i.quantity),
      unitPrice: String(i.unit_price),
      lineTotal: String(i.line_total),
      batch: i.batch_number ?? null,
      expiry: null,
    })),
    subtotal: String(txn.subtotal),
    discount: String(txn.discount_total),
    tax: String(txn.tax_total),
    total: String(txn.grand_total),
    paymentMethod: normaliseMethod(txn.payment_method),
    cashTendered: args.cashTendered ?? null,
    changeDue: args.changeDue ?? null,
    languages: ["ar", "en"],
    currency: "EGP",
    confirmation: args.confirmation ?? "confirmed",
  };
}

interface BuildShiftArgs {
  /** ``TerminalSessionResponse`` from the close-shift endpoint, or the
   *  active terminal row when reprinting. */
  shift: {
    id: number;
    site_code?: string | null;
    terminal_name?: string | null;
    opened_at?: string | null;
    closed_at?: string | null;
    opening_cash?: number | string | null;
    closing_cash?: number | string | null;
  };
  /** Cash sales over the shift, when the server exposes it. ``0`` is fine
   *  in the smoke-test phase — the variance line will reflect that. */
  cashSales?: number | string | null;
  staffName: string;
  storeName: string;
  storeAddress: string;
  storePhone?: string;
}

/**
 * Build a {@link ReceiptPayload} that the existing thermal adapter can
 * print as a shift-close slip. The adapter formats items[] / total /
 * payment header generically, so we synthesise items[] from the shift
 * fields and use ``total`` for closing cash. The receipt header reads
 * ``SHIFT CLOSE`` instead of a transaction number.
 *
 * Avoids growing a parallel ESC/POS code path in the main process — one
 * payload shape, one renderer, one main-process formatter.
 */
export function buildShiftReceiptPayload(args: BuildShiftArgs): ReceiptPayload {
  const { shift } = args;
  const opening = Number(shift.opening_cash ?? 0);
  const closing = Number(shift.closing_cash ?? 0);
  const cashSales = Number(args.cashSales ?? 0);
  const expected = opening + cashSales;
  const variance = closing - expected;
  const fmt = (n: number) => n.toFixed(2);
  return {
    storeName: args.storeName,
    storeAddress: args.storeAddress,
    storePhone: args.storePhone ?? "",
    logoPath: null,
    transactionId: null,
    receiptNumber: `SHIFT-${shift.id}`,
    createdAt: shift.closed_at ?? new Date().toISOString(),
    staffName: args.staffName || "Staff",
    customerName: shift.terminal_name ?? null,
    items: [
      { name: "Opening cash", qty: "", unitPrice: "", lineTotal: fmt(opening), batch: null, expiry: null },
      { name: "Cash sales", qty: "", unitPrice: "", lineTotal: fmt(cashSales), batch: null, expiry: null },
      { name: "Expected", qty: "", unitPrice: "", lineTotal: fmt(expected), batch: null, expiry: null },
      { name: "Counted (closing)", qty: "", unitPrice: "", lineTotal: fmt(closing), batch: null, expiry: null },
      { name: "Variance", qty: "", unitPrice: "", lineTotal: fmt(variance), batch: null, expiry: null },
    ],
    subtotal: fmt(expected),
    discount: "0.00",
    tax: "0.00",
    total: fmt(closing),
    paymentMethod: "cash",
    cashTendered: null,
    changeDue: null,
    languages: ["ar", "en"],
    currency: "EGP",
    confirmation: "confirmed",
  };
}

/**
 * Print the receipt via the Electron native thermal adapter when available,
 * else fall back to `window.print()`. Always resolves — never throws.
 *
 * Returns the route taken so callers can log telemetry.
 */
export async function printReceipt(
  payload: ReceiptPayload,
): Promise<{ route: "thermal" | "browser"; error?: string }> {
  if (!hasElectron()) {
    if (typeof window !== "undefined") window.print();
    return { route: "browser" };
  }
  try {
    const res = await printer.print(payload);
    if (res.success) return { route: "thermal" };
    if (typeof window !== "undefined") window.print();
    return { route: "browser", error: res.error };
  } catch (err: unknown) {
    if (typeof window !== "undefined") window.print();
    const msg = err instanceof Error ? err.message : String(err);
    return { route: "browser", error: msg };
  }
}
