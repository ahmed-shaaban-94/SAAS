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
});
