import { describe, it, expect } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { SWRConfig } from "swr";
import React from "react";
import { usePipelineRuns } from "@/hooks/use-pipeline-runs";

function wrapper({ children }: { children: React.ReactNode }) {
  return React.createElement(SWRConfig, { value: { dedupingInterval: 0, provider: () => new Map() } }, children);
}

describe("usePipelineRuns", () => {
  it("fetches pipeline runs list", async () => {
    const { result } = renderHook(() => usePipelineRuns({ limit: 50 }), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.data?.items).toHaveLength(2);
    expect(result.current.data?.items[0].status).toBe("success");
    expect(result.current.data?.items[1].status).toBe("failed");
    expect(result.current.data?.total).toBe(2);
  });

  it("provides mutate function", async () => {
    const { result } = renderHook(() => usePipelineRuns(), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.mutate).toBeDefined();
  });
});
