import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { StocktakingModal } from "@pos/components/StocktakingModal";
import type { DrugRow } from "@pos/components/drugs/types";

function makeRow(overrides: Partial<DrugRow> = {}): DrugRow {
  return {
    drug_code: "MED-001",
    drug_name: "Paracetamol 500mg",
    drug_brand: "Panadol",
    is_controlled: false,
    unit_price: 25,
    stock_available: 12,
    stock_tag: "watch",
    ...overrides,
  };
}

const baseProps = {
  branchName: "DataPulse Pharmacy — Maadi",
  branchAddress: "12 Sobhi Saleh St · Maadi · Cairo",
  crNumber: "428893",
};

// jsdom does not implement window.print — stub it so components that
// call it (Print button) don't throw during tests.
const printStub = vi.fn();
Object.defineProperty(window, "print", {
  configurable: true,
  writable: true,
  value: printStub,
});

describe("StocktakingModal", () => {
  beforeEach(() => {
    printStub.mockReset();
  });

  it("renders nothing when closed", () => {
    render(
      <StocktakingModal
        open={false}
        onClose={vi.fn()}
        rows={[makeRow()]}
        {...baseProps}
      />,
    );
    expect(screen.queryByTestId("pos-stocktaking-modal")).not.toBeInTheDocument();
  });

  it("renders title, letterhead, and one row when open", () => {
    render(
      <StocktakingModal
        open
        onClose={vi.fn()}
        rows={[makeRow()]}
        {...baseProps}
      />,
    );
    expect(screen.getByTestId("pos-stocktaking-modal")).toBeInTheDocument();
    expect(screen.getByText("Stocktaking Worksheet")).toBeInTheDocument();
    expect(screen.getByText(/DataPulse Pharmacy — Maadi/)).toBeInTheDocument();
    expect(screen.getByText(/CR 428893/)).toBeInTheDocument();
    expect(screen.getByText("Paracetamol 500mg")).toBeInTheDocument();
  });

  it("produces a STK- doc number derived from today", () => {
    render(
      <StocktakingModal
        open
        onClose={vi.fn()}
        rows={[makeRow()]}
        {...baseProps}
      />,
    );
    expect(screen.getByTestId("pos-stocktaking-doc-no")).toHaveTextContent(
      /^STK-\d{6}-01$/,
    );
  });

  it("totals row sums system quantities across rows", () => {
    render(
      <StocktakingModal
        open
        onClose={vi.fn()}
        rows={[
          makeRow({ drug_code: "A", stock_available: 3 }),
          makeRow({ drug_code: "B", stock_available: 5 }),
          makeRow({ drug_code: "C", stock_available: 7 }),
        ]}
        {...baseProps}
      />,
    );
    expect(screen.getByTestId("pos-stocktaking-total-system")).toHaveTextContent("15");
    expect(screen.getByText(/3 SKUs/)).toBeInTheDocument();
  });

  it("shows an empty-state message when no rows", () => {
    render(
      <StocktakingModal
        open
        onClose={vi.fn()}
        rows={[]}
        {...baseProps}
      />,
    );
    expect(screen.getByText(/No products to count yet/)).toBeInTheDocument();
    expect(
      screen.queryByTestId("pos-stocktaking-total-system"),
    ).not.toBeInTheDocument();
  });

  it("Print button calls window.print()", async () => {
    render(
      <StocktakingModal
        open
        onClose={vi.fn()}
        rows={[makeRow()]}
        {...baseProps}
      />,
    );
    await userEvent.click(screen.getByTestId("pos-stocktaking-print-button"));
    expect(printStub).toHaveBeenCalledTimes(1);
  });

  it("Close button and Esc fire onClose", async () => {
    const onClose = vi.fn();
    render(
      <StocktakingModal
        open
        onClose={onClose}
        rows={[makeRow()]}
        {...baseProps}
      />,
    );
    await userEvent.click(screen.getByTestId("pos-stocktaking-close-button"));
    expect(onClose).toHaveBeenCalledTimes(1);

    await userEvent.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalledTimes(2);
  });

  it("uses the provided shift number in the meta grid", () => {
    render(
      <StocktakingModal
        open
        onClose={vi.fn()}
        rows={[makeRow()]}
        shiftNumber="POS-03"
        {...baseProps}
      />,
    );
    expect(screen.getByText("POS-03")).toBeInTheDocument();
  });
});
