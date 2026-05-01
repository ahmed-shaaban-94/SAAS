import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { OrderTabs } from "@pos/components/terminal/OrderTabs";

describe("OrderTabs", () => {
  it("renders the active tab with order name and item count", () => {
    render(<OrderTabs orderName="طلب #101" itemCount={2} />);
    expect(screen.getByTestId("order-tab-active")).toHaveTextContent("طلب #101");
    expect(screen.getByTestId("order-tab-count")).toHaveTextContent("2");
  });

  it("renders a disabled + button with multi-cart-coming-soon tooltip", () => {
    render(<OrderTabs orderName="طلب #101" itemCount={0} />);
    const addBtn = screen.getByTestId("order-tab-add");
    expect(addBtn).toBeDisabled();
    expect(addBtn.getAttribute("title") ?? "").toContain("Multi-cart");
  });
});
