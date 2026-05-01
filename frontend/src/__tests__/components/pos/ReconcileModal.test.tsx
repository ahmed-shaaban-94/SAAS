import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

vi.mock("@pos/lib/offline-db", async () => {
  const actual = await vi.importActual<typeof import("@pos/lib/offline-db")>(
    "@pos/lib/offline-db",
  );
  return {
    ...actual,
    reconcileQueue: vi.fn(),
  };
});

import { reconcileQueue } from "@pos/lib/offline-db";
import { ReconcileModal } from "@pos/components/ReconcileModal";
import type { QueueRow } from "@pos/lib/ipc";

const reconcile = vi.mocked(reconcileQueue);

function makeRow(overrides: Partial<QueueRow> = {}): QueueRow {
  return {
    local_id: "local-1",
    client_txn_id: "ctx-1",
    endpoint: "/api/v1/pos/transactions/commit",
    status: "rejected",
    confirmation: "provisional",
    retry_count: 2,
    last_error: "duplicate override consumed",
    next_attempt_at: null,
    signed_at: "2026-04-19T10:00:00Z",
    created_at: "2026-04-19T10:00:00Z",
    updated_at: "2026-04-19T10:00:00Z",
    ...overrides,
  };
}

describe("ReconcileModal", () => {
  beforeEach(() => {
    reconcile.mockReset();
    reconcile.mockResolvedValue({
      status: "reconciled",
      confirmation: "reconciled",
      reconciled_at: "2026-04-19T10:10:00Z",
    });
  });

  it("shows the last_error prominently when present", () => {
    render(
      <ReconcileModal
        row={makeRow()}
        kind="record_loss"
        onSuccess={vi.fn()}
        onCancel={vi.fn()}
      />,
    );
    expect(screen.getByText(/duplicate override consumed/i)).toBeInTheDocument();
  });

  it("Cancel button fires onCancel", async () => {
    const onCancel = vi.fn();
    render(
      <ReconcileModal
        row={makeRow()}
        kind="record_loss"
        onSuccess={vi.fn()}
        onCancel={onCancel}
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: /^cancel$/i }));
    expect(onCancel).toHaveBeenCalled();
  });

  describe("record_loss", () => {
    it("renders a note field but no override code field", () => {
      render(
        <ReconcileModal
          row={makeRow()}
          kind="record_loss"
          onSuccess={vi.fn()}
          onCancel={vi.fn()}
        />,
      );
      expect(screen.getByLabelText(/note/i)).toBeInTheDocument();
      expect(screen.queryByLabelText(/override code/i)).not.toBeInTheDocument();
    });

    it("submit is disabled until note is valid", async () => {
      render(
        <ReconcileModal
          row={makeRow()}
          kind="record_loss"
          onSuccess={vi.fn()}
          onCancel={vi.fn()}
        />,
      );
      const submit = screen.getByRole("button", { name: /record as loss/i });
      expect(submit).toBeDisabled();
      await userEvent.type(screen.getByLabelText(/note/i), "lost");
      expect(submit).not.toBeDisabled();
    });

    it("submits with null overrideCode and fires onSuccess", async () => {
      const onSuccess = vi.fn();
      render(
        <ReconcileModal
          row={makeRow()}
          kind="record_loss"
          onSuccess={onSuccess}
          onCancel={vi.fn()}
        />,
      );
      await userEvent.type(screen.getByLabelText(/note/i), "abandon it");
      await userEvent.click(screen.getByRole("button", { name: /record as loss/i }));
      await waitFor(() => {
        expect(reconcile).toHaveBeenCalledWith(
          "local-1",
          "record_loss",
          "abandon it",
          null,
        );
        expect(onSuccess).toHaveBeenCalled();
      });
    });
  });

  describe("retry_override", () => {
    it("renders both override code and note fields", () => {
      render(
        <ReconcileModal
          row={makeRow()}
          kind="retry_override"
          onSuccess={vi.fn()}
          onCancel={vi.fn()}
        />,
      );
      expect(screen.getByLabelText(/override code/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/note/i)).toBeInTheDocument();
    });

    it("submit disabled until both note and 6-char override are valid", async () => {
      render(
        <ReconcileModal
          row={makeRow()}
          kind="retry_override"
          onSuccess={vi.fn()}
          onCancel={vi.fn()}
        />,
      );
      const submit = screen.getByRole("button", { name: /retry with override/i });
      expect(submit).toBeDisabled();
      await userEvent.type(screen.getByLabelText(/note/i), "trying again");
      expect(submit).toBeDisabled();
      await userEvent.type(screen.getByLabelText(/override code/i), "ABC12");
      expect(submit).toBeDisabled();
      await userEvent.type(screen.getByLabelText(/override code/i), "3");
      expect(submit).not.toBeDisabled();
    });

    it("submits with the override code included", async () => {
      const onSuccess = vi.fn();
      render(
        <ReconcileModal
          row={makeRow()}
          kind="retry_override"
          onSuccess={onSuccess}
          onCancel={vi.fn()}
        />,
      );
      await userEvent.type(screen.getByLabelText(/note/i), "trying again");
      await userEvent.type(screen.getByLabelText(/override code/i), "abc123");
      await userEvent.click(screen.getByRole("button", { name: /retry with override/i }));
      await waitFor(() => {
        expect(reconcile).toHaveBeenCalledWith(
          "local-1",
          "retry_override",
          "trying again",
          "ABC123",
        );
        expect(onSuccess).toHaveBeenCalled();
      });
    });

    it("surfaces reconcile errors inline", async () => {
      reconcile.mockRejectedValueOnce(new Error("override expired"));
      render(
        <ReconcileModal
          row={makeRow()}
          kind="retry_override"
          onSuccess={vi.fn()}
          onCancel={vi.fn()}
        />,
      );
      await userEvent.type(screen.getByLabelText(/note/i), "retrying");
      await userEvent.type(screen.getByLabelText(/override code/i), "ABC123");
      await userEvent.click(screen.getByRole("button", { name: /retry with override/i }));
      await waitFor(() => {
        expect(screen.getByText(/override expired/i)).toBeInTheDocument();
      });
    });
  });

  describe("corrective_void", () => {
    it("renders a note field only", () => {
      render(
        <ReconcileModal
          row={makeRow()}
          kind="corrective_void"
          onSuccess={vi.fn()}
          onCancel={vi.fn()}
        />,
      );
      expect(screen.getByLabelText(/note/i)).toBeInTheDocument();
      expect(screen.queryByLabelText(/override code/i)).not.toBeInTheDocument();
    });

    it("submits with null overrideCode", async () => {
      const onSuccess = vi.fn();
      render(
        <ReconcileModal
          row={makeRow()}
          kind="corrective_void"
          onSuccess={onSuccess}
          onCancel={vi.fn()}
        />,
      );
      await userEvent.type(screen.getByLabelText(/note/i), "compensate");
      await userEvent.click(screen.getByRole("button", { name: /issue corrective void/i }));
      await waitFor(() => {
        expect(reconcile).toHaveBeenCalledWith(
          "local-1",
          "corrective_void",
          "compensate",
          null,
        );
        expect(onSuccess).toHaveBeenCalled();
      });
    });
  });
});
