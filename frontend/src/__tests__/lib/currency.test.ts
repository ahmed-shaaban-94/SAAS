import { describe, it, expect } from "vitest";
import { formatPrice } from "@/lib/currency";

describe("formatPrice", () => {
  it("formats USD piastres-equivalent (cents) correctly in en-US", () => {
    expect(formatPrice(4900, "USD", "en")).toBe("$49.00");
  });

  it("formats EGP piastres with Arabic digits in ar", () => {
    // 149900 piastres = 1,499 EGP
    const out = formatPrice(149900, "EGP", "ar");
    expect(out).toMatch(/١٬?٤٩٩|1,499/);
    expect(out).toMatch(/ج\.م|EGP/);
  });

  it("zero is rendered", () => {
    expect(formatPrice(0, "USD", "en")).toBe("$0.00");
  });

  it("unknown currency falls back to ISO code", () => {
    expect(formatPrice(1000, "XYZ", "en")).toContain("XYZ");
  });
});
