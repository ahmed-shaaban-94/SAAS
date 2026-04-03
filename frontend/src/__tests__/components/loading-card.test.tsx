import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { LoadingCard } from "@/components/loading-card";

describe("LoadingCard", () => {
  it("renders with default 3 shimmer lines", () => {
    const { container } = render(<LoadingCard />);
    const shimmerLines = container.querySelectorAll(".shimmer-line");
    // 2 fixed shimmer lines + 3 dynamic = 5
    expect(shimmerLines.length).toBe(5);
  });

  it("renders custom number of lines", () => {
    const { container } = render(<LoadingCard lines={5} />);
    const shimmerLines = container.querySelectorAll(".shimmer-line");
    // 2 fixed + 5 dynamic = 7
    expect(shimmerLines.length).toBe(7);
  });

  it("applies custom className", () => {
    const { container } = render(<LoadingCard className="w-full" />);
    expect(container.firstChild).toHaveClass("w-full");
  });

  it("has animation class", () => {
    const { container } = render(<LoadingCard />);
    expect(container.firstChild).toHaveClass("animate-fade-in");
  });
});
