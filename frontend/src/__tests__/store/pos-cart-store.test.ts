import { describe, it, expect, beforeEach } from "vitest";
import { usePosCartStore } from "@/store/pos-cart-store";

beforeEach(() => {
  usePosCartStore.setState({
    items: [],
    appliedDiscount: null,
  });
});

// Base item with zero line discount (discount = 0 EGP flat)
const item = {
  drug_code: "PARA500",
  drug_name: "Paracetamol 500mg",
  batch_number: null,
  expiry_date: null,
  quantity: 1,
  unit_price: 10,
  discount: 0,
  line_total: 10,
  is_controlled: false,
};

// Item with a flat EGP per-line discount
const discountedItem = {
  drug_code: "IBU400",
  drug_name: "Ibuprofen 400mg",
  batch_number: null,
  expiry_date: null,
  quantity: 2,
  unit_price: 20,
  discount: 5, // 5 EGP flat discount (not percent)
  line_total: 35, // 2*20 - 5
  is_controlled: false,
};

describe("pos-cart-store", () => {
  it("adds item", () => {
    usePosCartStore.getState().addItem(item);
    expect(usePosCartStore.getState().items).toHaveLength(1);
    expect(usePosCartStore.getState().items[0].drug_code).toBe("PARA500");
  });

  it("stacks quantity for existing drug_code", () => {
    usePosCartStore.getState().addItem(item);
    usePosCartStore.getState().addItem(item);
    const items = usePosCartStore.getState().items;
    expect(items).toHaveLength(1);
    expect(items[0].quantity).toBe(2);
    // line_total = qty * unit_price - discount = 2*10 - 0 = 20
    expect(items[0].line_total).toBe(20);
  });

  it("stacks correctly with non-zero discount (EGP flat)", () => {
    usePosCartStore.getState().addItem(discountedItem);
    usePosCartStore.getState().addItem({ ...discountedItem, quantity: 1, line_total: 15 });
    const items = usePosCartStore.getState().items;
    expect(items).toHaveLength(1);
    // total qty = 2+1 = 3; line_total = 3*20 - 5 = 55
    expect(items[0].quantity).toBe(3);
    expect(items[0].line_total).toBe(55);
  });

  it("removes item", () => {
    usePosCartStore.getState().addItem(item);
    usePosCartStore.getState().removeItem("PARA500");
    expect(usePosCartStore.getState().items).toHaveLength(0);
  });

  it("removing last item nulls appliedDiscount", () => {
    usePosCartStore.getState().addItem(item);
    usePosCartStore
      .getState()
      .applyDiscount({ source: "voucher", ref: "CODE", label: "CODE", discountAmount: 5 });
    usePosCartStore.getState().removeItem("PARA500");
    expect(usePosCartStore.getState().items).toHaveLength(0);
    expect(usePosCartStore.getState().appliedDiscount).toBeNull();
  });

  it("updates quantity and recalculates line_total with EGP flat discount", () => {
    usePosCartStore.getState().addItem(discountedItem);
    usePosCartStore.getState().updateQuantity("IBU400", 4);
    const updated = usePosCartStore.getState().items[0];
    expect(updated.quantity).toBe(4);
    // line_total = 4*20 - 5 = 75
    expect(updated.line_total).toBe(75);
  });

  it("updateQuantity <= 0 removes the item", () => {
    usePosCartStore.getState().addItem(item);
    usePosCartStore.getState().updateQuantity("PARA500", 0);
    expect(usePosCartStore.getState().items).toHaveLength(0);
  });

  it("updateQuantity <= 0 nulls appliedDiscount when cart becomes empty", () => {
    usePosCartStore.getState().addItem(item);
    usePosCartStore
      .getState()
      .applyDiscount({ source: "voucher", ref: "V", label: "V", discountAmount: 2 });
    usePosCartStore.getState().updateQuantity("PARA500", 0);
    expect(usePosCartStore.getState().appliedDiscount).toBeNull();
  });

  it("applies discount", () => {
    const discount = {
      source: "voucher" as const,
      ref: "SAVE10",
      label: "SAVE10",
      discountAmount: 10,
    };
    usePosCartStore.getState().applyDiscount(discount);
    expect(usePosCartStore.getState().appliedDiscount?.ref).toBe("SAVE10");
  });

  it("clears discount", () => {
    usePosCartStore
      .getState()
      .applyDiscount({ source: "voucher" as const, ref: "X", label: "X", discountAmount: 5 });
    usePosCartStore.getState().clearDiscount();
    expect(usePosCartStore.getState().appliedDiscount).toBeNull();
  });

  it("clears cart", () => {
    usePosCartStore.getState().addItem(item);
    usePosCartStore.getState().clear();
    expect(usePosCartStore.getState().items).toHaveLength(0);
    expect(usePosCartStore.getState().appliedDiscount).toBeNull();
  });

  it("subtotal sums gross (quantity * unit_price, before line discount)", () => {
    usePosCartStore.getState().addItem(item); // 1*10 = 10
    usePosCartStore.getState().addItem(discountedItem); // 2*20 = 40 gross
    // subtotal = 10 + 40 = 50 (gross)
    expect(usePosCartStore.getState().subtotal()).toBe(50);
  });

  it("itemDiscountTotal sums discount field directly", () => {
    usePosCartStore.getState().addItem(item); // discount = 0
    usePosCartStore.getState().addItem(discountedItem); // discount = 5
    expect(usePosCartStore.getState().itemDiscountTotal()).toBe(5);
  });

  it("cartDiscountTotal returns applied discount amount", () => {
    usePosCartStore
      .getState()
      .applyDiscount({ source: "promotion", ref: "PROMO1", label: "Promo", discountAmount: 15 });
    expect(usePosCartStore.getState().cartDiscountTotal()).toBe(15);
  });

  it("voucherDiscount is 0 when source is promotion", () => {
    usePosCartStore
      .getState()
      .applyDiscount({ source: "promotion", ref: "PROMO1", label: "Promo", discountAmount: 15 });
    expect(usePosCartStore.getState().voucherDiscount()).toBe(0);
  });

  it("voucherDiscount returns amount when source is voucher", () => {
    usePosCartStore
      .getState()
      .applyDiscount({ source: "voucher", ref: "CODE", label: "CODE", discountAmount: 10 });
    expect(usePosCartStore.getState().voucherDiscount()).toBe(10);
  });

  it("grandTotal = max(0, subtotal - discountTotal)", () => {
    usePosCartStore.getState().addItem(item); // gross 10, line discount 0
    usePosCartStore
      .getState()
      .applyDiscount({ source: "voucher", ref: "V", label: "V", discountAmount: 3 });
    // subtotal = 10, itemDiscountTotal = 0, cartDiscount = 3, discountTotal = 3
    // grandTotal = 10 - 3 = 7
    expect(usePosCartStore.getState().grandTotal()).toBe(7);
  });

  it("hasControlledSubstance is true when any item is controlled", () => {
    usePosCartStore.getState().addItem(item); // not controlled
    usePosCartStore
      .getState()
      .addItem({ ...item, drug_code: "MORPH10", is_controlled: true, line_total: 10 });
    expect(usePosCartStore.getState().hasControlledSubstance()).toBe(true);
  });

  it("hasControlledSubstance is false when no controlled items", () => {
    usePosCartStore.getState().addItem(item);
    expect(usePosCartStore.getState().hasControlledSubstance()).toBe(false);
  });
});
