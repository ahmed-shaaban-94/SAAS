import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { StocktakingModal, type StocktakingRow } from "@/components/pos/StocktakingModal";

function makeRow(overrides: Partial<StocktakingRow> = {}): StocktakingRow {
  return {
    drug_code: "AMOX-500",
    drug_name: "Amoxicillin 500mg",
    drug_brand: "PharmaCo",
    stock_available: 42,
    unit_price: 25.5,
    shelf: "B-03",
    batch_number: "LOT-2406",
    expiry_date: "2027-08-31",
    ...overrides,
  };
}

describe("StocktakingModal", () => {
  const originalPrint = window.print;
  beforeEach(() => {
    window.print = vi.fn();
  });
  afterEach(() => {
    window.print = originalPrint;
    vi.restoreAllMocks();
  });

  it("renders nothing when open=false", () => {
    const { container } = render(
      <StocktakingModal open={false} onClose={vi.fn()} rows={[makeRow()]} />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("renders one row per SKU, sorted by shelf, with a minted doc number", () => {
    render(
      <StocktakingModal
        open
        onClose={vi.fn()}
        rows={[
          makeRow({ drug_code: "Z-1", shelf: "Z-09" }),
          makeRow({ drug_code: "A-1", shelf: "A-01" }),
          makeRow({ drug_code: "M-1", shelf: "M-05" }),
        ]}
      />,
    );
    const body = screen.getByTestId("stocktaking-body");
    const rowNodes = within(body).getAllByTestId(/^stocktaking-row-/);
    expect(rowNodes.map((r) => r.getAttribute("data-testid"))).toEqual([
      "stocktaking-row-A-1",
      "stocktaking-row-M-1",
      "stocktaking-row-Z-1",
    ]);
    expect(screen.getByTestId("stocktaking-doc-number").textContent).toMatch(
      /^STK-\d{6}-01$/,
    );
  });

  it("totals the SKU count, system qty, and system value", () => {
    render(
      <StocktakingModal
        open
        onClose={vi.fn()}
        rows={[
          makeRow({ drug_code: "A", stock_available: 10, unit_price: 5 }),
          makeRow({ drug_code: "B", stock_available: 20, unit_price: 10 }),
        ]}
      />,
    );
    // 2 SKUs, system qty = 30, system value = 10*5 + 20*10 = 250
    const body = screen.getByTestId("stocktaking-body");
    expect(body.textContent).toContain("Totals — 2 SKUs");
    expect(body.textContent).toContain("EGP 250.00");
    expect(body.textContent).toContain("30");
  });

  it("renders a helpful empty state when rows is empty", () => {
    render(<StocktakingModal open onClose={vi.fn()} rows={[]} />);
    expect(screen.getByText(/No items to count/i)).toBeInTheDocument();
  });

  it("uses a provided branch name / doc number verbatim", () => {
    render(
      <StocktakingModal
        open
        onClose={vi.fn()}
        rows={[makeRow()]}
        branchName="DataPulse Pharmacy — Downtown"
        docNumber="STK-260419-42"
      />,
    );
    expect(screen.getByTestId("stocktaking-letterhead").textContent).toContain(
      "DataPulse Pharmacy — Downtown",
    );
    expect(screen.getByTestId("stocktaking-doc-number").textContent).toBe("STK-260419-42");
  });

  it("Print button invokes window.print", async () => {
    const user = userEvent.setup();
    render(<StocktakingModal open onClose={vi.fn()} rows={[makeRow()]} />);
    await user.click(screen.getByTestId("stocktaking-print-button"));
    expect(window.print).toHaveBeenCalledOnce();
  });

  it("Close button + Escape key both fire onClose", async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();
    render(<StocktakingModal open onClose={onClose} rows={[makeRow()]} />);

    await user.click(screen.getByTestId("stocktaking-close-button"));
    expect(onClose).toHaveBeenCalledTimes(1);

    await user.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalledTimes(2);
  });
});
