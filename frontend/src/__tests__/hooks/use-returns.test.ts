import { describe, it, expect } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { SWRConfig } from "swr";
import React from "react";
import { useReturns } from "@/hooks/use-returns";

function wrapper({ children }: { children: React.ReactNode }) {
  return React.createElement(SWRConfig, { value: { dedupingInterval: 0, provider: () => new Map() } }, children);
}

describe("useReturns", () => {
  it("fetches returns data", async () => {
    const { result } = renderHook(() => useReturns(), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.data).toHaveLength(1);
    expect(result.current.data?.[0].product_name).toBe("Drug X");
    expect(result.current.data?.[0].return_rate).toBe(3.2);
  });
});
