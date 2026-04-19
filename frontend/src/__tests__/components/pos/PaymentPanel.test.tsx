import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";

import { PaymentPanel } from "@/components/pos/PaymentPanel";

describe("PaymentPanel", () => {
  it("renders all four payment method buttons", () => {
    render(<PaymentPanel grandTotal={100} onCheckout={vi.fn()} />);
    expect(screen.getByRole("button", { name: /pay with cash/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /pay with card/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /pay with insur/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /pay with voucher/i })).toBeInTheDocument();
  });

  it("invokes onCheckout with the chosen method", () => {
    const onCheckout = vi.fn();
    render(<PaymentPanel grandTotal={50} onCheckout={onCheckout} />);

    fireEvent.click(screen.getByRole("button", { name: /pay with voucher/i }));
    expect(onCheckout).toHaveBeenCalledWith("voucher");

    fireEvent.click(screen.getByRole("button", { name: /pay with cash/i }));
    expect(onCheckout).toHaveBeenCalledWith("cash");
  });

  it("disables all buttons when grandTotal is zero", () => {
    render(<PaymentPanel grandTotal={0} onCheckout={vi.fn()} />);
    for (const method of [/cash/i, /card/i, /insur/i, /voucher/i]) {
      expect(screen.getByRole("button", { name: new RegExp(`pay with ${method.source}`, "i") })).toBeDisabled();
    }
  });

  it("disables buttons when disabled prop is true", () => {
    render(<PaymentPanel grandTotal={100} disabled onCheckout={vi.fn()} />);
    expect(screen.getByRole("button", { name: /pay with voucher/i })).toBeDisabled();
  });

  it("renders grand total formatted", () => {
    render(<PaymentPanel grandTotal={1234.5} onCheckout={vi.fn()} />);
    expect(screen.getByText(/EGP/i)).toBeInTheDocument();
  });
});
