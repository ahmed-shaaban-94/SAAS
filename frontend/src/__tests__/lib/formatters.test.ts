import { describe, it, expect } from "vitest";
import { formatCurrency, formatPercent, formatNumber, formatCompact, formatDuration, truncate } from "@/lib/formatters";

describe("formatCurrency", () => {
  it("formats positive numbers with EGP prefix", () => {
    expect(formatCurrency(1500000)).toContain("1,500,000");
    expect(formatCurrency(1500000)).toContain("EGP");
  });

  it("formats zero", () => {
    expect(formatCurrency(0)).toContain("0");
  });

  it("returns N/A for null", () => {
    expect(formatCurrency(null)).toBe("N/A");
  });

  it("returns N/A for undefined", () => {
    expect(formatCurrency(undefined)).toBe("N/A");
  });

  it("formats negative numbers", () => {
    const result = formatCurrency(-5000);
    expect(result).toContain("5,000");
  });
});

describe("formatPercent", () => {
  it("formats positive with + prefix", () => {
    expect(formatPercent(15.5)).toBe("+15.5%");
  });

  it("formats negative without + prefix", () => {
    expect(formatPercent(-8.2)).toBe("-8.2%");
  });

  it("formats zero", () => {
    expect(formatPercent(0)).toBe("0.0%");
  });

  it("returns N/A for null", () => {
    expect(formatPercent(null)).toBe("N/A");
  });

  it("returns N/A for undefined", () => {
    expect(formatPercent(undefined)).toBe("N/A");
  });
});

describe("formatNumber", () => {
  it("formats with commas", () => {
    expect(formatNumber(1234567)).toBe("1,234,567");
  });

  it("returns N/A for null", () => {
    expect(formatNumber(null)).toBe("N/A");
  });

  it("formats zero", () => {
    expect(formatNumber(0)).toBe("0");
  });
});

describe("formatCompact", () => {
  it("formats millions", () => {
    expect(formatCompact(1500000)).toBe("1.5M");
  });

  it("formats thousands", () => {
    expect(formatCompact(45000)).toBe("45K");
  });

  it("formats small numbers as-is", () => {
    expect(formatCompact(500)).toBe("500");
  });

  it("returns N/A for null", () => {
    expect(formatCompact(null)).toBe("N/A");
  });

  it("handles negative millions", () => {
    expect(formatCompact(-2000000)).toBe("-2.0M");
  });

  it("handles negative thousands", () => {
    expect(formatCompact(-5000)).toBe("-5K");
  });
});

describe("formatDuration", () => {
  it("formats seconds only", () => {
    expect(formatDuration(45)).toBe("45s");
  });

  it("formats minutes and seconds", () => {
    expect(formatDuration(125)).toBe("2m 5s");
  });

  it("formats exact minutes", () => {
    expect(formatDuration(120)).toBe("2m");
  });

  it("returns dash for null", () => {
    expect(formatDuration(null)).toBe("-");
  });
});

describe("truncate", () => {
  it("truncates long strings", () => {
    expect(truncate("This is a very long string", 10)).toBe("This is a ...");
  });

  it("does not truncate short strings", () => {
    expect(truncate("Short")).toBe("Short");
  });

  it("uses default max length of 20", () => {
    const str = "A".repeat(25);
    expect(truncate(str)).toBe("A".repeat(20) + "...");
  });
});
