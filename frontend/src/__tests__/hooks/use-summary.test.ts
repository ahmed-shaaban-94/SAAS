import { describe, it, expect } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { SWRConfig } from "swr";
import React from "react";
import { useSummary } from "@/hooks/use-summary";

function wrapper({ children }: { children: React.ReactNode }) {
  return React.createElement(SWRConfig, { value: { dedupingInterval: 0, provider: () => new Map() } }, children);
}

describe("useSummary", () => {
  it("fetches summary data", async () => {
    const { result } = renderHook(() => useSummary(), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.data).toBeDefined();
    expect(result.current.data?.today_net).toBe(125000);
    expect(result.current.data?.mtd_net).toBe(3500000);
    expect(result.current.data?.ytd_net).toBe(42000000);
  });

  it("passes target_date from filters end_date", async () => {
    const { result } = renderHook(
      () => useSummary({ end_date: "2024-06-30" }),
      { wrapper },
    );
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.data).toBeDefined();
  });

  it("starts in loading state", () => {
    const { result } = renderHook(() => useSummary(), { wrapper });
    expect(result.current.isLoading).toBe(true);
  });
});
