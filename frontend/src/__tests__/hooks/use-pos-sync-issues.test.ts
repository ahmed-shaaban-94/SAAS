import { describe, it, expect, vi, beforeEach } from "vitest";
import { act, renderHook, waitFor } from "@testing-library/react";
import { SWRConfig } from "swr";
import React from "react";

vi.mock("@pos/lib/offline-db", () => ({
  getRejectedQueue: vi.fn(),
  reconcileQueue: vi.fn(),
}));

import { getRejectedQueue, reconcileQueue } from "@pos/lib/offline-db";
import { usePosSyncIssues } from "@pos/hooks/use-pos-sync-issues";
import type { QueueRow } from "@pos/lib/ipc";

const getRejected = vi.mocked(getRejectedQueue);
const reconcile = vi.mocked(reconcileQueue);

function wrapper({ children }: { children: React.ReactNode }) {
  return React.createElement(
    SWRConfig,
    { value: { dedupingInterval: 0, provider: () => new Map() } },
    children,
  );
}

function row(local_id: string, overrides: Partial<QueueRow> = {}): QueueRow {
  return {
    local_id,
    client_txn_id: `ctx-${local_id}`,
    endpoint: "/api/v1/pos/transactions/commit",
    status: "rejected",
    confirmation: "provisional",
    retry_count: 1,
    last_error: "server rejected",
    next_attempt_at: null,
    signed_at: "2026-04-19T10:00:00Z",
    created_at: "2026-04-19T10:00:00Z",
    updated_at: "2026-04-19T10:00:00Z",
    ...overrides,
  };
}

describe("usePosSyncIssues", () => {
  beforeEach(() => {
    getRejected.mockReset();
    reconcile.mockReset();
  });

  it("returns an empty array when adapter returns none", async () => {
    getRejected.mockResolvedValue([]);
    const { result } = renderHook(() => usePosSyncIssues(), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.items).toEqual([]);
    expect(result.current.isError).toBe(false);
  });

  it("surfaces rejected queue rows from the adapter", async () => {
    getRejected.mockResolvedValue([row("a"), row("b")]);
    const { result } = renderHook(() => usePosSyncIssues(), { wrapper });
    await waitFor(() => expect(result.current.items).toHaveLength(2));
    expect(result.current.items[0].local_id).toBe("a");
  });

  it("reconcile calls the adapter and refreshes the list", async () => {
    getRejected.mockResolvedValueOnce([row("a")]);
    reconcile.mockResolvedValue({
      status: "reconciled",
      confirmation: "reconciled",
      reconciled_at: "2026-04-19T10:05:00Z",
    });
    const { result } = renderHook(() => usePosSyncIssues(), { wrapper });
    await waitFor(() => expect(result.current.items).toHaveLength(1));

    getRejected.mockResolvedValueOnce([]);
    await act(async () => {
      const res = await result.current.reconcile("a", "record_loss", "lost", null);
      expect(res.status).toBe("reconciled");
    });

    expect(reconcile).toHaveBeenCalledWith("a", "record_loss", "lost", null);
    await waitFor(() => expect(result.current.items).toHaveLength(0));
  });

  it("reconcile failure propagates to the caller", async () => {
    getRejected.mockResolvedValue([row("a")]);
    reconcile.mockRejectedValue(new Error("bad override"));
    const { result } = renderHook(() => usePosSyncIssues(), { wrapper });
    await waitFor(() => expect(result.current.items).toHaveLength(1));

    await expect(
      result.current.reconcile("a", "retry_override", "try again", "ABC123"),
    ).rejects.toThrow("bad override");
  });

  it("defaults overrideCode to null when omitted", async () => {
    getRejected.mockResolvedValue([row("a")]);
    reconcile.mockResolvedValue({
      status: "reconciled",
      confirmation: "reconciled",
      reconciled_at: "2026-04-19T10:05:00Z",
    });
    const { result } = renderHook(() => usePosSyncIssues(), { wrapper });
    await waitFor(() => expect(result.current.items).toHaveLength(1));

    await act(async () => {
      await result.current.reconcile("a", "record_loss", "note ok");
    });
    expect(reconcile).toHaveBeenCalledWith("a", "record_loss", "note ok", null);
  });
});
