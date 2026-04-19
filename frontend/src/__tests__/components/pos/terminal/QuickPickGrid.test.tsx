import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QuickPickGrid } from "@/components/pos/terminal/QuickPickGrid";
import type { QuickPickItem } from "@/components/pos/terminal/types";

const CATALOG: QuickPickItem[] = Array.from({ length: 9 }, (_, i) => ({
  drug_code: `SKU-${i + 1}`,
  drug_name: `Drug ${i + 1}`,
  unit_price: (i + 1) * 10,
  is_controlled: false,
}));

describe("QuickPickGrid", () => {
  it("renders 9 tiles with numeric shortcut badges", () => {
    render(<QuickPickGrid items={CATALOG} onPick={vi.fn()} />);
    for (let i = 1; i <= 9; i++) {
      expect(screen.getByTestId(`quick-pick-${i}`)).toBeInTheDocument();
    }
    expect(screen.getByText("Drug 1")).toBeInTheDocument();
    expect(screen.getByText("Drug 9")).toBeInTheDocument();
  });

  it("invokes onPick with the correct tile when clicked", async () => {
    const user = userEvent.setup();
    const onPick = vi.fn();
    render(<QuickPickGrid items={CATALOG} onPick={onPick} />);

    await user.click(screen.getByTestId("quick-pick-3"));

    expect(onPick).toHaveBeenCalledTimes(1);
    expect(onPick).toHaveBeenCalledWith(CATALOG[2]);
  });

  it("pads the grid with placeholder slots when catalog has fewer than 9 items", () => {
    render(<QuickPickGrid items={CATALOG.slice(0, 3)} onPick={vi.fn()} />);

    // First 3 tiles render as real buttons
    expect(screen.getByTestId("quick-pick-1")).toBeInTheDocument();
    expect(screen.getByTestId("quick-pick-3")).toBeInTheDocument();

    // Slots 4-9 exist as placeholders but are not interactive
    expect(screen.queryByTestId("quick-pick-4")).not.toBeInTheDocument();
  });

  it("includes the catalog price in each tile's aria-label for screen readers", () => {
    render(<QuickPickGrid items={CATALOG} onPick={vi.fn()} />);
    expect(screen.getByLabelText(/Quick pick 1.*Drug 1.*10\.00/)).toBeInTheDocument();
  });

  it("does not crash when the catalog is empty", () => {
    render(<QuickPickGrid items={[]} onPick={vi.fn()} />);
    // No real tiles, only placeholders — the grid renders its header
    expect(screen.getByText(/press 1/i)).toBeInTheDocument();
    expect(screen.queryByTestId("quick-pick-1")).not.toBeInTheDocument();
  });
});
