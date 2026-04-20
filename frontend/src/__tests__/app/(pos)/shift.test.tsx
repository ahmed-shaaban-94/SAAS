import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { TerminalSessionResponse } from "@/types/pos";

vi.mock("@/hooks/use-pos-terminal", () => ({
  openTerminal: vi.fn(),
  closeTerminal: vi.fn(),
}));

import { closeTerminal } from "@/hooks/use-pos-terminal";
import ShiftPage from "@/app/(pos)/shift/page";

const mockedClose = vi.mocked(closeTerminal);

const TERMINAL: TerminalSessionResponse = {
  id: 42,
  tenant_id: 1,
  site_code: "ALEX-001",
  staff_id: "nour.m",
  terminal_name: "POS-03",
  status: "open",
  opened_at: "2026-04-20T08:00:00Z",
  closed_at: null,
  opening_cash: 2000,
  closing_cash: null,
};

const originalPrint = window.print;

describe("ShiftPage (#469 redesign)", () => {
  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem("pos:active_terminal", JSON.stringify(TERMINAL));
    mockedClose.mockReset();
    window.print = vi.fn();
  });

  afterEach(() => {
    window.print = originalPrint;
    vi.restoreAllMocks();
  });

  it("renders the Active Terminal summary when a shift is open", () => {
    render(<ShiftPage />);
    expect(screen.getByText("POS-03")).toBeInTheDocument();
    expect(screen.getByText(/site: alex-001/i)).toBeInTheDocument();
  });

  it("Close Shift button switches to the reconcile view with thermal preview", async () => {
    const user = userEvent.setup();
    render(<ShiftPage />);
    await user.click(screen.getByRole("button", { name: /close shift/i }));
    expect(screen.getByTestId("shift-close-reconcile")).toBeInTheDocument();
    expect(screen.getByTestId("shift-receipt-preview")).toBeInTheDocument();
    expect(screen.getByTestId("thermal-shift-receipt")).toBeInTheDocument();
    expect(
      screen.getByText(/reconcile cash, print the report/i),
    ).toBeInTheDocument();
  });

  it("variance is color-coded red when |variance| ≥ 20", async () => {
    const user = userEvent.setup();
    render(<ShiftPage />);
    await user.click(screen.getByRole("button", { name: /close shift/i }));
    const input = screen.getByTestId("counted-cash-input");
    await user.type(input, "1500");
    const variance = screen.getByTestId("variance-display");
    expect(variance.className).toMatch(/text-destructive/);
    expect(variance.textContent).toMatch(/500\.00/);
  });

  it("variance is green when counted matches opening float exactly", async () => {
    const user = userEvent.setup();
    render(<ShiftPage />);
    await user.click(screen.getByRole("button", { name: /close shift/i }));
    const input = screen.getByTestId("counted-cash-input");
    await user.type(input, "2000");
    const variance = screen.getByTestId("variance-display");
    expect(variance.className).toMatch(/text-green-400/);
  });

  it("F4 triggers window.print from the close view", async () => {
    const user = userEvent.setup();
    render(<ShiftPage />);
    await user.click(screen.getByRole("button", { name: /close shift/i }));
    act(() => {
      window.dispatchEvent(new KeyboardEvent("keydown", { key: "F4" }));
    });
    expect(window.print).toHaveBeenCalledTimes(1);
  });

  it("Print button also triggers window.print", async () => {
    const user = userEvent.setup();
    render(<ShiftPage />);
    await user.click(screen.getByRole("button", { name: /close shift/i }));
    await user.click(screen.getByTestId("shift-print-button"));
    expect(window.print).toHaveBeenCalled();
  });

  it("Finalize button is disabled until counted cash is entered", async () => {
    const user = userEvent.setup();
    render(<ShiftPage />);
    await user.click(screen.getByRole("button", { name: /close shift/i }));
    const finalize = screen.getByTestId("shift-finalize-button");
    expect(finalize).toBeDisabled();
    await user.type(screen.getByTestId("counted-cash-input"), "2000");
    expect(finalize).not.toBeDisabled();
  });

  it("Finalize calls closeTerminal with the counted cash amount", async () => {
    mockedClose.mockResolvedValue({
      ...TERMINAL,
      status: "closed",
      closed_at: "2026-04-20T16:00:00Z",
      closing_cash: 2100,
    });
    const user = userEvent.setup();
    render(<ShiftPage />);
    await user.click(screen.getByRole("button", { name: /close shift/i }));
    await user.type(screen.getByTestId("counted-cash-input"), "2100");
    await user.click(screen.getByTestId("shift-finalize-button"));
    expect(mockedClose).toHaveBeenCalledWith(42, { closing_cash: 2100 });
  });
});
