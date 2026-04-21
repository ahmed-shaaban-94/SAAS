import { describe, it, expect } from "vitest";
import { buildBranchRollup, type BranchRollupRow } from "@/lib/branch-rollup";

describe("buildBranchRollup", () => {
  it("maps ranking items into rollup rows, preserving name/revenue/order", () => {
    const rollup = buildBranchRollup({
      sites: {
        items: [
          { rank: 1, key: 10, name: "Branch 1", value: 500_000, pct_of_total: 0.4 },
          { rank: 2, key: 11, name: "Branch 2", value: 300_000, pct_of_total: 0.24 },
        ],
        total: 1_250_000,
      },
      reorder: [],
      calendar: [],
    });
    expect(rollup.map((r) => r.name)).toEqual(["Branch 1", "Branch 2"]);
    expect(rollup[0].revenue).toBe(500_000);
  });

  it("counts reorder alerts per site", () => {
    const rollup = buildBranchRollup({
      sites: {
        items: [
          { rank: 1, key: 10, name: "Branch 1", value: 1, pct_of_total: 0 },
          { rank: 2, key: 11, name: "Branch 2", value: 1, pct_of_total: 0 },
        ],
        total: 2,
      },
      reorder: [
        { drug_code: "A", drug_name: "a", on_hand: 0, reorder_point: 10, site_name: "Branch 1" },
        { drug_code: "B", drug_name: "b", on_hand: 1, reorder_point: 10, site_name: "Branch 1" },
        { drug_code: "C", drug_name: "c", on_hand: 0, reorder_point: 10, site_name: "Branch 2" },
      ],
      calendar: [],
    });
    expect(rollup.find((r) => r.name === "Branch 1")!.riskCount).toBe(2);
    expect(rollup.find((r) => r.name === "Branch 2")!.riskCount).toBe(1);
  });

  it("sums expiry exposure from calendar buckets <=30 days per site", () => {
    const rollup = buildBranchRollup({
      sites: {
        items: [
          { rank: 1, key: 10, name: "Branch 1", value: 1, pct_of_total: 0 },
        ],
        total: 1,
      },
      reorder: [],
      calendar: [
        { bucket: "0-7", days_out: 7, exposure_egp: 5_000, batch_count: 1, site_name: "Branch 1" },
        { bucket: "15-30", days_out: 30, exposure_egp: 3_000, batch_count: 1, site_name: "Branch 1" },
        { bucket: "31+", days_out: 60, exposure_egp: 99_999, batch_count: 1, site_name: "Branch 1" },
      ],
    });
    expect(rollup[0].expiryExposureEgp).toBe(8_000);
  });

  it("returns empty array when sites payload is undefined", () => {
    expect(buildBranchRollup({ sites: undefined, reorder: [], calendar: [] })).toEqual([]);
  });

  it("assigns trend='flat' as default when no trend source provided", () => {
    const rollup = buildBranchRollup({
      sites: {
        items: [{ rank: 1, key: 10, name: "Branch 1", value: 1, pct_of_total: 0 }],
        total: 1,
      },
      reorder: [],
      calendar: [],
    });
    expect(rollup[0].trend).toBe("flat");
  });
});
