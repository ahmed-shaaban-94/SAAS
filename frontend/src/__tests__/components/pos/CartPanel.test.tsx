import { describe, it, expect } from "vitest";
import { render, screen, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";

import { CartPanel } from "@/components/pos/CartPanel";
import {
  PosCartProvider,
  usePosCart,
} from "@/contexts/pos-cart-context";
import type { PosCartItem } from "@/types/pos";
import type { VoucherValidateResponse } from "@/types/vouchers";

const drug: PosCartItem = {
  drug_code: "D1",
  drug_name: "Drug One",
  batch_number: null,
  expiry_date: null,
  quantity: 2,
  unit_price: 100,
  discount: 0,
  line_total: 200,
  is_controlled: false,
};

const PERCENT_25: VoucherValidateResponse = {
  code: "SUMMER25",
  discount_type: "percent",
  value: 25,
  remaining_uses: 5,
  expires_at: null,
  min_purchase: null,
};

/**
 * Helper: renders CartPanel inside a provider that's been pre-loaded with
 * a single drug + applied voucher. Exposes the cart hook via a ref so
 * tests can drive additional actions (e.g. clearVoucher).
 */
function Harness({ applyVoucher = false }: { applyVoucher?: boolean }) {
  const api = usePosCart();
  React.useEffect(() => {
    api.addItem(drug);
    if (applyVoucher) api.applyVoucher(PERCENT_25, 50);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  return <CartPanel />;
}

function renderWith(applyVoucher = false) {
  return render(
    <PosCartProvider>
      <Harness applyVoucher={applyVoucher} />
    </PosCartProvider>,
  );
}

describe("CartPanel voucher line", () => {
  it("does not render the voucher row when no voucher is applied", async () => {
    renderWith(false);
    await act(async () => {});
    expect(screen.queryByText(/SUMMER25/)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/remove voucher/i)).not.toBeInTheDocument();
  });

  it("renders the voucher code and discount when applied", async () => {
    renderWith(true);
    await act(async () => {});
    expect(screen.getByText(/SUMMER25/)).toBeInTheDocument();
    expect(screen.getByLabelText(/remove voucher/i)).toBeInTheDocument();
  });

  it("removes the voucher when the X button is clicked", async () => {
    const user = userEvent.setup();
    renderWith(true);
    await act(async () => {});
    await user.click(screen.getByLabelText(/remove voucher/i));
    expect(screen.queryByText(/SUMMER25/)).not.toBeInTheDocument();
  });
});
