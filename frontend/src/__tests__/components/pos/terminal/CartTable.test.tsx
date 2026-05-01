import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CartTable } from "@pos/components/terminal/CartTable";
import type { PosCartItem } from "@pos/types/pos";

function makeItem(code: string, name: string, qty = 1, price = 25): PosCartItem {
  return {
    drug_code: code,
    drug_name: name,
    batch_number: null,
    expiry_date: null,
    quantity: qty,
    unit_price: price,
    discount: 0,
    line_total: qty * price,
    is_controlled: false,
  };
}

describe("CartTable", () => {
  it("renders the empty state when there are no items", () => {
    render(
      <CartTable
        items={[]}
        unsyncedCodes={new Set()}
        itemCount={0}
        averageItem={0}
        onIncrement={vi.fn()}
        onDecrement={vi.fn()}
        onRemove={vi.fn()}
      />,
    );

    expect(screen.getByTestId("cart-empty")).toBeInTheDocument();
    expect(screen.getByText("Start by scanning a drug")).toBeInTheDocument();
  });

  it("numbers rows sequentially starting at 01", () => {
    const items = [makeItem("A", "Alpha"), makeItem("B", "Beta"), makeItem("C", "Gamma")];
    render(
      <CartTable
        items={items}
        unsyncedCodes={new Set()}
        itemCount={3}
        averageItem={25}
        onIncrement={vi.fn()}
        onDecrement={vi.fn()}
        onRemove={vi.fn()}
      />,
    );

    expect(screen.getByText("01")).toBeInTheDocument();
    expect(screen.getByText("02")).toBeInTheDocument();
    expect(screen.getByText("03")).toBeInTheDocument();
  });

  it("marks unsynced rows with a Queued badge", () => {
    const items = [makeItem("A", "Alpha"), makeItem("B", "Beta")];
    render(
      <CartTable
        items={items}
        unsyncedCodes={new Set(["B"])}
        itemCount={2}
        averageItem={25}
        onIncrement={vi.fn()}
        onDecrement={vi.fn()}
        onRemove={vi.fn()}
      />,
    );

    const badges = screen.getAllByTestId("queued-badge");
    expect(badges).toHaveLength(1);
    expect(screen.getByTestId("cart-row-B")).toHaveAttribute("data-synced", "false");
    expect(screen.getByTestId("cart-row-A")).toHaveAttribute("data-synced", "true");
  });

  it("shows the running item count and average in the header", () => {
    render(
      <CartTable
        items={[makeItem("A", "Alpha", 2, 50)]}
        unsyncedCodes={new Set()}
        itemCount={2}
        averageItem={50}
        onIncrement={vi.fn()}
        onDecrement={vi.fn()}
        onRemove={vi.fn()}
      />,
    );

    // Header is a fragmented text node "Cart · 2 items · avg 50.00"
    const header = screen.getByText(/items/i).closest("div");
    expect(header).toHaveTextContent(/Cart/i);
    expect(header).toHaveTextContent(/2\s*items/);
    expect(header).toHaveTextContent(/avg/);
  });

  it("invokes the qty/remove callbacks with the correct drug_code", async () => {
    const user = userEvent.setup();
    const onIncrement = vi.fn();
    const onDecrement = vi.fn();
    const onRemove = vi.fn();
    render(
      <CartTable
        items={[makeItem("A", "Alpha")]}
        unsyncedCodes={new Set()}
        itemCount={1}
        averageItem={25}
        onIncrement={onIncrement}
        onDecrement={onDecrement}
        onRemove={onRemove}
      />,
    );

    await user.click(screen.getByLabelText(/increase quantity of Alpha/i));
    await user.click(screen.getByLabelText(/decrease quantity of Alpha/i));
    await user.click(screen.getByLabelText(/remove Alpha/i));

    expect(onIncrement).toHaveBeenCalledWith("A");
    expect(onDecrement).toHaveBeenCalledWith("A");
    expect(onRemove).toHaveBeenCalledWith("A");
  });
});
