import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

import { buildReceiptPayload, printReceipt } from "@pos/lib/print-bridge";
import type { TransactionDetailResponse, CheckoutResponse } from "@pos/types/pos";

const TXN: TransactionDetailResponse = {
  id: 7,
  client_txn_id: "client-7",
  status: "confirmed",
  shift_id: 1,
  staff_id: "nour.m",
  site_code: "ALEX-001",
  customer_id: "أحمد",
  payment_method: "cash",
  insurance_no: null,
  subtotal: 100,
  discount_total: 0,
  tax_total: 0,
  grand_total: 100,
  created_at: "2026-04-25T10:00:00Z",
  items: [
    {
      id: 1,
      transaction_id: 7,
      drug_code: "101040",
      drug_name: "PARACETAMOL 20/TAB",
      quantity: 1,
      unit_price: 100,
      line_total: 100,
      batch_number: "B1",
    },
  ],
} as unknown as TransactionDetailResponse;

const RESULT: CheckoutResponse = {
  transaction: { id: 7 } as never,
  receipt_number: "RCT-2026-0007",
} as unknown as CheckoutResponse;

const STORE = {
  staffName: "Nour M",
  storeName: "Branch 1",
  storeAddress: "5 St., Alexandria",
};

describe("buildReceiptPayload", () => {
  it("maps txn + result into the Electron ReceiptPayload shape", () => {
    const payload = buildReceiptPayload({ txn: TXN, result: RESULT, ...STORE });
    expect(payload.receiptNumber).toBe("RCT-2026-0007");
    expect(payload.storeName).toBe("Branch 1");
    expect(payload.staffName).toBe("Nour M");
    expect(payload.items).toHaveLength(1);
    expect(payload.items[0]).toMatchObject({
      name: "PARACETAMOL 20/TAB",
      qty: "1",
      unitPrice: "100",
      lineTotal: "100",
      batch: "B1",
    });
    expect(payload.total).toBe("100");
    expect(payload.paymentMethod).toBe("cash");
    expect(payload.confirmation).toBe("confirmed");
    expect(payload.currency).toBe("EGP");
  });

  it("falls back to TXN-{id} when receipt_number missing", () => {
    const result = { ...RESULT, receipt_number: undefined } as unknown as CheckoutResponse;
    const payload = buildReceiptPayload({ txn: TXN, result, ...STORE });
    expect(payload.receiptNumber).toBe("TXN-7");
  });

  it("normalises an unknown payment_method to 'cash'", () => {
    const txn = { ...TXN, payment_method: "weird" } as unknown as TransactionDetailResponse;
    const payload = buildReceiptPayload({ txn, result: RESULT, ...STORE });
    expect(payload.paymentMethod).toBe("cash");
  });
});

describe("printReceipt", () => {
  const originalPrint = window.print;
  const originalAPI = (window as { electronAPI?: unknown }).electronAPI;

  beforeEach(() => {
    window.print = vi.fn();
  });

  afterEach(() => {
    window.print = originalPrint;
    (window as { electronAPI?: unknown }).electronAPI = originalAPI;
    vi.restoreAllMocks();
  });

  it("falls back to window.print() when not running inside Electron", async () => {
    (window as { electronAPI?: unknown }).electronAPI = undefined;
    const payload = buildReceiptPayload({ txn: TXN, result: RESULT, ...STORE });
    const route = await printReceipt(payload);
    expect(route).toEqual({ route: "browser" });
    expect(window.print).toHaveBeenCalledTimes(1);
  });

  it("dispatches to the thermal IPC bridge when Electron is present and succeeds", async () => {
    const print = vi.fn().mockResolvedValue({ success: true });
    (window as { electronAPI?: unknown }).electronAPI = {
      app: { isElectron: true, platform: "win32" },
      printer: { print, status: vi.fn(), testPrint: vi.fn() },
    };
    const payload = buildReceiptPayload({ txn: TXN, result: RESULT, ...STORE });
    const route = await printReceipt(payload);
    expect(route).toEqual({ route: "thermal" });
    expect(print).toHaveBeenCalledWith(payload);
    expect(window.print).not.toHaveBeenCalled();
  });

  it("falls back to window.print() when the thermal adapter reports failure", async () => {
    const print = vi.fn().mockResolvedValue({ success: false, error: "printer_offline" });
    (window as { electronAPI?: unknown }).electronAPI = {
      app: { isElectron: true, platform: "win32" },
      printer: { print, status: vi.fn(), testPrint: vi.fn() },
    };
    const payload = buildReceiptPayload({ txn: TXN, result: RESULT, ...STORE });
    const route = await printReceipt(payload);
    expect(route).toEqual({ route: "browser", error: "printer_offline" });
    expect(window.print).toHaveBeenCalledTimes(1);
  });

  it("falls back to window.print() when the thermal adapter throws", async () => {
    const print = vi.fn().mockRejectedValue(new Error("ipc_failed"));
    (window as { electronAPI?: unknown }).electronAPI = {
      app: { isElectron: true, platform: "win32" },
      printer: { print, status: vi.fn(), testPrint: vi.fn() },
    };
    const payload = buildReceiptPayload({ txn: TXN, result: RESULT, ...STORE });
    const route = await printReceipt(payload);
    expect(route.route).toBe("browser");
    expect(route.error).toContain("ipc_failed");
    expect(window.print).toHaveBeenCalledTimes(1);
  });
});
