import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { fetchAPI, swrKey } from "@/lib/api-client";

vi.mock("next-auth/react", () => ({
  getSession: vi.fn().mockResolvedValue(null),
}));

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

describe("fetchAPI decimal parsing", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("parses scientific-notation numeric strings from API responses", async () => {
    vi.mocked(fetch).mockResolvedValue({
      ok: true,
      json: async () => ({
        tiny: "1e-5",
        large: "2.5E+3",
      }),
    } as Response);

    const result = await fetchAPI<{ tiny: number; large: number }>("/metrics");

    expect(result).toEqual({
      tiny: 0.00001,
      large: 2500,
    });
  });

  it("parses decimal strings while preserving unsafe integer strings", async () => {
    vi.mocked(fetch).mockResolvedValue({
      ok: true,
      json: async () => ({
        growth_pct: "15.25",
        nested: {
          pct_of_total: "35.2",
          huge_id: "9007199254740993",
        },
        points: [{ value: "1234.56" }],
      }),
    } as Response);

    const result = await fetchAPI<{
      growth_pct: number;
      nested: { pct_of_total: number; huge_id: string };
      points: Array<{ value: number }>;
    }>("/metrics");

    expect(result).toEqual({
      growth_pct: 15.25,
      nested: {
        pct_of_total: 35.2,
        huge_id: "9007199254740993",
      },
      points: [{ value: 1234.56 }],
    });
  });
});
