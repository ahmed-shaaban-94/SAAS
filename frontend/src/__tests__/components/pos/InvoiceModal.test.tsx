import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { InvoiceModal } from "@/components/pos/InvoiceModal";
import type {
  CheckoutResponse,
  PosCartItem,
  TransactionDetailResponse,
} from "@/types/pos";

function makeItem(overrides: Partial<PosCartItem> = {}): PosCartItem {
  const quantity = overrides.quantity ?? 2;
  const unit_price = overrides.unit_price ?? 57;
  return {
    drug_code: "MED-001",
    drug_name: "Paracetamol 500mg",
    batch_number: null,
    expiry_date: null,
    quantity,
    unit_price,
    discount: 0,
    line_total: quantity * unit_price,
    is_controlled: false,
    ...overrides,
  };
}

function makeTxn(overrides: Partial<TransactionDetailResponse> = {}): TransactionDetailResponse {
  const items = overrides.items ?? [makeItem()];
  const subtotal = items.reduce((s, i) => s + i.line_total, 0);
  const tax_total = subtotal - subtotal / 1.14;
  return {
    id: 42,
    tenant_id: 1,
    terminal_id: 1,
    staff_id: "staff-1",
    pharmacist_id: null,
    customer_id: null,
    site_code: "MAADI",
    subtotal,
    discount_total: 0,
    tax_total,
    grand_total: subtotal,
    payment_method: "cash",
    status: "completed",
    receipt_number: "INV-260420-0042",
    created_at: "2026-04-20T09:15:00Z",
    items,
    ...overrides,
  };
}

function makeResult(overrides: Partial<CheckoutResponse> = {}): CheckoutResponse {
  return {
    transaction: {
      id: 42,
      tenant_id: 1,
      terminal_id: 1,
      staff_id: "staff-1",
      pharmacist_id: null,
      customer_id: null,
      site_code: "MAADI",
      subtotal: 114,
      discount_total: 0,
      tax_total: 14,
      grand_total: 114,
      payment_method: "cash",
      status: "completed",
      receipt_number: "INV-260420-0042",
      created_at: "2026-04-20T09:15:00Z",
    },
    change_amount: 0,
    receipt_number: "INV-260420-0042",
    ...overrides,
  };
}

const baseProps = {
  branchName: "Maadi branch · POS-03",
  branchAddress: "12 Sobhi Saleh St · Cairo",
  taxNumber: "428-893-011",
  cashierName: "Nour Mohamed",
};

// jsdom does not implement window.print — stub it so components that
// call it (Print button) don't throw during tests.
const printStub = vi.fn();
Object.defineProperty(window, "print", {
  configurable: true,
  writable: true,
  value: printStub,
});

describe("InvoiceModal", () => {
  beforeEach(() => {
    printStub.mockReset();
  });

  it("renders nothing when closed", () => {
    render(
      <InvoiceModal
        open={false}
        onClose={vi.fn()}
        transaction={makeTxn()}
        checkoutResult={makeResult()}
        {...baseProps}
      />,
    );
    expect(screen.queryByTestId("pos-invoice-modal")).not.toBeInTheDocument();
  });

  it("shows invoice number, branch, cashier, and one item row when open", () => {
    render(
      <InvoiceModal
        open
        onClose={vi.fn()}
        transaction={makeTxn()}
        checkoutResult={makeResult()}
        {...baseProps}
      />,
    );
    expect(screen.getByTestId("pos-invoice-modal")).toBeInTheDocument();
    expect(screen.getByTestId("pos-invoice-number")).toHaveTextContent("INV-260420-0042");
    expect(screen.getByText(/Maadi branch · POS-03/)).toBeInTheDocument();
    // Cashier name appears in both the meta block and the signature line.
    expect(screen.getAllByText("Nour Mohamed").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/Paracetamol 500mg/)).toBeInTheDocument();
  });

  it("falls back to a derived invoice number when receipt_number is null", () => {
    render(
      <InvoiceModal
        open
        onClose={vi.fn()}
        transaction={makeTxn({ receipt_number: null })}
        checkoutResult={makeResult({ receipt_number: "" })}
        {...baseProps}
      />,
    );
    expect(screen.getByTestId("pos-invoice-number")).toHaveTextContent(/^INV-260420-\d{4}$/);
  });

  it("Print button calls window.print()", async () => {
    render(
      <InvoiceModal
        open
        onClose={vi.fn()}
        transaction={makeTxn()}
        checkoutResult={makeResult()}
        {...baseProps}
      />,
    );
    await userEvent.click(screen.getByTestId("pos-invoice-print-button"));
    expect(printStub).toHaveBeenCalledTimes(1);
  });

  it("Close button and Esc fire onClose", async () => {
    const onClose = vi.fn();
    render(
      <InvoiceModal
        open
        onClose={onClose}
        transaction={makeTxn()}
        checkoutResult={makeResult()}
        {...baseProps}
      />,
    );
    await userEvent.click(screen.getByTestId("pos-invoice-close-button"));
    expect(onClose).toHaveBeenCalledTimes(1);

    await userEvent.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalledTimes(2);
  });

  it("shows insurance meta block and insurer-pays line when insurance prop present", () => {
    render(
      <InvoiceModal
        open
        onClose={vi.fn()}
        transaction={makeTxn()}
        checkoutResult={makeResult()}
        insurance={{ name: "AXA Egypt", coverage: 80 }}
        {...baseProps}
      />,
    );
    expect(screen.getByText("AXA Egypt")).toBeInTheDocument();
    expect(screen.getByText(/Coverage 80%/)).toBeInTheDocument();
    expect(screen.getByText(/Insurer pays \(80%\)/)).toBeInTheDocument();
    expect(screen.getByText(/Patient pays/)).toBeInTheDocument();
  });

  it("labels amount due instead of patient pays when no insurance", () => {
    render(
      <InvoiceModal
        open
        onClose={vi.fn()}
        transaction={makeTxn()}
        checkoutResult={makeResult()}
        {...baseProps}
      />,
    );
    expect(screen.getByText(/Amount due/)).toBeInTheDocument();
    expect(screen.queryByText(/Patient pays/)).not.toBeInTheDocument();
  });

  it("shows the voucher code note when voucher is applied", () => {
    render(
      <InvoiceModal
        open
        onClose={vi.fn()}
        transaction={makeTxn({ discount_total: 14 })}
        checkoutResult={makeResult()}
        voucher="SAVE10"
        {...baseProps}
      />,
    );
    expect(screen.getByText(/Voucher applied:/)).toBeInTheDocument();
    expect(screen.getByText("SAVE10")).toBeInTheDocument();
    expect(screen.getByText(/Discounts/)).toBeInTheDocument();
  });

  it("shows the promotion name when a promotion is applied", () => {
    render(
      <InvoiceModal
        open
        onClose={vi.fn()}
        transaction={makeTxn({ discount_total: 7 })}
        checkoutResult={makeResult()}
        promotion="Ramadan 2026"
        {...baseProps}
      />,
    );
    expect(screen.getByText(/Promotion:/)).toBeInTheDocument();
    expect(screen.getByText(/Ramadan 2026/)).toBeInTheDocument();
  });

  it("renders an em-dash row when items is empty", () => {
    render(
      <InvoiceModal
        open
        onClose={vi.fn()}
        transaction={makeTxn({ items: [] })}
        checkoutResult={makeResult()}
        {...baseProps}
      />,
    );
    const tbody = screen.getByTestId("pos-invoice-items").querySelector("tbody");
    expect(tbody?.textContent ?? "").toContain("—");
  });
});
