import { describe, it, expect } from "vitest";
import { renderHook } from "@testing-library/react";
import { useLineageImpact } from "@/hooks/use-lineage-impact";

const EDGES = [
  { source: "stg_sales", target: "dim_customer" },
  { source: "stg_sales", target: "dim_product" },
  { source: "stg_sales", target: "fct_sales" },
  { source: "dim_customer", target: "fct_sales" },
  { source: "fct_sales", target: "agg_daily" },
  { source: "agg_daily", target: "agg_weekly" },
];

describe("useLineageImpact", () => {
  it("returns null when no node selected", () => {
    const { result } = renderHook(() => useLineageImpact(null, EDGES));
    expect(result.current).toBeNull();
  });

  it("returns null when edges are empty", () => {
    const { result } = renderHook(() => useLineageImpact("stg_sales", []));
    expect(result.current).toBeNull();
  });

  it("computes direct dependents at depth 1", () => {
    const { result } = renderHook(() => useLineageImpact("stg_sales", EDGES));
    expect(result.current).not.toBeNull();
    expect(result.current!.directDependents).toEqual(
      expect.arrayContaining(["dim_customer", "dim_product", "fct_sales"]),
    );
    expect(result.current!.directDependents).toHaveLength(3);
  });

  it("computes transitive dependents at depth > 1", () => {
    const { result } = renderHook(() => useLineageImpact("stg_sales", EDGES));
    expect(result.current!.transitiveDependents).toEqual(
      expect.arrayContaining(["agg_daily", "agg_weekly"]),
    );
  });

  it("computes max depth correctly", () => {
    const { result } = renderHook(() => useLineageImpact("stg_sales", EDGES));
    // stg_sales -> agg_daily(2) -> agg_weekly(3)
    expect(result.current!.maxDepth).toBe(3);
  });

  it("computes upstream dependencies", () => {
    const { result } = renderHook(() => useLineageImpact("fct_sales", EDGES));
    expect(result.current!.upstream).toEqual(
      expect.arrayContaining(["stg_sales", "dim_customer"]),
    );
  });

  it("returns empty arrays for leaf node with no downstream", () => {
    const { result } = renderHook(() => useLineageImpact("agg_weekly", EDGES));
    expect(result.current!.directDependents).toHaveLength(0);
    expect(result.current!.transitiveDependents).toHaveLength(0);
    expect(result.current!.maxDepth).toBe(0);
  });

  it("populates depthMap for all downstream nodes", () => {
    const { result } = renderHook(() => useLineageImpact("stg_sales", EDGES));
    const map = result.current!.depthMap;
    expect(map.get("dim_customer")).toBe(1);
    expect(map.get("fct_sales")).toBe(1);
    expect(map.get("agg_daily")).toBe(2);
    expect(map.get("agg_weekly")).toBe(3);
  });
});
