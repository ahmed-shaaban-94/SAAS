import { describe, it, expect } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { SWRConfig } from "swr";
import React from "react";
import { useQualityScorecard } from "@/hooks/use-quality-scorecard";
import { useAuditLog } from "@/hooks/use-audit-log";
import { useStaffQuota } from "@/hooks/use-staff-quota";
import { useLineage } from "@/hooks/use-lineage";

function wrapper({ children }: { children: React.ReactNode }) {
  return React.createElement(SWRConfig, { value: { dedupingInterval: 0, provider: () => new Map() } }, children);
}

describe("useQualityScorecard", () => {
  it("fetches scorecard data", async () => {
    const { result } = renderHook(() => useQualityScorecard(), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.data.overall_pass_rate).toBe(90.0);
    expect(result.current.data.runs).toHaveLength(1);
  });

  it("starts in loading state", () => {
    const { result } = renderHook(() => useQualityScorecard(), { wrapper });
    expect(result.current.isLoading).toBe(true);
  });
});

describe("useAuditLog", () => {
  it("fetches audit log entries", async () => {
    const { result } = renderHook(() => useAuditLog(), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.data?.items).toHaveLength(1);
    expect(result.current.data?.total).toBe(1);
  });
});

describe("useStaffQuota", () => {
  it("fetches staff quota data", async () => {
    const { result } = renderHook(() => useStaffQuota(), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.data).toHaveLength(1);
    expect(result.current.data[0].staff_name).toBe("Ahmed");
  });
});

describe("useLineage", () => {
  it("fetches lineage graph", async () => {
    const { result } = renderHook(() => useLineage(), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.data?.nodes).toHaveLength(2);
    expect(result.current.data?.edges).toHaveLength(1);
  });
});
