import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { PaymentTiles } from "@pos/components/terminal/PaymentTiles";

function renderTiles(props: Partial<React.ComponentProps<typeof PaymentTiles>> = {}) {
  const defaults = {
    active: "cash" as const,
    onSelect: vi.fn(),
    voucherCode: null,
    voucherDiscount: 0,
    insuranceCoveragePct: null,
  };
  return render(<PaymentTiles {...defaults} {...props} />);
}

describe("PaymentTiles", () => {
  it("renders all four methods with their F-key badges", () => {
    renderTiles();

    expect(screen.getByTestId("pay-tile-cash")).toBeInTheDocument();
    expect(screen.getByTestId("pay-tile-card")).toBeInTheDocument();
    expect(screen.getByTestId("pay-tile-insurance")).toBeInTheDocument();
    expect(screen.getByTestId("pay-tile-voucher")).toBeInTheDocument();

    expect(screen.getByText("F9")).toBeInTheDocument();
    expect(screen.getByText("F10")).toBeInTheDocument();
    expect(screen.getByText("F11")).toBeInTheDocument();
    expect(screen.getByText("F7")).toBeInTheDocument();
  });

  it("marks the active method with aria-pressed=true", () => {
    renderTiles({ active: "card" });

    expect(screen.getByTestId("pay-tile-cash")).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByTestId("pay-tile-card")).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByTestId("pay-tile-insurance")).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByTestId("pay-tile-voucher")).toHaveAttribute("aria-pressed", "false");
  });

  it("invokes onSelect with the tile's method when clicked", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    renderTiles({ onSelect });

    await user.click(screen.getByTestId("pay-tile-insurance"));

    expect(onSelect).toHaveBeenCalledWith("insurance");
  });

  it("shows the voucher code + resolved discount on the voucher tile when attached", () => {
    renderTiles({ voucherCode: "SAVE10", voucherDiscount: 12.5 });

    const voucherTile = screen.getByTestId("pay-tile-voucher");
    expect(voucherTile).toHaveTextContent("−EGP 12.50");
  });

  it("shows coverage % on the insurance tile when active", () => {
    renderTiles({ insuranceCoveragePct: 80 });

    const insuranceTile = screen.getByTestId("pay-tile-insurance");
    expect(insuranceTile).toHaveTextContent("80% covered");
  });

  it("exposes a group role with an accessible label", () => {
    renderTiles();
    expect(screen.getByRole("group", { name: /payment methods/i })).toBeInTheDocument();
  });
});
