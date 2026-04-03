import { describe, it, expect } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { SWRConfig } from "swr";
import React from "react";
import { useTopProducts } from "@/hooks/use-top-products";

function wrapper({ children }: { children: React.ReactNode }) {
  return React.createElement(SWRConfig, { value: { dedupingInterval: 0, provider: () => new Map() } }, children);
}

describe("useTopProducts", () => {
  it("fetches top products ranking", async () => {
    const { result } = renderHook(() => useTopProducts(), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.data?.items).toHaveLength(3);
    expect(result.current.data?.items[0].name).toBe("Product A");
    expect(result.current.data?.items[0].rank).toBe(1);
    expect(result.current.data?.total).toBe(1420000);
  });

  it("passes filter params", async () => {
    const { result } = renderHook(
      () => useTopProducts({ category: "Pharma", limit: 5 }),
      { wrapper },
    );
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.data).toBeDefined();
  });
});
