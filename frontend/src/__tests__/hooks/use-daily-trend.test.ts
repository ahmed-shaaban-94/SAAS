import { describe, it, expect } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { SWRConfig } from "swr";
import React from "react";
import { useDailyTrend } from "@/hooks/use-daily-trend";

function wrapper({ children }: { children: React.ReactNode }) {
  return React.createElement(SWRConfig, { value: { dedupingInterval: 0, provider: () => new Map() } }, children);
}

describe("useDailyTrend", () => {
  it("fetches daily trend data", async () => {
    const { result } = renderHook(() => useDailyTrend(), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.data?.points).toHaveLength(3);
    expect(result.current.data?.total).toBe(335000);
    expect(result.current.data?.growth_pct).toBe(15.0);
  });

  it("passes date range filters", async () => {
    const { result } = renderHook(
      () => useDailyTrend({ start_date: "2024-01-01", end_date: "2024-03-31" }),
      { wrapper },
    );
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.data?.points).toBeDefined();
  });
});
