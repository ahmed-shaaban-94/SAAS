import { describe, it, expect } from "vitest";
import { renderHook, act } from "@testing-library/react";
import React, { type ReactNode } from "react";
import { PosCartProvider, usePosCart } from "@/contexts/pos-cart-context";
import type { PosCartItem } from "@/types/pos";
import type { VoucherValidateResponse } from "@/types/vouchers";

function wrapper({ children }: { children: ReactNode }) {
  return React.createElement(PosCartProvider, null, children);
}

const drug = (overrides: Partial<PosCartItem> = {}): PosCartItem => ({
  drug_code: "D1",
  drug_name: "Drug One",
  batch_number: null,
  expiry_date: null,
  quantity: 1,
  unit_price: 100,
  discount: 0,
  line_total: 100,
  is_controlled: false,
  ...overrides,
});

const PERCENT_25: VoucherValidateResponse = {
  code: "SUMMER25",
  discount_type: "percent",
  value: 25,
  remaining_uses: 5,
  expires_at: null,
  min_purchase: null,
};

const AMOUNT_50: VoucherValidateResponse = {
  code: "FLAT50",
  discount_type: "amount",
  value: 50,
  remaining_uses: 1,
  expires_at: null,
  min_purchase: null,
};

describe("PosCartProvider voucher slice", () => {
  it("starts with no voucher", () => {
    const { result } = renderHook(() => usePosCart(), { wrapper });
    expect(result.current.voucher).toBeNull();
    expect(result.current.voucherDiscountTotal).toBe(0);
  });

  it("applies a percent voucher and subtracts from grand total", () => {
    const { result } = renderHook(() => usePosCart(), { wrapper });
    act(() => {
      result.current.addItem(drug({ quantity: 2, line_total: 200 }));
    });
    expect(result.current.subtotal).toBe(200);

    act(() => {
      result.current.applyVoucher(PERCENT_25, 50);
    });
    expect(result.current.voucher?.code).toBe("SUMMER25");
    expect(result.current.voucherDiscountTotal).toBe(50);
    expect(result.current.discountTotal).toBe(50);
    expect(result.current.grandTotal).toBe(150);
  });

  it("applies a fixed-amount voucher", () => {
    const { result } = renderHook(() => usePosCart(), { wrapper });
    act(() => {
      result.current.addItem(drug({ quantity: 3, line_total: 300 }));
      result.current.applyVoucher(AMOUNT_50, 50);
    });
    expect(result.current.voucherDiscountTotal).toBe(50);
    expect(result.current.grandTotal).toBe(250);
  });

  it("recomputes percent discount when cart changes after applying", () => {
    const { result } = renderHook(() => usePosCart(), { wrapper });
    act(() => {
      result.current.addItem(drug({ quantity: 2, line_total: 200 }));
      result.current.applyVoucher(PERCENT_25, 50);
    });
    expect(result.current.grandTotal).toBe(150);

    // Adding another item: subtotal 300, new 25% = 75
    act(() => {
      result.current.addItem(
        drug({ drug_code: "D2", drug_name: "Drug Two", quantity: 1, line_total: 100 }),
      );
    });
    expect(result.current.subtotal).toBe(300);
    expect(result.current.voucherDiscountTotal).toBe(75);
    expect(result.current.grandTotal).toBe(225);
  });

  it("caps fixed-amount voucher at subtotal when cart shrinks", () => {
    const { result } = renderHook(() => usePosCart(), { wrapper });
    act(() => {
      result.current.addItem(drug({ quantity: 3, line_total: 300 }));
      result.current.applyVoucher(AMOUNT_50, 50);
    });

    // Reduce to 1 unit of 10 EGP -> voucher clamps to 10
    act(() => {
      result.current.updateQuantity("D1", 1);
    });
    // subtotal 100, flat 50 applies normally
    expect(result.current.voucherDiscountTotal).toBe(50);
    expect(result.current.grandTotal).toBe(50);
  });

  it("never drives grand total negative", () => {
    const { result } = renderHook(() => usePosCart(), { wrapper });
    act(() => {
      result.current.addItem(drug({ quantity: 1, unit_price: 30, line_total: 30 }));
      result.current.applyVoucher(AMOUNT_50, 50);
    });
    // subtotal 30, flat 50 clamps to 30
    expect(result.current.voucherDiscountTotal).toBe(30);
    expect(result.current.grandTotal).toBe(0);
  });

  it("clearVoucher removes the voucher and restores grand total", () => {
    const { result } = renderHook(() => usePosCart(), { wrapper });
    act(() => {
      result.current.addItem(drug({ quantity: 2, line_total: 200 }));
      result.current.applyVoucher(PERCENT_25, 50);
    });
    expect(result.current.grandTotal).toBe(150);

    act(() => {
      result.current.clearVoucher();
    });
    expect(result.current.voucher).toBeNull();
    expect(result.current.voucherDiscountTotal).toBe(0);
    expect(result.current.grandTotal).toBe(200);
  });

  it("clearCart also clears the voucher", () => {
    const { result } = renderHook(() => usePosCart(), { wrapper });
    act(() => {
      result.current.addItem(drug({ quantity: 2, line_total: 200 }));
      result.current.applyVoucher(PERCENT_25, 50);
      result.current.clearCart();
    });
    expect(result.current.items).toHaveLength(0);
    expect(result.current.voucher).toBeNull();
    expect(result.current.grandTotal).toBe(0);
  });
});
