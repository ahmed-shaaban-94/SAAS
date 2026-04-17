import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { EmptyState } from "@/components/empty-state";

describe("EmptyState", () => {
  it("renders default title and description", () => {
    render(<EmptyState />);
    expect(screen.getByText("No data available")).toBeInTheDocument();
    expect(screen.getByText("Try adjusting your filters or check back later.")).toBeInTheDocument();
  });

  it("renders custom title", () => {
    render(<EmptyState title="No products found" />);
    expect(screen.getByText("No products found")).toBeInTheDocument();
  });

  it("renders custom description", () => {
    render(<EmptyState description="Please add some data first." />);
    expect(screen.getByText("Please add some data first.")).toBeInTheDocument();
  });

  it("renders SVG illustration", () => {
    const { container } = render(<EmptyState />);
    const svg = container.querySelector("svg");
    expect(svg).toBeInTheDocument();
    expect(svg).toHaveAttribute("aria-hidden", "true");
  });

  it("renders an optional primary-action slot", () => {
    render(
      <EmptyState
        title="No data yet"
        action={<button type="button">Load sample</button>}
      />,
    );
    expect(
      screen.getByRole("button", { name: /load sample/i }),
    ).toBeInTheDocument();
  });

  it("does not render an action slot when not provided (backward compat)", () => {
    const { container } = render(<EmptyState />);
    expect(container.querySelector("button")).toBeNull();
  });

  it("replaces the default illustration when icon prop is provided", () => {
    const Icon = () => (
      <svg data-testid="custom-icon" aria-hidden="true">
        <circle cx="10" cy="10" r="5" />
      </svg>
    );
    render(<EmptyState icon={<Icon />} title="Custom" />);
    expect(screen.getByTestId("custom-icon")).toBeInTheDocument();
  });
});
