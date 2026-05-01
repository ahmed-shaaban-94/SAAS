import { describe, it, expect } from "vitest";

import { cleanDrugName } from "@pos/lib/format-drug-name";

describe("cleanDrugName", () => {
  it("returns empty string for null/undefined/empty", () => {
    expect(cleanDrugName(null)).toBe("");
    expect(cleanDrugName(undefined)).toBe("");
    expect(cleanDrugName("")).toBe("");
  });

  it("strips wrapping #$ ... $# markers", () => {
    expect(cleanDrugName("#$CALDIN-C 30/TAB(NEW)$#")).toBe("CALDIN-C 30/TAB(NEW)");
  });

  it("strips a leading 4+ digit prefix before alphabetic chars", () => {
    expect(cleanDrugName("4321MINCEUR TEACTIVE")).toBe("MINCEUR TEACTIVE");
    expect(cleanDrugName("3238577777 PARACETAMOL 500MG")).toBe("PARACETAMOL 500MG");
  });

  it("does NOT strip short numeric prefixes (drug-strength markers)", () => {
    // "3FLY 1200" should keep the 3 — it's part of the drug name, not a SAP prefix
    expect(cleanDrugName("3FLY 1200 20/EX.RE.F.C.TAB")).toBe("3FLY 1200 20/EX.RE.F.C.TAB");
  });

  it("strips trailing #-prefixed marker tokens at end", () => {
    expect(cleanDrugName("A.BANDERAS KING #F/M100M")).toBe("A.BANDERAS KING");
  });

  it("collapses multiple dots and whitespace", () => {
    expect(cleanDrugName("FOO..BAR  BAZ")).toBe("FOO.BAR BAZ");
  });

  it("trims surrounding whitespace", () => {
    expect(cleanDrugName("   PARACETAMOL   ")).toBe("PARACETAMOL");
  });

  it("leaves a clean name unchanged", () => {
    expect(cleanDrugName("PARACETAMOL 500MG 20/TAB")).toBe("PARACETAMOL 500MG 20/TAB");
  });

  it("handles combined junk markers in one string", () => {
    expect(cleanDrugName("#$4321MINCEUR  TEA..BAG#F/X$#")).toBe("MINCEUR TEA.BAG");
  });
});
