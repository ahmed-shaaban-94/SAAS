import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";

import { ReceiptPreview } from "@/components/pos/ReceiptPreview";
import type {
  TransactionDetailResponse,
  CheckoutResponse,
} from "@/types/pos";

const transaction: TransactionDetailResponse = {
  id: 42,
  tenant_id: 1,
  terminal_id: 1,
  staff_id: "s1",
  pharmacist_id: null,
  customer_id: null,
  site_code: "SITE1",
  subtotal: 200,
  discount_total: 50,
  tax_total: 0,
  grand_total: 150,
  payment_method: "cash",
  status: "completed",
  receipt_number: "R-0042",
  created_at: "2026-04-19T12:00:00Z",
  items: [
    {
      drug_code: "D1",
      drug_name: "Drug One",
      batch_number: null,
      expiry_date: null,
      quantity: 2,
      unit_price: 100,
      discount: 0,
      line_total: 200,
      is_controlled: false,
    },
  ],
};

const checkoutResult: CheckoutResponse = {
  transaction,
  change_amount: 0,
  receipt_number: "R-0042",
};

describe("ReceiptPreview voucher line", () => {
  it("renders the voucher code and discount when voucher is supplied", () => {
    render(
      <ReceiptPreview
        transaction={transaction}
        checkoutResult={checkoutResult}
        voucher={{ code: "SUMMER25", discount_amount: 50 }}
        onClose={vi.fn()}
      />,
    );
    expect(screen.getByText(/Voucher SUMMER25/i)).toBeInTheDocument();
  });

  it("does not render a voucher line when voucher is null", () => {
    render(
      <ReceiptPreview
        transaction={transaction}
        checkoutResult={checkoutResult}
        voucher={null}
        onClose={vi.fn()}
      />,
    );
    expect(screen.queryByText(/Voucher SUMMER25/i)).not.toBeInTheDocument();
  });
});
