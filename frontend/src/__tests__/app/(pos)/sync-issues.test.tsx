import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";

vi.mock("@/hooks/use-pos-sync-issues", () => ({
  usePosSyncIssues: vi.fn(),
}));

vi.mock("@/lib/pos/ipc", async () => {
  const actual = await vi.importActual<typeof import("@/lib/pos/ipc")>("@/lib/pos/ipc");
  return {
    ...actual,
    hasElectron: vi.fn(),
  };
});

// Simple stand-in for the modal — lets us assert on the kind prop without
// exercising reconcileQueue a second time (that's already covered by
// ReconcileModal.test.tsx).
vi.mock("@/components/pos/ReconcileModal", () => ({
  ReconcileModal: ({
    kind,
    onCancel,
  }: {
    kind: string;
    onCancel: () => void;
  }) =>
    React.createElement(
      "div",
      { "data-testid": "reconcile-modal", "data-kind": kind },
      React.createElement(
        "button",
        { type: "button", onClick: onCancel },
        "close-modal",
      ),
    ),
}));

import { usePosSyncIssues } from "@/hooks/use-pos-sync-issues";
import { hasElectron } from "@/lib/pos/ipc";
import PosSyncIssuesPage from "@/app/(pos)/sync-issues/page";
import type { QueueRow } from "@/lib/pos/ipc";

const mockedHook = vi.mocked(usePosSyncIssues);
const mockedHasElectron = vi.mocked(hasElectron);

function row(local_id: string, overrides: Partial<QueueRow> = {}): QueueRow {
  return {
    local_id,
    client_txn_id: `ctx-${local_id}`,
    endpoint: "/api/v1/pos/transactions/commit",
    status: "rejected",
    confirmation: "provisional",
    retry_count: 1,
    last_error: "server said no",
    next_attempt_at: null,
    signed_at: "2026-04-19T10:00:00Z",
    created_at: "2026-04-19T10:00:00Z",
    updated_at: "2026-04-19T10:00:00Z",
    ...overrides,
  };
}

function setHook(overrides: Partial<ReturnType<typeof usePosSyncIssues>> = {}) {
  mockedHook.mockReturnValue({
    items: [],
    isLoading: false,
    isError: false,
    mutate: vi.fn().mockResolvedValue(undefined),
    reconcile: vi.fn(),
    ...overrides,
  });
}

describe("PosSyncIssuesPage", () => {
  beforeEach(() => {
    mockedHook.mockReset();
    mockedHasElectron.mockReset();
    mockedHasElectron.mockReturnValue(true);
  });

  it("shows the browser-only banner when not running in Electron", () => {
    mockedHasElectron.mockReturnValue(false);
    setHook();
    render(<PosSyncIssuesPage />);
    expect(
      screen.getByText(/only available in the desktop app/i),
    ).toBeInTheDocument();
  });

  it("renders a loading skeleton while loading with no items yet", () => {
    setHook({ isLoading: true, items: [] });
    render(<PosSyncIssuesPage />);
    expect(screen.getByTestId("sync-issues-skeleton")).toBeInTheDocument();
  });

  it("renders the empty-state 'shift can be closed' message", () => {
    setHook({ isLoading: false, items: [] });
    render(<PosSyncIssuesPage />);
    expect(screen.getByText(/no unresolved sync issues/i)).toBeInTheDocument();
    expect(screen.getByText(/shift can be closed/i)).toBeInTheDocument();
  });

  it("renders one card per rejected row", () => {
    setHook({ items: [row("a"), row("b"), row("c")] });
    render(<PosSyncIssuesPage />);
    expect(screen.getAllByText(/^rejected$/i)).toHaveLength(3);
  });

  it("clicking 'Retry with override' opens the modal with retry_override kind", async () => {
    setHook({ items: [row("a")] });
    render(<PosSyncIssuesPage />);
    await userEvent.click(screen.getByRole("button", { name: /retry with override/i }));
    const modal = await screen.findByTestId("reconcile-modal");
    expect(modal).toHaveAttribute("data-kind", "retry_override");
  });

  it("clicking 'Record as loss' opens the modal with record_loss kind", async () => {
    setHook({ items: [row("a")] });
    render(<PosSyncIssuesPage />);
    await userEvent.click(screen.getByRole("button", { name: /record as loss/i }));
    const modal = await screen.findByTestId("reconcile-modal");
    expect(modal).toHaveAttribute("data-kind", "record_loss");
  });

  it("clicking 'Corrective void' opens the modal with corrective_void kind", async () => {
    setHook({ items: [row("a")] });
    render(<PosSyncIssuesPage />);
    await userEvent.click(screen.getByRole("button", { name: /corrective void/i }));
    const modal = await screen.findByTestId("reconcile-modal");
    expect(modal).toHaveAttribute("data-kind", "corrective_void");
  });
});
