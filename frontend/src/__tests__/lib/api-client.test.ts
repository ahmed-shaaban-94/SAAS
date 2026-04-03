import { describe, it, expect, vi, beforeEach } from "vitest";
import { swrKey } from "@/lib/api-client";

describe("swrKey", () => {
  it("returns path alone when no params", () => {
    expect(swrKey("/api/v1/analytics/summary")).toBe("/api/v1/analytics/summary");
  });

  it("returns path alone when params are undefined", () => {
    expect(swrKey("/api/v1/analytics/summary", undefined)).toBe("/api/v1/analytics/summary");
  });

  it("appends sorted query params", () => {
    const result = swrKey("/api/v1/analytics/summary", {
      end_date: "2024-12-31",
      start_date: "2024-01-01",
    });
    // Params should be sorted alphabetically
    expect(result).toContain("end_date=2024-12-31");
    expect(result).toContain("start_date=2024-01-01");
    expect(result.indexOf("end_date")).toBeLessThan(result.indexOf("start_date"));
  });

  it("ignores null/undefined values", () => {
    const result = swrKey("/api/v1/analytics/summary", {
      start_date: "2024-01-01",
      category: undefined,
      brand: null as unknown as string,
    });
    expect(result).not.toContain("category");
    expect(result).not.toContain("brand");
    expect(result).toContain("start_date=2024-01-01");
  });

  it("returns path only when all params are null/undefined", () => {
    const result = swrKey("/test", {
      category: undefined,
    });
    expect(result).toBe("/test");
  });
});
