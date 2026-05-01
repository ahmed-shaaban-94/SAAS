import { describe, it, expect } from "vitest";
import { classifyReason } from "@pos/components/sync/reason-tags";

describe("classifyReason", () => {
  it("returns UNKNOWN for null or empty error", () => {
    expect(classifyReason(null).key).toBe("UNKNOWN");
    expect(classifyReason("").key).toBe("UNKNOWN");
  });

  it("matches price mismatch messages", () => {
    expect(classifyReason("price mismatch on line 2").key).toBe("PRICE_MISMATCH");
    expect(classifyReason("Total mismatch").key).toBe("PRICE_MISMATCH");
  });

  it("matches voucher / promo messages", () => {
    expect(classifyReason("Voucher FOO expired").key).toBe("EXPIRED_VOUCHER");
    expect(classifyReason("promo rule blocked").key).toBe("EXPIRED_VOUCHER");
  });

  it("matches stock / oversold messages", () => {
    expect(classifyReason("negative inventory").key).toBe("STOCK_NEGATIVE");
    expect(classifyReason("stock shortage").key).toBe("STOCK_NEGATIVE");
    expect(classifyReason("oversold").key).toBe("STOCK_NEGATIVE");
  });

  it("matches insurance messages", () => {
    expect(classifyReason("insurance authorization denied").key).toBe("INSURANCE_REJECT");
    expect(classifyReason("Insurer rejected claim").key).toBe("INSURANCE_REJECT");
  });

  it("matches duplicate / barcode messages", () => {
    expect(classifyReason("duplicate client_txn_id").key).toBe("DUPLICATE_BARCODE");
    expect(classifyReason("barcode collision").key).toBe("DUPLICATE_BARCODE");
  });

  it("falls back to UNKNOWN for unrecognized errors", () => {
    expect(classifyReason("random gibberish").key).toBe("UNKNOWN");
  });
});
