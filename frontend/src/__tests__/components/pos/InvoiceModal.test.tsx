import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { InvoiceModal } from "@/components/pos/InvoiceModal";
import type { PosCartItem } from "@/types/pos";

function makeItem(overrides: Partial<PosCartItem> = {}): PosCartItem {
  return {
    drug_code: "AMOX-500",
    drug_name: "Amoxicillin 500mg",
    batch_number: null,
    expiry_date: null,
    quantity: 2,
    unit_price: 28.5,
    discount: 0,
    line_total: 57.0,
    is_controlled: true,
    ...overrides,
  };
}

describe("InvoiceModal", () => {
  // jsdom ships without window.print, so assign a fresh mock each test.
  const originalPrint = window.print;
  beforeEach(() => {
    window.print = vi.fn();
  });
  afterEach(() => {
    window.print = originalPrint;
    vi.restoreAllMocks();
  });

  it("renders nothing when open=false", () => {
    const { container } = render(
      <InvoiceModal
        open={false}
        onClose={vi.fn()}
        items={[makeItem()]}
        grandTotal={57}
        discountTotal={0}
        paymentMethod="cash"
      />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("renders one row per cart item and mints an invoice number", () => {
    render(
      <InvoiceModal
        open
        onClose={vi.fn()}
        items={[
          makeItem(),
          makeItem({ drug_code: "PARA-500", drug_name: "Paracetamol", quantity: 1, unit_price: 5.75, line_total: 5.75 }),
        ]}
        grandTotal={62.75}
        discountTotal={0}
        paymentMethod="card"
      />,
    );
    expect(screen.getByTestId("invoice-row-AMOX-500")).toBeInTheDocument();
    expect(screen.getByTestId("invoice-row-PARA-500")).toBeInTheDocument();
    expect(screen.getByTestId("invoice-number").textContent).toMatch(/^INV-\d{6}-\d{4}$/);
  });

  it("prefers the server-provided receipt_number over a minted one", () => {
    render(
      <InvoiceModal
        open
        onClose={vi.fn()}
        items={[makeItem()]}
        grandTotal={57}
        discountTotal={0}
        paymentMethod="cash"
        receiptNumber="RCPT-42-0001"
      />,
    );
    expect(screen.getByTestId("invoice-number").textContent).toBe("RCPT-42-0001");
  });

  it("computes VAT 14% from the line total (inclusive pricing)", () => {
    render(
      <InvoiceModal
        open
        onClose={vi.fn()}
        items={[
          makeItem({
            drug_code: "AMOX-500",
            quantity: 1,
            unit_price: 114.0,
            line_total: 114.0,
          }),
        ]}
        grandTotal={114}
        discountTotal={0}
        paymentMethod="cash"
      />,
    );
    // Subtotal ex-VAT = 114 / 1.14 = 100.00; VAT = 14.00; Grand = 114.00
    const totalsBox = screen.getByTestId("invoice-totals-box");
    expect(totalsBox.textContent).toContain("EGP 100.00");
    expect(totalsBox.textContent).toContain("EGP 14.00");
    expect(screen.getByTestId("invoice-grand-total").textContent).toContain("EGP 114.00");
  });

  it("shows insurer / patient split when an insurance prop is supplied", () => {
    render(
      <InvoiceModal
        open
        onClose={vi.fn()}
        items={[makeItem({ quantity: 1, unit_price: 100, line_total: 100 })]}
        grandTotal={100}
        discountTotal={0}
        paymentMethod="insurance"
        insurance={{ name: "MedCo", coveragePct: 80 }}
      />,
    );
    // Insurer pays 80 of 100, patient pays 20.
    expect(screen.getByText(/Insurer pays \(80%\)/)).toBeInTheDocument();
    expect(screen.getByText(/Patient pays/)).toBeInTheDocument();
    expect(screen.getByTestId("invoice-grand-total").textContent).toContain("EGP 20.00");
  });

  it("echoes voucher/promotion label into the Notes block", () => {
    const { rerender } = render(
      <InvoiceModal
        open
        onClose={vi.fn()}
        items={[makeItem()]}
        grandTotal={57}
        discountTotal={10}
        discountSource="voucher"
        discountLabel="SUMMER10"
        paymentMethod="cash"
      />,
    );
    expect(screen.getByText(/SUMMER10/)).toBeInTheDocument();

    rerender(
      <InvoiceModal
        open
        onClose={vi.fn()}
        items={[makeItem()]}
        grandTotal={57}
        discountTotal={10}
        discountSource="promotion"
        discountLabel="Ramadan 2026"
        paymentMethod="cash"
      />,
    );
    expect(screen.getByText(/Ramadan 2026/)).toBeInTheDocument();
  });

  it("Print button invokes window.print", async () => {
    const user = userEvent.setup();
    render(
      <InvoiceModal
        open
        onClose={vi.fn()}
        items={[makeItem()]}
        grandTotal={57}
        discountTotal={0}
        paymentMethod="cash"
      />,
    );
    await user.click(screen.getByTestId("invoice-print-button"));
    expect(window.print).toHaveBeenCalledOnce();
  });

  it("Close button + Escape key both fire onClose", async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();
    render(
      <InvoiceModal
        open
        onClose={onClose}
        items={[makeItem()]}
        grandTotal={57}
        discountTotal={0}
        paymentMethod="cash"
      />,
    );
    await user.click(screen.getByTestId("invoice-close-button"));
    expect(onClose).toHaveBeenCalledTimes(1);

    await user.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalledTimes(2);
  });
});
