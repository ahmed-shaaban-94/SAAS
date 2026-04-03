import { describe, it, expect } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { SWRConfig } from "swr";
import React from "react";
import { useHealth } from "@/hooks/use-health";

function wrapper({ children }: { children: React.ReactNode }) {
  return React.createElement(SWRConfig, { value: { dedupingInterval: 0, provider: () => new Map() } }, children);
}

describe("useHealth", () => {
  it("returns healthy data on success", async () => {
    const { result } = renderHook(() => useHealth(), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.data).toBeDefined();
    expect(result.current.data?.status).toBe("healthy");
    expect(result.current.error).toBeUndefined();
  });

  it("starts in loading state", () => {
    const { result } = renderHook(() => useHealth(), { wrapper });
    expect(result.current.isLoading).toBe(true);
    expect(result.current.data).toBeUndefined();
  });
});
